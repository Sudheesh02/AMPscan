#!/usr/bin/env python3
"""Slide the locked AMPscan RF along a protein. Window scores, not a protein-level AMP call.

AmpGram-style scanning using OUR frozen forest, not the R AmpGram model.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services" / "predict_api"))

from run_baseline import featurize_many  # noqa: E402
from scoring import MAP, get_artifacts  # noqa: E402


def parse_fasta(path: Path):
    recs = []
    hdr, buf = None, []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    recs.append((hdr.split()[0], "".join(buf)))
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            recs.append((hdr.split()[0], "".join(buf)))
    return recs


def windows(seq: str, w: int, step: int):
    if len(seq) < w:
        return []
    out = []
    for start in range(0, len(seq) - w + 1, step):
        out.append((start + 1, start + w, seq[start : start + w]))  # 1-based
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Locked RF sliding window. Does NOT classify the full protein as AMP."
    )
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--window", type=int, default=25)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not (5 <= args.window <= 100):
        raise SystemExit("window must be 5–100 (RF input range)")
    if args.step < 1:
        raise SystemExit("step must be >= 1")

    art = get_artifacts()
    recs = parse_fasta(Path(args.fasta))
    rows = []
    skipped = 0
    for pid, raw in recs:
        s = raw.replace(" ", "").upper().translate(MAP)
        wins = windows(s, args.window, args.step)
        if not wins:
            skipped += 1
            continue
        seqs = [w[2] for w in wins]
        X = featurize_many(seqs)
        p_raw = art.rf.predict_proba(X)[:, 1]
        p_cal = 1.0 / (1.0 + np.exp(-np.clip(art.platt_a * p_raw + art.platt_b, -60, 60)))
        for (start, end, sub), p in zip(wins, p_cal):
            rows.append(
                {
                    "protein_id": pid,
                    "protein_len": len(s),
                    "start": start,
                    "end": end,
                    "window": args.window,
                    "seq": sub,
                    "p_ampscan_rf": float(p),
                    "note": "window score; not a protein-level AMP call",
                }
            )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(
        f"wrote {out} windows={len(rows)} proteins={len(recs)} skipped_short={skipped} "
        f"(window={args.window} step={args.step})",
        flush=True,
    )


if __name__ == "__main__":
    main()
