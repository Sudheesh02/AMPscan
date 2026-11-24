#!/usr/bin/env python3
"""Build length-matched homology splits (v2) to eliminate the 20aa vs 61aa confounder.

Preserves v1.1 homology split assignments for positives, samples length-matched
negatives in 5-aa bins from existing splits + AMPlify_non_AMP_*_imbalanced.fa,
and guarantees zero exact-sequence overlap across splits or with DBAASP OOD cohorts.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPLITS_V1 = ROOT / "data" / "splits"
SPLITS_V2 = ROOT / "data" / "splits_v2"
RAW_DIR = ROOT / "data" / "raw"
OOD_DIR = SPLITS_V1 / "dbaasp_ood"

AA20X = set("ACDEFGHIKLMNPQRSTVWXY")
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})
SEED = 42


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        return []
    recs: list[tuple[str, str]] = []
    hdr: str | None = None
    buf: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    recs.append((hdr, "".join(buf).strip().upper().translate(MAP)))
                hdr = line[1:].strip()
                buf = []
            else:
                buf.append(line.strip())
    if hdr is not None:
        recs.append((hdr, "".join(buf).strip().upper().translate(MAP)))
    return recs


def valid_seq(seq: str) -> bool:
    return 5 <= len(seq) <= 100 and all(c in AA20X for c in seq)


def write_fasta(path: Path, recs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for hdr, seq in recs:
            f.write(f">{hdr}\n{seq}\n")


def length_bin(seq: str) -> int:
    return (len(seq) - 5) // 5


def verify_splits(splits_dir: Path, ood_seqs: set[str]) -> dict:
    stats: dict = {}
    seen_by_split: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        recs = parse_fasta(splits_dir / f"{split}.fasta")
        pos = [s for h, s in recs if "LABEL=1" in h]
        neg = [s for h, s in recs if "LABEL=0" in h]
        seen_by_split[split] = {s for _, s in recs}
        med_pos = float(np.median([len(s) for s in pos])) if pos else 0.0
        med_neg = float(np.median([len(s) for s in neg])) if neg else 0.0
        if abs(med_pos - med_neg) > 2.0:
            raise AssertionError(f"{split}: median length mismatch pos={med_pos} vs neg={med_neg}")
        ood_hit = len(seen_by_split[split] & ood_seqs)
        if ood_hit:
            raise AssertionError(f"{split}: {ood_hit} sequences overlap with DBAASP OOD cohorts")
        stats[split] = {
            "n": len(recs),
            "n_pos": len(pos),
            "n_neg": len(neg),
            "median_len_pos": med_pos,
            "median_len_neg": med_neg,
        }
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        ov = len(seen_by_split[a] & seen_by_split[b])
        if ov:
            raise AssertionError(f"overlap between {a} and {b}: {ov}")
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Build length-matched v2 homology splits")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    ood_seqs: set[str] = set()
    for name in ("cohort2.fasta", "cohort2b_fair.fasta"):
        for _, seq in parse_fasta(OOD_DIR / name):
            ood_seqs.add(seq)

    if args.verify_only:
        stats = verify_splits(SPLITS_V2, ood_seqs)
        print(json.dumps(stats, indent=2))
        return

    rng = random.Random(SEED)

    # 1. Load v1.1 positives per split (excluding any accidental OOD overlap)
    pos_by_split: dict[str, list[tuple[str, str]]] = {}
    neg_by_split: dict[str, list[tuple[str, str]]] = {}
    used_seqs: set[str] = set(ood_seqs)

    for split in ("train", "val", "test"):
        pos_recs, neg_recs = [], []
        for hdr, seq in parse_fasta(SPLITS_V1 / f"{split}.fasta"):
            if not valid_seq(seq) or seq in used_seqs:
                continue
            used_seqs.add(seq)
            if "LABEL=1" in hdr:
                pos_recs.append((hdr, seq))
            else:
                neg_recs.append((hdr, seq))
        pos_by_split[split] = pos_recs
        neg_by_split[split] = neg_recs

    # 2. Load extra AMPlify negative pool (deduplicated against all v1.1 & OOD seqs)
    extra_neg_pool: list[tuple[str, str]] = []
    for fname in ("AMPlify_non_AMP_train_imbalanced.fa", "AMPlify_non_AMP_test_imbalanced.fa"):
        for hdr, seq in parse_fasta(RAW_DIR / fname):
            if not valid_seq(seq) or seq in used_seqs:
                continue
            used_seqs.add(seq)
            tid = hdr.split()[0]
            extra_neg_pool.append((f"NEG_AMPLIFY_{tid} LABEL=0", seq))
    rng.shuffle(extra_neg_pool)

    # Partition extra negatives 70 / 15 / 15 across train / val / test so splits stay disjoint
    n_tot = len(extra_neg_pool)
    n_tr = int(0.70 * n_tot)
    n_va = int(0.85 * n_tot)
    extra_by_split = {
        "train": extra_neg_pool[:n_tr],
        "val": extra_neg_pool[n_tr:n_va],
        "test": extra_neg_pool[n_va:],
    }

    # 3. For each split, bin positives by 5-aa length and match negatives 1:1 per bin
    for split in ("train", "val", "test"):
        pos_bins: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for rec in pos_by_split[split]:
            pos_bins[length_bin(rec[1])].append(rec)

        neg_bins_primary: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for rec in neg_by_split[split]:
            neg_bins_primary[length_bin(rec[1])].append(rec)

        neg_bins_extra: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for rec in extra_by_split[split]:
            neg_bins_extra[length_bin(rec[1])].append(rec)

        matched_pos: list[tuple[str, str]] = []
        matched_neg: list[tuple[str, str]] = []

        for b in sorted(pos_bins):
            p_list = pos_bins[b]
            n_list = neg_bins_primary[b]
            rng.shuffle(n_list)
            e_list = neg_bins_extra[b]
            rng.shuffle(e_list)
            pool = n_list + e_list
            k = min(len(p_list), len(pool))
            matched_pos.extend(p_list[:k])
            matched_neg.extend(pool[:k])

        combined = matched_pos + matched_neg
        rng.shuffle(combined)
        write_fasta(SPLITS_V2 / f"{split}.fasta", combined)

    stats = verify_splits(SPLITS_V2, ood_seqs)
    meta = {
        "kind": "homology_length_matched_v2",
        "seed": SEED,
        "bin_width_aa": 5,
        "assertions_passed": True,
        "splits": stats,
    }
    (SPLITS_V2 / "split_stats_v2.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
