#!/usr/bin/env python3
"""Score locked homology test with AI4AMP PC6 (Keras h5). Run inside amp-tf.

  conda run -n amp-tf python scripts/benchmark/adapters/score_ai4amp.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
AI4 = ROOT / "AI4AMP_predictor"

from keras.models import load_model  # noqa: E402


def amino_encode_table_6(path=None):
    """PC6 z-scored table from AI4AMP (same as PC6_encoding.amino_encode_table_6)."""
    path = Path(path or AI4 / "PC6" / "6-pc")
    df = pd.read_csv(path, sep=" ", index_col=0)
    cols = ["H1", "V", "P1", "Pl", "PKa", "NCI"]
    z = (df[cols] - df[cols].mean()) / df[cols].std(ddof=1)
    amino = list("ACDEFGHIKLMNPQRSTVWY")
    table = {aa: list(z.loc[aa].astype(float)) for aa in amino}
    table["X"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return table

OUT = ROOT / "reports" / "benchmarks"
CACHE = OUT / "cache"
TEST_FA = Path(os.environ.get("AMP_BENCH_FASTA", str(ROOT / "data" / "splits" / "test.fasta")))
OUT_CSV = Path(os.environ.get("AMP_BENCH_OUT", str(OUT / "cohort_1_ai4amp_scores.csv")))
META_NAME = os.environ.get("AMP_BENCH_META", "ai4amp_meta.txt")
PAD = 200
AA_OK = set("ACDEFGHIKLMNPQRSTVWYX")


def parse_fasta(path: Path):
    ids, seqs = [], []
    hdr, buf = None, []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    ids.append(hdr.split()[0])
                    seqs.append("".join(buf).upper())
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            ids.append(hdr.split()[0])
            seqs.append("".join(buf).upper())
    return ids, seqs


def encode(seqs, table):
    """PC6 encode, pad to 200 with X. Skip seqs with unknown letters or len>200."""
    X = np.zeros((len(seqs), PAD, 6), dtype=np.float32)
    valid = np.zeros(len(seqs), dtype=bool)
    for i, s in enumerate(seqs):
        if not s or len(s) > PAD or any(c not in AA_OK for c in s):
            continue
        padded = s + "X" * (PAD - len(s))
        X[i] = np.asarray([table[c] for c in padded], dtype=np.float32)
        valid[i] = True
    return X, valid


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    ids, seqs = parse_fasta(TEST_FA)
    table = amino_encode_table_6()
    X, valid = encode(seqs, table)
    n_skip = int((~valid).sum())
    print(f"AI4AMP n={len(ids)} skip={n_skip}", flush=True)

    model_path = AI4 / "model" / "PC6_final_8.h5"
    t0 = time.perf_counter()
    model = load_model(str(model_path), compile=False)
    scores = np.full(len(ids), np.nan, dtype=np.float64)
    if valid.any():
        pred = model.predict(X[valid], batch_size=64, verbose=1)
        pred = np.asarray(pred).reshape(-1)
        scores[valid] = pred
    elapsed = time.perf_counter() - t0

    rows = [{"id": i, "p_ai4amp": (None if np.isnan(p) else float(p))} for i, p in zip(ids, scores)]
    out_csv = OUT_CSV
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    meta = CACHE / META_NAME
    meta.write_text(f"wall_s={elapsed:.3f}\nskip={n_skip}\nn={len(ids)}\nscored={int(valid.sum())}\n")
    print(f"wrote {out_csv} in {elapsed:.1f}s skip={n_skip}", flush=True)


if __name__ == "__main__":
    main()
