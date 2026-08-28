#!/usr/bin/env python3
"""Build Cohort 2: DBAASP peptides <30% ID to AMPscan train + matched non-AMPs.

Does not retrain. Does not mix DBAASP into AMPscan v1 weights.
MMseqs settings match the locked split: --min-seq-id 0.3 -c 0.8 --cov-mode 1.
"""
from __future__ import annotations

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
CACHE = ROOT / "reports" / "benchmarks" / "cache" / "dbaasp_ood"
TRAIN_FA = ROOT / "data" / "splits" / "train.fasta"
TEST_FA = ROOT / "data" / "splits" / "test.fasta"
VAL_FA = ROOT / "data" / "splits" / "val.fasta"
DBAASP_FA = ROOT / "DBAASP" / "master_DBAASP.fasta"
DBAASP_CSV = ROOT / "DBAASP" / "master_DBAASP.csv"
NEG_POOL = ROOT / "data" / "raw" / "AMPlify_non_AMP_train_imbalanced.fa"
MMSEQS = Path("/home/sudheesh02/miniforge3/envs/amp-data/bin/mmseqs")
SEED = 42
MIN_ID = 0.3
COV = 0.8


def clean_seq(raw: str):
    """Uppercase, B/Z/U/O/J→X, length 5–100, 20 AA + X only.

    Lowercase letters in DBAASP are D-amino acids. We case-fold (limitation).
    """
    has_d = any("a" <= c <= "z" for c in raw if c.isalpha())
    s = raw.replace(" ", "").upper().translate(MAP)
    if not (5 <= len(s) <= 100):
        return None, has_d
    if any(c not in AA20X for c in s):
        return None, has_d
    return s, has_d


def fasta_seqs(path: Path) -> dict[str, str]:
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
            if not line.strip():
                continue
            q.add(line.split("\t")[0])
    return q


def length_matched_sample(cands, target_lens, k, rng):
    """Sample k sequences matching the empirical length histogram of target_lens."""
    if k <= 0 or not cands:
        return []
    bins = defaultdict(list)
    for sid, s in cands:
        bins[len(s)].append((sid, s))
    want = defaultdict(int)
    for L in target_lens:
        want[L] += 1
    # scale histogram to k
    total = sum(want.values()) or 1
    scaled = {L: max(1, round(k * n / total)) for L, n in want.items()}
    # trim to k
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
    # fill remainder from nearest lengths
    if len(picked) < k:
        rest = [x for L in bins for x in bins[L]]
        rng.shuffle(rest)
        picked.extend(rest[: k - len(picked)])
    return picked[:k]


def main():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    train = fasta_seqs(TRAIN_FA)
    test = fasta_seqs(TEST_FA)
    val = fasta_seqs(VAL_FA)
    seen_exact = {s.upper() for s in list(train.values()) + list(test.values()) + list(val.values())}

    # DBAASP unique cleaned
    d_recs = parse_fasta(DBAASP_FA)
    pos = []  # (id, seq, has_d)
    dropped = {"len_or_aa": 0, "dup": 0, "exact_ampscan": 0}
    seen_seq = set()
    for h, raw in d_recs:
        sid = h.split()[0]
        s, has_d = clean_seq(raw)
        if s is None:
            dropped["len_or_aa"] += 1
            continue
        if s in seen_seq:
            dropped["dup"] += 1
            continue
        seen_seq.add(s)
        if s in seen_exact:
            dropped["exact_ampscan"] += 1
            continue
        pos.append((sid, s, has_d))
    print(
        f"DBAASP cleaned unique not-exact-in-AMPscan n={len(pos)} "
        f"dropped={dropped}",
        flush=True,
    )

    qfa = CACHE / "dbaasp_query.fasta"
    tfa = CACHE / "train_target.fasta"
    write_fasta(qfa, [(i, s) for i, s, _ in pos])
    write_fasta(tfa, list(train.items()))
    m8 = CACHE / "dbaasp_vs_train.m8"
    run_search(qfa, tfa, m8, CACHE / "tmp_search_pos")
    homologs = hit_queries(m8)
    novel = [(i, s, d) for i, s, d in pos if i not in homologs]
    print(f"DBAASP vs train 30%/80%: homologs={len(homologs)} novel={len(novel)}", flush=True)

    # Negative pool
    neg_all = []
    seen_n = set()
    for h, raw in parse_fasta(NEG_POOL):
        sid = "NEG_" + h.split()[0]
        s, _ = clean_seq(raw)
        if s is None or s in seen_n or s in seen_exact or s in seen_seq:
            continue
        seen_n.add(s)
        neg_all.append((sid, s))
    print(f"neg pool cleaned unused n={len(neg_all)}", flush=True)
    nfa = CACHE / "neg_query.fasta"
    write_fasta(nfa, neg_all)
    m8n = CACHE / "neg_vs_train.m8"
    run_search(nfa, tfa, m8n, CACHE / "tmp_search_neg_train")
    neg_h_train = hit_queries(m8n)
    neg_cand = [(i, s) for i, s in neg_all if i not in neg_h_train]
    print(f"neg after vs train n={len(neg_cand)}", flush=True)

    pfa = CACHE / "dbaasp_novel_pos.fasta"
    write_fasta(pfa, [(i, s) for i, s, _ in novel])
    nfa2 = CACHE / "neg_cand.fasta"
    write_fasta(nfa2, neg_cand)
    m8np = CACHE / "neg_vs_dbaasp_novel.m8"
    run_search(nfa2, pfa, m8np, CACHE / "tmp_search_neg_pos")
    neg_h_pos = hit_queries(m8np)
    neg_ok = [(i, s) for i, s in neg_cand if i not in neg_h_pos]
    print(f"neg after vs DBAASP-novel n={len(neg_ok)}", flush=True)

    k = min(len(novel), len(neg_ok))
    # keep all novel positives; match that many negatives
    target_lens = [len(s) for _, s, _ in novel]
    neg_pick = length_matched_sample(neg_ok, target_lens, k, rng)
    print(f"sampled negatives n={len(neg_pick)} (k={k})", flush=True)

    # labeled FASTA: LABEL=1 DBAASP novel, LABEL=0 matched neg
    recs = []
    rows = []
    for i, s, has_d in novel:
        recs.append((f"{i} LABEL=1 SRC=DBAASP DAA={int(has_d)}", s))
        rows.append({"id": i, "y": 1, "src": "dbaasp", "len": len(s), "has_d_aa": int(has_d), "seq": s})
    for i, s in neg_pick:
        recs.append((f"{i} LABEL=0 SRC=AMPLIFY_NEG", s))
        rows.append({"id": i, "y": 0, "src": "amplify_neg", "len": len(s), "has_d_aa": 0, "seq": s})

    out_fa = OUT / "cohort2.fasta"
    write_fasta(out_fa, recs)
    import csv

    with (OUT / "cohort2_index.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "y", "src", "len", "has_d_aa", "seq"])
        w.writeheader()
        w.writerows(rows)

    n_pos, n_neg = len(novel), len(neg_pick)
    n_d = sum(d for _, _, d in novel)
    sha = hashlib.sha256(out_fa.read_bytes()).hexdigest()
    meta = {
        "n_total": n_pos + n_neg,
        "n_pos_dbaasp_novel": n_pos,
        "n_neg_matched": n_neg,
        "n_pos_has_d_aa": n_d,
        "dropped": dropped,
        "n_dbaasp_homolog_to_train": len(homologs),
        "mmseqs": {
            "min_seq_id": MIN_ID,
            "coverage": COV,
            "cov_mode": 1,
            "target": "data/splits/train.fasta",
        },
        "negatives": "AMPlify_non_AMP_train_imbalanced.fa, unused in AMPscan, <30% to train and to DBAASP-novel",
        "d_aa_note": "DBAASP lowercase (D-aa) case-folded to L-aa for MMseqs/scoring; counted in n_pos_has_d_aa",
        "seed": SEED,
        "fasta": str(out_fa.relative_to(ROOT)),
        "sha256": sha,
        "note": "Independent OOD table. Do not mix into locked 0.9515.",
    }
    (OUT / "cohort2_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    print("wrote", out_fa)


if __name__ == "__main__":
    main()
