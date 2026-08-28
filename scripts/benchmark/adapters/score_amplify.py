#!/usr/bin/env python3
"""Score locked homology test with AMPlify (BiLSTM+attention ensemble).

Run inside amp-tf (Keras 2 / TF 2.10) — same env as AI4AMP. Custom layers
are imported from the cloned AMPlify/src. Sequences with non-20 AA (incl. X)
or length outside [2, 200] are skipped, matching upstream AMPlify.py.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "AMPlify" / "src"
MODELS = ROOT / "AMPlify" / "models" / "balanced"
OUT = ROOT / "reports" / "benchmarks"
CACHE = OUT / "cache"
TEST_FA = Path(os.environ.get("AMP_BENCH_FASTA", str(ROOT / "data" / "splits" / "test.fasta")))
OUT_CSV = Path(os.environ.get("AMP_BENCH_OUT", str(OUT / "cohort_1_amplify_scores.csv")))
META_NAME = os.environ.get("AMP_BENCH_META", "amplify_meta.txt")
AA20 = set("ACDEFGHIKLMNPQRSTVWY")


def load_amplify_mod():
    spec = importlib.util.spec_from_file_location("amplify_cli", SRC / "AMPlify.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["amplify_cli"] = mod
    # AMPlify.py imports layers from the same directory
    sys.path.insert(0, str(SRC))
    spec.loader.exec_module(mod)
    return mod


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


def is_valid(s: str) -> bool:
    if not (2 <= len(s) <= 200):
        return False
    body = s[:-1] if s.endswith("*") else s
    return set(body) <= AA20


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    ids, seqs = parse_fasta(TEST_FA)
    valid_ix = [i for i, s in enumerate(seqs) if is_valid(s)]
    peptides = [seqs[i][:-1] if seqs[i].endswith("*") else seqs[i] for i in valid_ix]
    print(f"AMPlify n={len(ids)} valid={len(peptides)} skip={len(ids)-len(peptides)}", flush=True)

    amp = load_amplify_mod()
    weights = [str(MODELS / f"AMPlify_balanced_model_weights_{k}.h5") for k in range(1, 6)]
    for w in weights:
        if not Path(w).is_file():
            raise FileNotFoundError(w)

    t0 = time.perf_counter()
    models = amp.load_multi_model(weights, amp.build_amplify)
    scores = np.full(len(ids), np.nan, dtype=np.float64)
    if peptides:
        X = amp.one_hot_padding(peptides, amp.MAX_LEN)
        ens, _ = amp.ensemble(models, X)
        for i, p in zip(valid_ix, ens):
            scores[i] = float(p)
    elapsed = time.perf_counter() - t0

    rows = [{"id": i, "p_amplify": (None if np.isnan(p) else float(p))} for i, p in zip(ids, scores)]
    out_csv = OUT_CSV
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    (CACHE / META_NAME).write_text(
        f"wall_s={elapsed:.3f}\nskip={len(ids)-len(peptides)}\nn={len(ids)}\nscored={len(peptides)}\n"
    )
    print(f"wrote {out_csv} in {elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
