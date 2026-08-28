#!/usr/bin/env python3
"""Score locked AMPscan RF/CNN + Macrel on Cohort 2 DBAASP OOD. No retraining."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(ROOT / "macrel"))

from metrics_engine import summarize  # noqa: E402
from scoring import get_artifacts  # noqa: E402

FA = ROOT / "data" / "splits" / "dbaasp_ood" / "cohort2.fasta"
OUT = ROOT / "reports" / "benchmarks"
CACHE = OUT / "cache"


def parse_labeled_fasta(path: Path):
    ids, labels, seqs = [], [], []
    hdr, buf = None, []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    ids.append(hdr.split()[0])
                    labels.append(1 if "LABEL=1" in hdr else 0)
                    seqs.append("".join(buf).upper())
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            ids.append(hdr.split()[0])
            labels.append(1 if "LABEL=1" in hdr else 0)
            seqs.append("".join(buf).upper())
    return ids, np.asarray(labels, dtype=int), seqs


def write_fasta(path: Path, ids, seqs):
    with path.open("w", encoding="utf-8") as f:
        for i, s in zip(ids, seqs):
            f.write(f">{i}\n{s}\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    ids, y, seqs = parse_labeled_fasta(FA)
    print(f"Cohort 2 n={len(ids)} pos={int(y.sum())} neg={int((y==0).sum())}", flush=True)

    art = get_artifacts()
    t0 = time.perf_counter()
    p_rf, p_cnn = [], []
    for i, s in enumerate(seqs):
        _, a = art.rf_calibrated(s)
        _, b = art.cnn_calibrated(s)
        p_rf.append(a)
        p_cnn.append(b)
        if (i + 1) % 1000 == 0:
            print(f"  AMPscan {i+1}/{len(seqs)}", flush=True)
    amp_t = time.perf_counter() - t0
    p_rf = np.asarray(p_rf)
    p_cnn = np.asarray(p_cnn)
    pd.DataFrame({"id": ids, "y": y, "p_ampscan_rf": p_rf, "p_ampscan_cnn": p_cnn}).to_csv(
        OUT / "cohort_2_ampscan_scores.csv", index=False
    )
    (CACHE / "cohort2_ampscan_meta.txt").write_text(f"wall_s={amp_t:.3f}\nskip=0\nn={len(ids)}\n")
    print("AMPscan done", amp_t, "RF", summarize(y, p_rf)["roc_auc"], flush=True)

    from macrel.AMP_features import fasta_features
    from macrel.AMP_predict import predict

    tmp = CACHE / "cohort2_macrel_in.fasta"
    write_fasta(tmp, ids, seqs)
    t0 = time.perf_counter()
    feat = fasta_features(str(tmp))
    amp = str(ROOT / "macrel" / "macrel" / "data" / "models" / "AMP.onnx.gz")
    hemo = str(ROOT / "macrel" / "macrel" / "data" / "models" / "Hemo.onnx.gz")
    out = predict(amp, hemo, feat, keep_negatives=True)
    mac_t = time.perf_counter() - t0
    pmap = {}
    if "AMP_probability" in out.columns:
        for acc, p in zip(out.index.astype(str), out["AMP_probability"]):
            pmap[acc.split()[0]] = float(p)
    rows, skip = [], 0
    for i, s in zip(ids, seqs):
        if i in pmap:
            rows.append((i, pmap[i]))
        else:
            skip += 1
    pd.DataFrame(rows, columns=["id", "p_macrel"]).to_csv(OUT / "cohort_2_macrel_scores.csv", index=False)
    (CACHE / "cohort2_macrel_meta.txt").write_text(
        f"wall_s={mac_t:.3f}\nskip={skip}\nn={len(ids)}\nscored={len(rows)}\n"
    )
    print(f"Macrel scored {len(rows)} skip {skip} in {mac_t:.1f}s", flush=True)

    s_rf = summarize(y, p_rf)
    print(json.dumps({k: v for k, v in s_rf.items() if k not in ("roc_fpr", "roc_tpr")}, indent=2))


if __name__ == "__main__":
    main()
