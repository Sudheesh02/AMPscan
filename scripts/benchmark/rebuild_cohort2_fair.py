#!/usr/bin/env python3
"""Rebuild Cohort 2b: DBAASP novels + length-matched FRAGMENT non-AMPs.

Intact unused short non-AMPs on disk are ~395 (5–30 aa). That is not enough.
This script cuts random windows from unused LONG negatives that already sit
outside the AMPscan splits, then applies the same 30% MMseqs walls.

Do not call these assayed non-AMPs. Header SRC=FRAGMENT_NEG.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_amp_dataset import AA20X, MAP, parse_fasta, write_fasta  # noqa: E402

OUT = ROOT / "data" / "splits" / "dbaasp_ood"
CACHE = ROOT / "reports" / "benchmarks" / "cache" / "dbaasp_ood_fair"
TRAIN_FA = ROOT / "data" / "splits" / "train.fasta"
VAL_FA = ROOT / "data" / "splits" / "val.fasta"
TEST_FA = ROOT / "data" / "splits" / "test.fasta"
DBAASP_FA = ROOT / "DBAASP" / "master_DBAASP.fasta"
NEG_ALPHA = ROOT / "data" / "processed" / "negatives_alphabet.fasta"
MMSEQS = Path("/home/sudheesh02/miniforge3/envs/amp-data/bin/mmseqs")
SEED = 42
MIN_ID = 0.3
COV = 0.8
PARENT_MIN_LEN = 40
WINDOWS_PER_PARENT = 4
TARGET_SHORT_NEGS = 8000


def clean_seq(raw: str):
    has_d = any("a" <= c <= "z" for c in raw if c.isalpha())
    s = raw.replace(" ", "").upper().translate(MAP)
    if not (5 <= len(s) <= 100):
        return None, has_d
    if any(c not in AA20X for c in s):
        return None, has_d
    return s, has_d


def fasta_map(path: Path) -> dict[str, str]:
    out = {}
    for h, s in parse_fasta(path):
        sid = h.split()[0]
        s = s.replace(" ", "").upper()
        out[sid] = s
    return out


def run_search(query: Path, target: Path, out_m8: Path, tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    if out_m8.exists():
        out_m8.unlink()
    cmd = [
        str(MMSEQS),
        "easy-search",
        str(query),
        str(target),
        str(out_m8),
        str(tmp),
        "--min-seq-id",
        str(MIN_ID),
        "-c",
        str(COV),
        "--cov-mode",
        "1",
        "--threads",
        "8",
        "-s",
        "5.7",
        "--format-output",
        "query,target,pident,alnlen,qcov,tcov",
    ]
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def hit_queries(m8: Path) -> set[str]:
    q = set()
    if not m8.is_file() or m8.stat().st_size == 0:
        return q
    with m8.open() as f:
        for line in f:
            if line.strip():
                q.add(line.split("\t")[0])
    return q


def load_or_rebuild_novels(rng_unused):
    """Reuse Cohort 2 DBAASP novels if present; else rebuild like build_dbaasp_ood_split."""
    idx = OUT / "cohort2_index.csv"
    if idx.is_file():
        novels = []
        with idx.open() as f:
            for row in csv.DictReader(f):
                if row["y"] == "1":
                    novels.append((row["id"], row["seq"], int(row["has_d_aa"])))
        print(f"reused {len(novels)} DBAASP novels from cohort2_index.csv", flush=True)
        return novels
    raise SystemExit("missing cohort2_index.csv — run build_dbaasp_ood_split.py first")


def length_matched_sample(cands, target_lens, k, rng):
    bins = defaultdict(list)
    for sid, s, src in cands:
        bins[len(s)].append((sid, s, src))
    want = defaultdict(int)
    for L in target_lens:
        want[L] += 1
    total = sum(want.values()) or 1
    scaled = {L: max(0, round(k * n / total)) for L, n in want.items()}
    picked = []
    for L, n in sorted(scaled.items()):
        pool = bins.get(L, [])
        rng.shuffle(pool)
        take = min(n, len(pool))
        picked.extend(pool[:take])
        bins[L] = pool[take:]
    if len(picked) > k:
        rng.shuffle(picked)
        picked = picked[:k]
    if len(picked) < k:
        # fill from nearest lengths (±8), never dump 70–100 aa into a 14-aa problem
        rest = []
        tgt_med = sorted(target_lens)[len(target_lens) // 2]
        for L, pool in bins.items():
            if abs(L - tgt_med) <= 8:
                rest.extend(pool)
        rng.shuffle(rest)
        picked.extend(rest[: k - len(picked)])
    return picked[:k]


def main():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    train = fasta_map(TRAIN_FA)
    used = set(train.values())
    used.update(fasta_map(VAL_FA).values())
    used.update(fasta_map(TEST_FA).values())

    novels = load_or_rebuild_novels(rng)
    novel_seqs = {s for _, s, _ in novels}
    target_lens = [len(s) for _, s, _ in novels]
    print(
        f"DBAASP novels n={len(novels)} len median={sorted(target_lens)[len(target_lens)//2]}",
        flush=True,
    )

    # unused intact negatives
    intact_short = []
    long_parents = []
    seen = set(novel_seqs) | used
    for h, raw in parse_fasta(NEG_ALPHA):
        s, _ = clean_seq(raw)
        if s is None or s in seen:
            continue
        seen.add(s)
        sid = "NEG_" + h.split()[0]
        if 5 <= len(s) <= 30:
            intact_short.append((sid, s, "intact_unused"))
        elif len(s) >= PARENT_MIN_LEN:
            long_parents.append((sid, s))
    print(f"intact unused short<=30 n={len(intact_short)} long parents n={len(long_parents)}", flush=True)

    # drop long parents homologous to train (whole chain)
    pfa = CACHE / "long_parents.fasta"
    write_fasta(pfa, long_parents)
    tfa = CACHE / "train_target.fasta"
    write_fasta(tfa, list(train.items()))
    run_search(pfa, tfa, CACHE / "parents_vs_train.m8", CACHE / "tmp_par_train")
    par_hits = hit_queries(CACHE / "parents_vs_train.m8")
    parents_ok = [(i, s) for i, s in long_parents if i not in par_hits]
    print(f"long parents <30% to train n={len(parents_ok)}", flush=True)

    # windows
    lens_pool = target_lens[:]
    fragments = []
    frag_seen = set(seen)
    for pi, (pid, ps) in enumerate(parents_ok):
        for w in range(WINDOWS_PER_PARENT):
            L = rng.choice(lens_pool)
            if len(ps) < L:
                continue
            start = rng.randint(0, len(ps) - L)
            frag = ps[start : start + L]
            if frag in frag_seen or frag in used or frag in novel_seqs:
                continue
            if any(c not in AA20X for c in frag):
                continue
            frag_seen.add(frag)
            fragments.append((f"FRAG_{pid}_{start}_{L}", frag, "fragment"))
        if len(fragments) >= TARGET_SHORT_NEGS * 3:
            break
    print(f"raw fragments n={len(fragments)}", flush=True)

    # MMseqs walls on fragments vs train and vs DBAASP novels
    ffa = CACHE / "fragments.fasta"
    write_fasta(ffa, [(i, s) for i, s, _ in fragments])
    run_search(ffa, tfa, CACHE / "frag_vs_train.m8", CACHE / "tmp_frag_train")
    frag_tr = hit_queries(CACHE / "frag_vs_train.m8")
    fragments = [x for x in fragments if x[0] not in frag_tr]
    print(f"fragments after vs train n={len(fragments)}", flush=True)

    nfa = CACHE / "dbaasp_novels.fasta"
    write_fasta(nfa, [(i, s) for i, s, _ in novels])
    ffa2 = CACHE / "fragments_ok.fasta"
    write_fasta(ffa2, [(i, s) for i, s, _ in fragments])
    run_search(ffa2, nfa, CACHE / "frag_vs_dbaasp.m8", CACHE / "tmp_frag_pos")
    frag_pos = hit_queries(CACHE / "frag_vs_dbaasp.m8")
    fragments = [x for x in fragments if x[0] not in frag_pos]
    print(f"fragments after vs DBAASP n={len(fragments)}", flush=True)

    # intact shorts through same walls
    ifa = CACHE / "intact_short.fasta"
    write_fasta(ifa, [(i, s) for i, s, _ in intact_short])
    run_search(ifa, tfa, CACHE / "intact_vs_train.m8", CACHE / "tmp_int_train")
    int_tr = hit_queries(CACHE / "intact_vs_train.m8")
    intact_short = [x for x in intact_short if x[0] not in int_tr]
    ifa2 = CACHE / "intact_ok.fasta"
    write_fasta(ifa2, [(i, s) for i, s, _ in intact_short])
    run_search(ifa2, nfa, CACHE / "intact_vs_dbaasp.m8", CACHE / "tmp_int_pos")
    int_pos = hit_queries(CACHE / "intact_vs_dbaasp.m8")
    intact_short = [x for x in intact_short if x[0] not in int_pos]
    print(f"intact shorts after walls n={len(intact_short)}", flush=True)

    pool = intact_short + fragments
    k = min(len(novels), len(pool), max(len(intact_short) + len(fragments), TARGET_SHORT_NEGS))
    # 1:1 with novels if we have enough; else use all pool and downsample novels
    if len(pool) >= len(novels):
        neg_pick = length_matched_sample(pool, target_lens, len(novels), rng)
        pos_pick = novels
    else:
        neg_pick = length_matched_sample(pool, target_lens, len(pool), rng)
        rng.shuffle(novels)
        pos_pick = novels[: len(neg_pick)]
        print(f"WARNING: not enough negs; downsampled positives to {len(pos_pick)}", flush=True)

    recs, rows = [], []
    for i, s, has_d in pos_pick:
        recs.append((f"{i} LABEL=1 SRC=DBAASP DAA={int(has_d)}", s))
        rows.append({"id": i, "y": 1, "src": "dbaasp", "len": len(s), "has_d_aa": int(has_d), "seq": s})
    for i, s, src in neg_pick:
        recs.append((f"{i} LABEL=0 SRC={src.upper()}", s))
        rows.append({"id": i, "y": 0, "src": src, "len": len(s), "has_d_aa": 0, "seq": s})

    out_fa = OUT / "cohort2b_fair.fasta"
    write_fasta(out_fa, recs)
    with (OUT / "cohort2b_index.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "y", "src", "len", "has_d_aa", "seq"])
        w.writeheader()
        w.writerows(rows)

    pos_len = [r["len"] for r in rows if r["y"] == 1]
    neg_len = [r["len"] for r in rows if r["y"] == 0]
    pos_med = sorted(pos_len)[len(pos_len) // 2] if pos_len else None
    neg_med = sorted(neg_len)[len(neg_len) // 2] if neg_len else None
    n_frag = sum(1 for r in rows if r["src"] == "fragment")
    n_int = sum(1 for r in rows if r["y"] == 0 and r["src"] != "fragment")
    meta = {
        "n_total": len(rows),
        "n_pos": len(pos_len),
        "n_neg": len(neg_len),
        "n_neg_fragment": n_frag,
        "n_neg_intact": n_int,
        "pos_len_median": pos_med,
        "neg_len_median": neg_med,
        "len_median_gap": (None if pos_med is None or neg_med is None else abs(pos_med - neg_med)),
        "mmseqs": {"min_seq_id": MIN_ID, "coverage": COV, "cov_mode": 1},
        "seed": SEED,
        "fasta": str(out_fa.relative_to(ROOT)),
        "sha256": hashlib.sha256(out_fa.read_bytes()).hexdigest(),
        "limitation": "Most negatives are random windows from unused long UniProt-style non-AMPs, not assayed inactive peptides.",
        "note": "Fair-ish length-matched Cohort 2b. Do not overwrite locked 0.9515.",
    }
    (OUT / "cohort2b_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    if meta["len_median_gap"] is not None and meta["len_median_gap"] > 8:
        print("ERROR: length median gap > 8 aa — do not score until fixed", flush=True)
        sys.exit(2)
    if meta["n_neg"] < 2000:
        print("ERROR: fewer than 2000 negatives — do not pad with long seqs", flush=True)
        sys.exit(3)
    print("wrote", out_fa)


if __name__ == "__main__":
    main()
