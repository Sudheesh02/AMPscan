#!/usr/bin/env python3
"""Build a clean AMP vs non-AMP dataset with homology-aware and random splits.

Stdlib only. Subcommands: preprocess, split, finalize.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

AA20X = set("ACDEFGHIKLMNPQRSTVWXY")
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})
SAFE_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")
UNIPROT_KW_RE = re.compile(
    r"antimicrobial|antibiotic|antibacterial|antifungal|antiviral|"
    r"antiparasitic|antiprotozoal|defensin|cathelicidin|bacteriocin|"
    r"cecropin|magainin|protegrin|thionin|hepcidin|histatin|lactoferricin|"
    r"piscidin|pleurocidin|dermaseptin|brevinin|esculentin|temporin|"
    r"bombinin|melittin|lysozyme|histone|defensin-like",
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parent.parent


def parse_fasta(path: Path):
    recs = []
    hdr = None
    seq = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    recs.append((hdr, "".join(seq)))
                hdr, seq = line[1:], []
            else:
                seq.append(line.strip())
        if hdr is not None:
            recs.append((hdr, "".join(seq)))
    return recs


def write_fasta(path: Path, recs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as out:
        for h, s in recs:
            out.write(f">{h}\n")
            if not s:
                out.write("\n")
                continue
            for i in range(0, len(s), 60):
                out.write(s[i : i + 60] + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_fasta(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s:
                return s.startswith(">")
    return False


def sanitize_token(hdr: str) -> str:
    tok = hdr.split()[0] if hdr.strip() else "unknown"
    tok = SAFE_TOKEN.sub("_", tok).strip("_")
    return tok or "unknown"


def make_id(label: int, source: str, hdr: str, used: set) -> str:
    prefix = f"{'POS' if label == 1 else 'NEG'}_{source}_{sanitize_token(hdr)}"
    sid = prefix
    n = 2
    while sid in used:
        sid = f"{prefix}_{n}"
        n += 1
    used.add(sid)
    return sid


def detect_pos_source(raw_dir: Path):
    dramp = raw_dir / "general_amps.fasta"
    apd = raw_dir / "naturalAMPs_APD2024a.fasta"
    amp_tr = raw_dir / "AMPlify_AMP_train_common.fa"
    amp_te = raw_dir / "AMPlify_AMP_test_common.fa"
    if looks_like_fasta(dramp):
        return "DRAMP", [dramp]
    if looks_like_fasta(apd):
        return "APD", [apd]
    if looks_like_fasta(amp_tr) or looks_like_fasta(amp_te):
        files = [p for p in (amp_tr, amp_te) if looks_like_fasta(p)]
        return "AMPLIFY", files
    raise SystemExit("No usable positive FASTA found in data/raw/")


def load_amplify_negatives(raw_dir: Path):
    bal = [
        raw_dir / "AMPlify_non_AMP_train_balanced.fa",
        raw_dir / "AMPlify_non_AMP_test_balanced.fa",
    ]
    imb = [
        raw_dir / "AMPlify_non_AMP_train_imbalanced.fa",
        raw_dir / "AMPlify_non_AMP_test_imbalanced.fa",
    ]
    bal_ok = [p for p in bal if looks_like_fasta(p)]
    imb_ok = [p for p in imb if looks_like_fasta(p)]
    if not bal_ok and not imb_ok:
        return None
    return {"balanced": bal_ok, "imbalanced": imb_ok}


def load_uniprot_fallback(raw_dir: Path, n_pos: int, seed: int = 42):
    gz = raw_dir / "uniprot_sprot.fasta.gz"
    fa = raw_dir / "uniprot_sprot.fasta"
    path = None
    gzipped = False
    if gz.is_file() and gz.stat().st_size > 0:
        path = gz
        gzipped = True
    elif looks_like_fasta(fa):
        path = fa
    if path is None:
        return None, {}

    import gzip

    opener = gzip.open if gzipped else open
    recs = []
    hdr, seq = None, []
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    recs.append((hdr, "".join(seq)))
                hdr, seq = line[1:], []
            else:
                seq.append(line.strip())
        if hdr is not None:
            recs.append((hdr, "".join(seq)))

    eligible = []
    n_in = len(recs)
    n_len = n_frag = n_kw = 0
    for hdr, seq in recs:
        s = seq.replace(" ", "").replace("*", "").upper()
        if not (5 <= len(s) <= 100):
            continue
        n_len += 1
        if "fragment" in hdr.lower():
            n_frag += 1
            continue
        if UNIPROT_KW_RE.search(hdr):
            n_kw += 1
            continue
        eligible.append((hdr, seq))

    rng = random.Random(seed)
    rng.shuffle(eligible)
    take = min(n_pos, len(eligible)) if n_pos > 0 else len(eligible)
    chosen = eligible[:take]
    stats = {
        "n_in": n_in,
        "n_len": n_len,
        "n_drop_fragment": n_frag,
        "n_drop_keyword": n_kw,
        "n_eligible": len(eligible),
        "n_sampled": len(chosen),
        "seed": seed,
        "file": str(path),
    }
    return chosen, stats


def stage_clean(recs, source: str, label: int, used_ids: set):
    raw = []
    len_ok = []
    alpha_ok = []
    dropped = []
    n_mapped = 0
    for hdr, seq in recs:
        raw.append((hdr, seq.replace(" ", "").replace("\t", "")))
        s = seq.replace(" ", "").replace("*", "").upper()
        if not (5 <= len(s) <= 100):
            continue
        len_ok.append((hdr, s))
        mapped = s.translate(MAP)
        if mapped != s:
            n_mapped += 1
        if any(c not in AA20X for c in mapped):
            dropped.append((hdr, mapped))
            continue
        alpha_ok.append((hdr, mapped))

    seen = set()
    dedup = []
    n_dup = 0
    for hdr, s in alpha_ok:
        if s in seen:
            n_dup += 1
            continue
        seen.add(s)
        sid = make_id(label, source, hdr, used_ids)
        dedup.append(
            {
                "id": sid,
                "seq": s,
                "orig_header": hdr,
                "source": source,
                "label": label,
            }
        )

    stats = {
        "n_in": len(recs),
        "n_raw": len(raw),
        "n_len": len(len_ok),
        "n_mapped": n_mapped,
        "n_drop_non_aa": len(dropped),
        "n_after_alphabet": len(alpha_ok),
        "n_exact_dups_dropped": n_dup,
        "n_dedup": len(dedup),
    }
    return {
        "raw": raw,
        "len_ok": len_ok,
        "alpha_ok": alpha_ok,
        "dropped": dropped,
        "dedup": dedup,
        "stats": stats,
    }


def recs_from_files(files):
    out = []
    for p in files:
        out.extend(parse_fasta(p))
    return out


def write_id_fasta(path: Path, rows):
    recs = []
    for r in rows:
        h = f"{r['id']} LABEL={r['label']} SOURCE={r['source']}"
        recs.append((h, r["seq"]))
    write_fasta(path, recs)


def path_for_json(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def cmd_preprocess(args):
    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.processed_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pos_source, pos_files = detect_pos_source(raw_dir)
    pos_recs = recs_from_files(pos_files)
    used_ids = set()
    pos_st = stage_clean(pos_recs, pos_source, 1, used_ids)

    neg_source = None
    neg_files_used = []
    imb_added = False
    uniprot_stats = None
    amp = load_amplify_negatives(raw_dir)

    if amp and amp["balanced"]:
        neg_source = "AMPLIFY"
        neg_files_used = list(amp["balanced"])
        neg_recs = recs_from_files(neg_files_used)
        neg_st = stage_clean(neg_recs, neg_source, 0, used_ids)
        if neg_st["stats"]["n_dedup"] < pos_st["stats"]["n_dedup"] and amp["imbalanced"]:
            extra_recs = recs_from_files(amp["imbalanced"])
            extra_st = stage_clean(extra_recs, neg_source, 0, used_ids)
            seen_neg = {r["seq"] for r in neg_st["dedup"]}
            need = pos_st["stats"]["n_dedup"] - neg_st["stats"]["n_dedup"]
            added = []
            for r in extra_st["dedup"]:
                if r["seq"] in seen_neg:
                    continue
                seen_neg.add(r["seq"])
                added.append(r)
                if len(added) >= need:
                    break
            if added:
                imb_added = True
                neg_files_used.extend(amp["imbalanced"])
                neg_st["raw"].extend(extra_st["raw"])
                neg_st["len_ok"].extend(extra_st["len_ok"])
                neg_st["alpha_ok"].extend(extra_st["alpha_ok"])
                neg_st["dropped"].extend(extra_st["dropped"])
                neg_st["dedup"].extend(added)
                neg_st["stats"]["imbalanced_considered"] = extra_st["stats"]
                neg_st["stats"]["imbalanced_added"] = len(added)
                neg_st["stats"]["n_dedup"] = len(neg_st["dedup"])
    else:
        recs, uniprot_stats = load_uniprot_fallback(
            raw_dir, pos_st["stats"]["n_dedup"], seed=42
        )
        if recs is None:
            raise SystemExit(
                "No AMPlify non-AMP FASTAs and no UniProt Swiss-Prot fallback file."
            )
        neg_source = "UNIPROT"
        neg_files_used = [Path(uniprot_stats["file"])]
        neg_st = stage_clean(recs, neg_source, 0, used_ids)

    pos_seq = {r["seq"]: r for r in pos_st["dedup"]}
    conflicts = []
    kept_neg = []
    for r in neg_st["dedup"]:
        if r["seq"] in pos_seq:
            conflicts.append(
                {
                    "seq": r["seq"],
                    "pos_id": pos_seq[r["seq"]]["id"],
                    "neg_id": r["id"],
                    "pos_header": pos_seq[r["seq"]]["orig_header"],
                    "neg_header": r["orig_header"],
                }
            )
        else:
            kept_neg.append(r)
    neg_st["dedup"] = kept_neg
    neg_st["stats"]["n_conflicts_dropped"] = len(conflicts)
    neg_st["stats"]["n_after_conflict"] = len(kept_neg)
    pos_st["stats"]["n_after_conflict"] = len(pos_st["dedup"])

    write_fasta(out_dir / "positives_raw.fasta", pos_st["raw"])
    write_fasta(out_dir / "negatives_raw.fasta", neg_st["raw"])
    write_fasta(out_dir / "positives_len5_100.fasta", pos_st["len_ok"])
    write_fasta(out_dir / "negatives_len5_100.fasta", neg_st["len_ok"])
    write_fasta(out_dir / "positives_alphabet.fasta", pos_st["alpha_ok"])
    write_fasta(out_dir / "negatives_alphabet.fasta", neg_st["alpha_ok"])
    write_fasta(out_dir / "dropped_non_aa.fasta", pos_st["dropped"] + neg_st["dropped"])
    write_id_fasta(out_dir / "positives_dedup.fasta", pos_st["dedup"])
    write_id_fasta(out_dir / "negatives_dedup.fasta", neg_st["dedup"])

    combined = pos_st["dedup"] + neg_st["dedup"]
    combined.sort(key=lambda r: r["id"])
    write_id_fasta(out_dir / "combined_clean.fasta", combined)

    with (out_dir / "labels.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["id", "label", "source", "length", "original_header"])
        for r in combined:
            w.writerow([r["id"], r["label"], r["source"], len(r["seq"]), r["orig_header"]])

    with (out_dir / "cross_class_conflicts.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["seq", "pos_id", "neg_id", "pos_header", "neg_header"])
        for c in conflicts:
            w.writerow(
                [c["seq"], c["pos_id"], c["neg_id"], c["pos_header"], c["neg_header"]]
            )

    alpha_counts = {
        "mapping": {"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"},
        "allowed_after_map": "ACDEFGHIKLMNPQRSTVWXY",
        "positives": {
            "n_mapped": pos_st["stats"]["n_mapped"],
            "n_drop_non_aa": pos_st["stats"]["n_drop_non_aa"],
            "n_kept_after_alphabet": pos_st["stats"]["n_after_alphabet"],
        },
        "negatives": {
            "n_mapped": neg_st["stats"]["n_mapped"],
            "n_drop_non_aa": neg_st["stats"]["n_drop_non_aa"],
            "n_kept_after_alphabet": neg_st["stats"]["n_after_alphabet"],
        },
    }
    (out_dir / "alphabet_filter_counts.json").write_text(
        json.dumps(alpha_counts, indent=2) + "\n", encoding="utf-8"
    )

    source_used = {
        "positives": {
            "source": pos_source,
            "files": [path_for_json(p) for p in pos_files],
        },
        "negatives": {
            "source": neg_source,
            "files": [path_for_json(p) for p in neg_files_used],
            "imbalanced_added": imb_added,
            "fallback_uniprot": neg_source == "UNIPROT",
            "uniprot_filter": uniprot_stats,
        },
    }
    (raw_dir / "SOURCE_USED.json").write_text(
        json.dumps(source_used, indent=2) + "\n", encoding="utf-8"
    )

    preprocess_counts = {
        "positives": pos_st["stats"],
        "negatives": neg_st["stats"],
        "n_conflicts": len(conflicts),
        "n_combined": len(combined),
        "n_pos_final": len(pos_st["dedup"]),
        "n_neg_final": len(neg_st["dedup"]),
        "source_used": source_used,
    }
    (out_dir / "preprocess_counts.json").write_text(
        json.dumps(preprocess_counts, indent=2) + "\n", encoding="utf-8"
    )

    print("PREPROCESS OK")
    print(
        f"  pos source={pos_source} raw={pos_st['stats']['n_in']} "
        f"len={pos_st['stats']['n_len']} alpha={pos_st['stats']['n_after_alphabet']} "
        f"dedup={pos_st['stats']['n_dedup']} final={len(pos_st['dedup'])}"
    )
    print(
        f"  neg source={neg_source} raw={neg_st['stats']['n_in']} "
        f"len={neg_st['stats']['n_len']} alpha={neg_st['stats']['n_after_alphabet']} "
        f"dedup={neg_st['stats']['n_dedup']} conflicts_dropped={len(conflicts)} "
        f"final={len(neg_st['dedup'])} imbalanced_added={imb_added}"
    )


def load_labels(path: Path):
    labels = {}
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            labels[row["id"]] = int(row["label"])
    return labels


def load_seq_map(fasta: Path):
    recs = parse_fasta(fasta)
    out = {}
    for h, s in recs:
        sid = h.split()[0]
        out[sid] = (h, s)
    return out


def parse_cluster_tsv(path: Path, labels: dict):
    clusters = defaultdict(list)
    unknown = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise SystemExit(f"Bad cluster.tsv line: {line!r}")
            _rep, member = parts[0], parts[1]
            if member not in labels:
                unknown.append(member)
                continue
            clusters[_rep].append(member)
    for rep, mems in list(clusters.items()):
        seen = set()
        uniq = []
        for m in mems:
            if m not in seen:
                seen.add(m)
                uniq.append(m)
        clusters[rep] = uniq
    if unknown:
        raise SystemExit(
            f"{len(unknown)} cluster members not in labels.tsv (example: {unknown[:5]})"
        )
    in_cluster = {m for mems in clusters.values() for m in mems}
    missing = set(labels) - in_cluster
    if missing:
        raise SystemExit(
            f"{len(missing)} labeled IDs missing from cluster.tsv (example: {list(missing)[:5]})"
        )
    return dict(clusters)


def stratum_of(n_pos, n_neg):
    if n_neg == 0:
        return "pos_only"
    if n_pos == 0:
        return "neg_only"
    return "mixed"


def greedy_assign_stratum(items, rng):
    items = list(items)
    rng.shuffle(items)
    stratum_n = sum(it["n"] for it in items)
    if stratum_n == 0:
        return []
    n_train = int(round(stratum_n * 0.70))
    n_val = int(round(stratum_n * 0.15))
    if n_train + n_val > stratum_n:
        n_val = max(0, stratum_n - n_train)
    n_test = stratum_n - n_train - n_val
    targets = {"train": n_train, "val": n_val, "test": n_test}
    current = {"train": 0, "val": 0, "test": 0}
    assigned = []
    for it in items:
        best = None
        best_ratio = float("inf")
        for fold in ("train", "val", "test"):
            t = targets[fold]
            if t <= 0:
                ratio = float("inf")
            else:
                ratio = current[fold] / t
            if ratio < best_ratio:
                best_ratio = ratio
                best = fold
        if best is None or best_ratio == float("inf"):
            remain = {f: targets[f] - current[f] for f in targets}
            if any(v > 0 for v in remain.values()):
                best = max(remain, key=lambda f: remain[f])
            else:
                best = min(current, key=current.get)
        row = dict(it)
        row["fold"] = best
        current[best] += it["n"]
        assigned.append(row)
    return assigned


def write_id_list(path: Path, ids):
    ids = sorted(ids)
    path.write_text("".join(i + "\n" for i in ids), encoding="utf-8")
    return ids


def write_fold_fastas(out_dir: Path, prefix: str, fold_ids, seq_map, labels):
    def dump(name, ids):
        recs = [(seq_map[i][0], seq_map[i][1]) for i in sorted(ids)]
        write_fasta(out_dir / name, recs)

    for fold, ids in fold_ids.items():
        dump(f"{prefix}{fold}.fasta", ids)
        pos = [i for i in ids if labels[i] == 1]
        neg = [i for i in ids if labels[i] == 0]
        dump(f"{prefix}{fold}_pos.fasta", pos)
        dump(f"{prefix}{fold}_neg.fasta", neg)


def assert_partition(fold_ids, labels, clusters=None):
    errors = []
    all_ids = set(labels)
    seen = []
    for fold, ids in fold_ids.items():
        s = set(ids)
        if not s:
            errors.append(f"fold {fold} is empty")
        pos = sum(1 for i in s if labels[i] == 1)
        neg = sum(1 for i in s if labels[i] == 0)
        if pos == 0 or neg == 0:
            errors.append(f"fold {fold} missing a class (pos={pos} neg={neg})")
        seen.append(s)
    union = set().union(*seen) if seen else set()
    inter_tv = seen[0] & seen[1] if len(seen) >= 2 else set()
    inter_tt = seen[0] & seen[2] if len(seen) >= 3 else set()
    inter_vt = seen[1] & seen[2] if len(seen) >= 3 else set()
    if inter_tv or inter_tt or inter_vt:
        errors.append(
            f"ID overlap across folds: train∩val={len(inter_tv)} "
            f"train∩test={len(inter_tt)} val∩test={len(inter_vt)}"
        )
    if union != all_ids:
        errors.append(
            f"union != all labels: missing={len(all_ids - union)} extra={len(union - all_ids)}"
        )
    if clusters is not None:
        id_to_fold = {}
        for fold, ids in fold_ids.items():
            for i in ids:
                id_to_fold[i] = fold
        for rep, members in clusters.items():
            fs = {id_to_fold[m] for m in members}
            if len(fs) != 1:
                errors.append(f"cluster {rep} split across {fs}")
                break
    if errors:
        raise SystemExit("SPLIT ASSERTIONS FAILED:\n  - " + "\n  - ".join(errors))


def fold_counts(ids, labels):
    pos = sum(1 for i in ids if labels[i] == 1)
    return {"n": len(ids), "n_pos": pos, "n_neg": len(ids) - pos}


def cmd_split(args):
    cluster_tsv = Path(args.cluster_tsv)
    labels_path = Path(args.labels)
    fasta_path = Path(args.fasta)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(args.seed)

    labels = load_labels(labels_path)
    seq_map = load_seq_map(fasta_path)
    if set(seq_map) != set(labels):
        raise SystemExit(
            f"FASTA/labels ID mismatch: "
            f"only_fa={len(set(seq_map) - set(labels))} "
            f"only_lab={len(set(labels) - set(seq_map))}"
        )

    clusters = parse_cluster_tsv(cluster_tsv, labels)

    cluster_rows = []
    strata = {"pos_only": [], "neg_only": [], "mixed": []}
    for rep, members in clusters.items():
        n_pos = sum(1 for m in members if labels[m] == 1)
        n_neg = len(members) - n_pos
        s = stratum_of(n_pos, n_neg)
        row = {
            "rep": rep,
            "members": members,
            "n": len(members),
            "n_pos": n_pos,
            "n_neg": n_neg,
            "stratum": s,
        }
        cluster_rows.append(row)
        strata[s].append(row)

    rng = random.Random(seed)
    assigned = []
    for sname in ("pos_only", "neg_only", "mixed"):
        assigned.extend(greedy_assign_stratum(strata[sname], rng))

    fold_ids = {"train": [], "val": [], "test": []}
    for it in assigned:
        fold_ids[it["fold"]].extend(it["members"])

    fold_sets = {k: set(v) for k, v in fold_ids.items()}
    assert_partition(fold_sets, labels, clusters)

    for fold in ("train", "val", "test"):
        write_id_list(out_dir / f"{fold}_ids.txt", fold_sets[fold])

    with (out_dir / "cluster_assignments.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["rep", "fold", "n", "n_pos", "n_neg", "stratum"])
        for it in sorted(assigned, key=lambda x: x["rep"]):
            w.writerow(
                [it["rep"], it["fold"], it["n"], it["n_pos"], it["n_neg"], it["stratum"]]
            )

    write_fold_fastas(out_dir, "", fold_sets, seq_map, labels)

    n_clusters = {
        "total": len(cluster_rows),
        "pos_only": len(strata["pos_only"]),
        "neg_only": len(strata["neg_only"]),
        "mixed": len(strata["mixed"]),
    }
    split_stats = {
        "kind": "homology_cluster",
        "seed": seed,
        "mmseqs": {"min_seq_id": 0.3, "c": 0.8, "cov_mode": 1},
        "fractions": {"train": 0.70, "val": 0.15, "test": 0.15},
        "clusters": n_clusters,
        "train": fold_counts(fold_sets["train"], labels),
        "val": fold_counts(fold_sets["val"], labels),
        "test": fold_counts(fold_sets["test"], labels),
        "assertions_passed": True,
    }
    (out_dir / "split_stats.json").write_text(
        json.dumps(split_stats, indent=2) + "\n", encoding="utf-8"
    )

    rng2 = random.Random(seed)
    rand_ids = {"train": [], "val": [], "test": []}
    for lab in (1, 0):
        ids = sorted(i for i, y in labels.items() if y == lab)
        rng2.shuffle(ids)
        n = len(ids)
        n_train = int(round(n * 0.70))
        n_val = int(round(n * 0.15))
        if n_train + n_val > n:
            n_val = max(0, n - n_train)
        rand_ids["train"].extend(ids[:n_train])
        rand_ids["val"].extend(ids[n_train : n_train + n_val])
        rand_ids["test"].extend(ids[n_train + n_val :])
    rand_sets = {k: set(v) for k, v in rand_ids.items()}
    assert_partition(rand_sets, labels, clusters=None)

    for fold in ("train", "val", "test"):
        write_id_list(out_dir / f"random_{fold}_ids.txt", rand_sets[fold])
    write_fold_fastas(out_dir, "random_", rand_sets, seq_map, labels)
    random_stats = {
        "kind": "random_control",
        "seed": seed,
        "note": "Same cleaned sequences as homology split; clusters ignored. Stratified by class.",
        "fractions": {"train": 0.70, "val": 0.15, "test": 0.15},
        "train": fold_counts(rand_sets["train"], labels),
        "val": fold_counts(rand_sets["val"], labels),
        "test": fold_counts(rand_sets["test"], labels),
        "assertions_passed": True,
    }
    (out_dir / "random_split_stats.json").write_text(
        json.dumps(random_stats, indent=2) + "\n", encoding="utf-8"
    )

    print("SPLIT OK (homology + random control)")
    print(
        "  clusters: total={total} pos_only={pos_only} neg_only={neg_only} mixed={mixed}".format(
            **n_clusters
        )
    )
    for fold in ("train", "val", "test"):
        c = split_stats[fold]
        print(f"  homology {fold}: n={c['n']} pos={c['n_pos']} neg={c['n_neg']}")
    for fold in ("train", "val", "test"):
        c = random_stats[fold]
        print(f"  random    {fold}: n={c['n']} pos={c['n_pos']} neg={c['n_neg']}")


EXPECTED_AMPLIFY_MD5 = {
    "AMPlify_non_AMP_train_balanced.fa": "7652c9ab3b42404d8a037ed22825bd97",
    "AMPlify_non_AMP_test_balanced.fa": "7dbc53abf6fcd66c0ad64d9e7925b476",
    "AMPlify_non_AMP_train_imbalanced.fa": "7f4d2514935597b0c0a073bd2acbb5a6",
    "AMPlify_non_AMP_test_imbalanced.fa": "35c764b23c325e0ff0c5b0741ecc1f6f",
    "AMPlify_AMP_train_common.fa": "67470a4ac0e0356c2f756ce2831a536d",
    "AMPlify_AMP_test_common.fa": "9251af687acaa4b55db56a656d8f33bd",
}


def cmd_finalize(args):
    data = ROOT / "data"
    raw = data / "raw"
    proc = data / "processed"
    splits = data / "splits"
    counts = json.loads((proc / "preprocess_counts.json").read_text(encoding="utf-8"))
    source_used = json.loads((raw / "SOURCE_USED.json").read_text(encoding="utf-8"))
    split_stats = json.loads((splits / "split_stats.json").read_text(encoding="utf-8"))
    random_stats = json.loads(
        (splits / "random_split_stats.json").read_text(encoding="utf-8")
    )
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pos_src = source_used["positives"]["source"]
    neg_src = source_used["negatives"]["source"]
    fallback_pos = pos_src != "DRAMP"
    fallback_neg = source_used["negatives"].get("fallback_uniprot", False)
    imb_added = source_used["negatives"].get("imbalanced_added", False)

    pos_cite = {
        "DRAMP": (
            "CC BY 4.0",
            "https://dramp.cpu-bioinfor.org/downloads/download.php"
            "?filename=download_data/DRAMP3.0_new/general_amps.fasta",
            [
                "DRAMP 4.0: Ma et al., Nucleic Acids Research 53:D403–D410 (2025). https://doi.org/10.1093/nar/gkae1046",
                "DRAMP 3.0: Shi et al., Nucleic Acids Research 50:D488–D496 (2022). PMID 34390348",
            ],
        ),
        "APD": (
            "APD terms of use (cite APD3/APD6; no CC license stated)",
            "https://aps.unmc.edu/assets/sequences/naturalAMPs_APD2024a.fasta",
            [
                "Wang et al., APD3, Nucleic Acids Research 2016",
                "Wang et al., APD6, Nucleic Acids Research 2025",
            ],
        ),
        "AMPLIFY": (
            "CC BY 4.0",
            "https://doi.org/10.5281/zenodo.7320306",
            ["Li et al., BMC Genomics 23:77 (2022)"],
        ),
    }
    license_s, url_s, cites = pos_cite[pos_src]
    pos_files = source_used["positives"]["files"]
    pos_raw_n = counts["positives"]["n_in"]

    uniprot_block = ""
    if fallback_neg:
        uf = source_used["negatives"].get("uniprot_filter") or {}
        uniprot_block = f"""
If Swiss-Prot fallback was used:
- File: {uf.get('file', 'uniprot_sprot.fasta.gz')} from UniProt FTP (CC BY 4.0)
- Filter: reviewed Swiss-Prot, length 5–100, drop Fragment, drop header matching:
  antimicrobial|antibiotic|antibacterial|antifungal|antiviral|antiparasitic|
  antiprotozoal|defensin|cathelicidin|bacteriocin|cecropin|magainin|protegrin|
  thionin|hepcidin|histatin|lactoferricin|piscidin|pleurocidin|dermaseptin|
  brevinin|esculentin|temporin|bombinin|melittin|lysozyme|histone|defensin-like
- Sample: random.Random(42), size = min(n_pos, n_eligible)
- Counts: in={uf.get('n_in')} len={uf.get('n_len')} drop_fragment={uf.get('n_drop_fragment')}
  drop_keyword={uf.get('n_drop_keyword')} eligible={uf.get('n_eligible')} sampled={uf.get('n_sampled')}
"""

    license_md = f"""# Data licenses and provenance — AMP vs non-AMP set

Built: {built}
Purpose: homology-aware AMP (1) vs non-AMP (0) peptide dataset. No model weights.

## Positives
Source used: {pos_src}
File: {', '.join(pos_files)}
URL: {url_s}
Records in raw file: {pos_raw_n}
License: {license_s}
Required citation:
"""
    for c in cites:
        license_md += f"- {c}\n"
    if pos_src == "DRAMP":
        license_md += (
            "\nDRAMP license confirmation: https://dramp.cpu-bioinfor.org/downloads/ "
            "and the homepage state the data are CC BY 4.0.\n"
        )

    license_md += f"""
## Negatives
Source used: {neg_src}
Files: {', '.join(source_used['negatives']['files'])}
Imbalanced AMPlify negatives added: {imb_added}
URL / DOI: 10.5281/zenodo.7320306 (CC BY 4.0)
Citation: Li, Sutherland, Hammond et al., BMC Genomics 23:77 (2022);
          Li, Warren & Birol, BMC Research Notes 16:11 (2023).
MD5 (Zenodo):
- AMPlify_non_AMP_train_balanced.fa   7652c9ab3b42404d8a037ed22825bd97
- AMPlify_non_AMP_test_balanced.fa    7dbc53abf6fcd66c0ad64d9e7925b476
- AMPlify_non_AMP_train_imbalanced.fa 7f4d2514935597b0c0a073bd2acbb5a6
- AMPlify_non_AMP_test_imbalanced.fa  35c764b23c325e0ff0c5b0741ecc1f6f
{uniprot_block}
## Preprocessing
- Length 5–100 inclusive
- Uppercase; B,Z,U,O,J mapped to X; leftover non-AA dropped (X allowed)
- Exact sequence dedup, keep first
- Cross-class exact duplicate → keep positive
- Final cleaned: {counts['n_pos_final']} positives, {counts['n_neg_final']} negatives
  ({counts['n_conflicts']} cross-class conflicts resolved)
See data/processed/preprocess_counts.json and alphabet_filter_counts.json

## Homology split
mmseqs easy-cluster combined_clean.fasta \\
  --min-seq-id 0.3 -c 0.8 --cov-mode 1
Whole clusters assigned to train/val/test (targets 70/15/15, seed 42),
stratified by pos_only / neg_only / mixed. A cluster is never split.
Clusters: total={split_stats['clusters']['total']} pos_only={split_stats['clusters']['pos_only']} \
neg_only={split_stats['clusters']['neg_only']} mixed={split_stats['clusters']['mixed']}
Homology fold sizes: train={split_stats['train']['n']} (pos={split_stats['train']['n_pos']} neg={split_stats['train']['n_neg']}), \
val={split_stats['val']['n']} (pos={split_stats['val']['n_pos']} neg={split_stats['val']['n_neg']}), \
test={split_stats['test']['n']} (pos={split_stats['test']['n_pos']} neg={split_stats['test']['n_neg']})

## Random-split control (not for primary evaluation)
Same cleaned sequences, clusters ignored, 70/15/15, seed 42, stratified by class.
Files: data/splits/random_*
Random fold sizes: train={random_stats['train']['n']} (pos={random_stats['train']['n_pos']} neg={random_stats['train']['n_neg']}), \
val={random_stats['val']['n']} (pos={random_stats['val']['n_pos']} neg={random_stats['val']['n_neg']}), \
test={random_stats['test']['n']} (pos={random_stats['test']['n_pos']} neg={random_stats['test']['n_neg']})
"""
    (data / "LICENSE_NOTES.md").write_text(license_md, encoding="utf-8")

    files_info = []
    for p in sorted(data.rglob("*")):
        if not p.is_file():
            continue
        if "mmseqs_tmp" in p.parts:
            continue
        files_info.append(
            {"path": path_for_json(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        )

    raw_hashes = {}
    md5_check = {}
    for p in sorted(raw.glob("*")):
        if not p.is_file() or p.suffix == ".json":
            continue
        raw_hashes[p.name] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        if p.name in EXPECTED_AMPLIFY_MD5:
            got = md5_file(p)
            md5_check[p.name] = {
                "expected": EXPECTED_AMPLIFY_MD5[p.name],
                "got": got,
                "ok": got == EXPECTED_AMPLIFY_MD5[p.name],
            }

    manifest = {
        "built": built,
        "project": str(ROOT),
        "phase": "data_only",
        "seed": 42,
        "sources": source_used,
        "fallback_used": {
            "positives": fallback_pos,
            "positives_source": pos_src,
            "negatives_uniprot": fallback_neg,
            "negatives_imbalanced_added": imb_added,
        },
        "raw_file_hashes": raw_hashes,
        "amplify_md5_check": md5_check,
        "preprocess_counts": counts,
        "homology_split": split_stats,
        "random_split": random_stats,
        "mmseqs": {
            "version": args.mmseqs_version or "unknown",
            "command": [
                "mmseqs",
                "easy-cluster",
                "data/processed/combined_clean.fasta",
                "data/splits/mmseqs/cluster",
                "data/splits/mmseqs_tmp",
                "--min-seq-id",
                "0.3",
                "-c",
                "0.8",
                "--cov-mode",
                "1",
                "--threads",
                "4",
            ],
        },
        "files": files_info,
    }
    (data / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("FINALIZE OK")
    print("  LICENSE_NOTES.md and data_manifest.json written")
    print(
        f"  fallback_pos={fallback_pos} ({pos_src}) "
        f"fallback_uniprot={fallback_neg} imbalanced_added={imb_added}"
    )


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("preprocess")
    sp.add_argument("--pos-source", default="auto")
    sp.add_argument("--neg-source", default="amplify")
    sp.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"))
    sp.add_argument("--processed-dir", default=str(ROOT / "data" / "processed"))
    sp.set_defaults(func=cmd_preprocess)

    ss = sub.add_parser("split")
    ss.add_argument(
        "--cluster-tsv",
        default=str(ROOT / "data" / "splits" / "mmseqs" / "cluster_cluster.tsv"),
    )
    ss.add_argument("--labels", default=str(ROOT / "data" / "processed" / "labels.tsv"))
    ss.add_argument(
        "--fasta", default=str(ROOT / "data" / "processed" / "combined_clean.fasta")
    )
    ss.add_argument("--out-dir", default=str(ROOT / "data" / "splits"))
    ss.add_argument("--train", type=float, default=0.70)
    ss.add_argument("--val", type=float, default=0.15)
    ss.add_argument("--test", type=float, default=0.15)
    ss.add_argument("--seed", type=int, default=42)
    ss.set_defaults(func=cmd_split)

    sf = sub.add_parser("finalize")
    sf.add_argument("--mmseqs-version", default="")
    sf.set_defaults(func=cmd_finalize)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
