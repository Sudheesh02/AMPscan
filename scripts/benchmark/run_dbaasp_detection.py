#!/usr/bin/env python3
"""DBAASP exact-novelty detection with locked AMPscan RF. Not a ROC (all positives)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))
sys.path.insert(0, str(ROOT / "scripts"))
from scoring import AA20X, MAP, get_artifacts  # noqa: E402

OUT = ROOT / "reports" / "benchmarks"


def parse_fasta(path: Path):
    ids, seqs = [], []
    hdr, buf = None, []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    ids.append(hdr.split()[0])
                    seqs.append("".join(buf))
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            ids.append(hdr.split()[0])
            seqs.append("".join(buf))
    return ids, seqs


def clean(s: str) -> str | None:
    s = s.replace(" ", "").upper().translate(MAP)
    if not (5 <= len(s) <= 100):
        return None
    if any(c not in AA20X for c in s):
        return None
    return s


def main():
    train_ids, train_seqs = parse_fasta(ROOT / "data" / "splits" / "train.fasta")
    test_ids, test_seqs = parse_fasta(ROOT / "data" / "splits" / "test.fasta")
    train_set = {s.upper() for s in train_seqs}
    test_set = {s.upper() for s in test_seqs}
    d_ids, d_seqs = parse_fasta(ROOT / "DBAASP" / "master_DBAASP.fasta")
    seen = set()
    novel, overlap_train, overlap_test, dropped = 0, 0, 0, 0
    novel_seqs = []
    for i, raw in zip(d_ids, d_seqs):
        s = clean(raw)
        if s is None:
            dropped += 1
            continue
        if s in seen:
            continue
        seen.add(s)
        if s in train_set:
            overlap_train += 1
        elif s in test_set:
            overlap_test += 1
        else:
            novel += 1
            novel_seqs.append((i, s))

    art = get_artifacts()
    ps = []
    for _, s in novel_seqs:
        _, p = art.rf_calibrated(s)
        ps.append(p)
    ps = np.array(ps)
    called = int((ps >= 0.5).sum())
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {
        "dbaasp_fasta_records": len(d_seqs),
        "unique_clean_5_100": len(seen),
        "exact_in_ampscan_train": overlap_train,
        "exact_in_ampscan_test": overlap_test,
        "exact_novel": novel,
        "novel_rf_n": int(len(ps)),
        "novel_rf_called_amp": called,
        "novel_rf_detection_rate": float(called / len(ps)) if len(ps) else None,
        "novel_rf_mean_p": float(ps.mean()) if len(ps) else None,
        "novel_rf_median_p": float(np.median(ps)) if len(ps) else None,
        "note": "DBAASP entries treated as AMP-like catalog peptides, not a balanced ROC set. Exact identity only (not 30% MMseqs).",
    }
    import json

    (OUT / "dbaasp_exact_novelty.json").write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
