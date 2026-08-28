#!/usr/bin/env python3
"""Batched AMPscan RF+CNN on a labeled FASTA. Frozen weights. Same Platt / T as the API.

Does not retrain. Does not change 425-D features.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services" / "predict_api"))
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))

from run_baseline import featurize_many  # noqa: E402
from scoring import get_artifacts, one_hot, sigmoid  # noqa: E402


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


def score_batched(seqs, cnn_batch=256):
    art = get_artifacts()
    t0 = time.perf_counter()
    X = featurize_many(seqs)
    p_raw = art.rf.predict_proba(X)[:, 1]
    p_rf = 1.0 / (1.0 + np.exp(-np.clip(art.platt_a * p_raw + art.platt_b, -60.0, 60.0)))
    t_rf = time.perf_counter() - t0

    t1 = time.perf_counter()
    p_cnn = np.empty(len(seqs), dtype=np.float64)
    art.cnn.eval()
    with torch.no_grad():
        for i in range(0, len(seqs), cnn_batch):
            chunk = seqs[i : i + cnn_batch]
            x = torch.from_numpy(np.stack([one_hot(s) for s in chunk])).to(art.device)
            logit = art.cnn(x).cpu().numpy().reshape(-1)
            p_cnn[i : i + len(chunk)] = [sigmoid(float(z) / art.t_cnn) for z in logit]
    t_cnn = time.perf_counter() - t1
    return p_rf, p_cnn, t_rf, t_cnn


def score_sequential(seqs, n_max=None):
    art = get_artifacts()
    use = seqs if n_max is None else seqs[:n_max]
    t0 = time.perf_counter()
    p_rf, p_cnn = [], []
    for s in use:
        _, a = art.rf_calibrated(s)
        _, b = art.cnn_calibrated(s)
        p_rf.append(a)
        p_cnn.append(b)
    return np.asarray(p_rf), np.asarray(p_cnn), time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser(description="Batched locked AMPscan scoring")
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", default=None, help="existing scores CSV with p_ampscan_rf, p_ampscan_cnn")
    ap.add_argument("--speed-md", default=None)
    ap.add_argument("--seq-sample", type=int, default=400, help="sequential timing sample")
    args = ap.parse_args()

    fasta = Path(args.fasta)
    ids, y, seqs = parse_labeled_fasta(fasta)
    print(f"n={len(ids)} pos={int(y.sum())}", flush=True)

    p_rf, p_cnn, t_rf, t_cnn = score_batched(seqs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id": ids, "y": y, "p_ampscan_rf": p_rf, "p_ampscan_cnn": p_cnn}).to_csv(out, index=False)
    print(f"batched RF {t_rf:.2f}s CNN {t_cnn:.2f}s -> {out}", flush=True)

    max_rf = max_cnn = None
    if args.verify:
        ref = pd.read_csv(args.verify)
        ref["id"] = ref["id"].astype(str)
        got = pd.DataFrame({"id": ids, "p_ampscan_rf": p_rf, "p_ampscan_cnn": p_cnn})
        m = ref.merge(got, on="id", suffixes=("_ref", "_got"))
        if len(m) != len(ref):
            raise SystemExit(f"verify join size {len(m)} != {len(ref)}")
        max_rf = float(np.max(np.abs(m["p_ampscan_rf_ref"] - m["p_ampscan_rf_got"])))
        max_cnn = float(np.max(np.abs(m["p_ampscan_cnn_ref"] - m["p_ampscan_cnn_got"])))
        print(f"max |Δ| RF={max_rf:.2e} CNN={max_cnn:.2e}", flush=True)
        if max_rf >= 1e-5 or max_cnn >= 1e-5:
            raise SystemExit("batched scores drifted from locked CSV — do not proceed")

    n_s = min(args.seq_sample, len(seqs))
    _, _, t_seq = score_sequential(seqs, n_max=n_s)
    seq_per_s = n_s / t_seq if t_seq else None
    bat_per_s = len(seqs) / (t_rf + t_cnn) if (t_rf + t_cnn) else None
    factor = (bat_per_s / seq_per_s) if seq_per_s and bat_per_s else None
    print(f"sequential {n_s} in {t_seq:.2f}s ({seq_per_s:.2f}/s)  batched {bat_per_s:.2f}/s  factor={factor}", flush=True)

    if args.speed_md:
        md = Path(args.speed_md)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(
            "\n".join(
                [
                    "# Batched vs sequential AMPscan scoring",
                    "",
                    "Frozen RF Platt + CNN T. No retrain. RF is CPU (`n_jobs=4`).",
                    "",
                    f"- FASTA: `{fasta}` n={len(seqs)}",
                    f"- Sequential sample n={n_s}: {t_seq:.2f}s, **{seq_per_s:.2f} seq/s**",
                    f"- Batched full n={len(seqs)}: RF {t_rf:.2f}s + CNN {t_cnn:.2f}s, **{bat_per_s:.2f} seq/s**",
                    f"- Speedup factor (batched/sequential): **{factor:.2f}×**" if factor else "- Speedup: n/a",
                    f"- Verify max |Δ| vs `{args.verify}`: RF {max_rf} CNN {max_cnn}"
                    if args.verify
                    else "- No verify CSV",
                    "",
                    "If factor < 1, the batch path is wrong. Do not claim GPU 20×.",
                    "",
                ]
            )
            + "\n"
        )
        print("wrote", md, flush=True)


if __name__ == "__main__":
    main()
