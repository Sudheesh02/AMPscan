#!/usr/bin/env python3
"""AMPscan v1.0 vs other AMP tools — Cohort 1 (locked homology test).

Does not retrain AMPscan. Does not train DBAASP multi-task heads.
Tier-1 tools that run in amp-data: AMPscan RF, AMPscan CNN, Macrel.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "macrel"))

from metrics_engine import summarize  # noqa: E402
from scoring import get_artifacts  # noqa: E402

OUT = ROOT / "reports" / "benchmarks"
CACHE = OUT / "cache"
TEST_FA = ROOT / "data" / "splits" / "test.fasta"


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


def score_ampscan(ids, seqs):
    art = get_artifacts()
    rows = []
    t0 = time.perf_counter()
    for i, s in zip(ids, seqs):
        _, p_rf = art.rf_calibrated(s)
        _, p_cnn = art.cnn_calibrated(s)
        rows.append((i, s, p_rf, p_cnn))
    elapsed = time.perf_counter() - t0
    return rows, elapsed


def score_macrel(ids, seqs):
    from macrel.AMP_features import fasta_features
    from macrel.AMP_predict import predict

    tmp = CACHE / "macrel_in.fasta"
    write_fasta(tmp, ids, seqs)
    t0 = time.perf_counter()
    feat = fasta_features(str(tmp))
    amp = str(ROOT / "macrel" / "macrel" / "data" / "models" / "AMP.onnx.gz")
    hemo = str(ROOT / "macrel" / "macrel" / "data" / "models" / "Hemo.onnx.gz")
    out = predict(amp, hemo, feat, keep_negatives=True)
    elapsed = time.perf_counter() - t0
    # index is headers
    pmap = {}
    if "AMP_probability" in out.columns:
        for acc, p in zip(out.index.astype(str), out["AMP_probability"]):
            pmap[acc.split()[0]] = float(p)
    skipped = 0
    rows = []
    for i, s in zip(ids, seqs):
        if i in pmap:
            rows.append((i, s, pmap[i]))
        else:
            skipped += 1
    return rows, elapsed, skipped


def plot_roc(summaries: dict, path: Path, title: str):
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    for name, s in summaries.items():
        ax.plot(s["roc_fpr"], s["roc_tpr"], label=f"{name}  {s['roc_auc']:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def table_row(name, s, elapsed, n_total):
    d = {k: v for k, v in s.items() if k not in ("roc_fpr", "roc_tpr")}
    d["model"] = name
    d["wall_s"] = round(elapsed, 3)
    d["seq_per_s"] = round(n_total / elapsed, 2) if elapsed else None
    return d


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    ids, y, seqs = parse_labeled_fasta(TEST_FA)
    print(f"Cohort 1 homology test n={len(ids)} pos={int(y.sum())} neg={int((y==0).sum())}")

    print("Scoring AMPscan RF + CNN...")
    amp_rows, amp_t = score_ampscan(ids, seqs)
    p_rf = np.array([r[2] for r in amp_rows])
    p_cnn = np.array([r[3] for r in amp_rows])
    # RF and CNN share wall time; split is not meaningful — report jointly and RF-only reuse
    s_rf = summarize(y, p_rf)
    s_cnn = summarize(y, p_cnn)
    print("  RF  ROC-AUC", round(s_rf["roc_auc"], 4), "acc", round(s_rf["accuracy"], 4))
    print("  CNN ROC-AUC", round(s_cnn["roc_auc"], 4))

    print("Scoring Macrel...")
    mac_rows, mac_t, mac_skip = score_macrel(ids, seqs)
    print(f"  macrel scored {len(mac_rows)} skipped {mac_skip} in {mac_t:.1f}s")
    id_to_y = dict(zip(ids, y))
    mac_y = np.array([id_to_y[r[0]] for r in mac_rows])
    mac_p = np.array([r[2] for r in mac_rows])
    s_mac = summarize(mac_y, mac_p)

    summaries = {
        "AMPscan RF (Platt)": s_rf,
        "AMPscan 1D-CNN (T)": s_cnn,
        "Macrel RF": s_mac,
    }
    plot_roc(summaries, OUT / "01_cohort1_roc.png", "Cohort 1 — locked homology test ROC")

    rows = [
        table_row("AMPscan RF (Platt)", s_rf, amp_t, len(ids)),
        table_row("AMPscan 1D-CNN (T)", s_cnn, amp_t, len(ids)),
        table_row("Macrel", s_mac, mac_t, len(mac_rows)),
    ]
    df = pd.DataFrame(rows)
    keep = [
        "model",
        "n",
        "accuracy",
        "macro_f1",
        "mcc",
        "roc_auc",
        "pr_auc",
        "ece_15",
        "brier",
        "sens_at_90spec",
        "wall_s",
        "seq_per_s",
        "tn",
        "fp",
        "fn",
        "tp",
    ]
    df[keep].to_csv(OUT / "cohort_1_metrics.csv", index=False)
    (OUT / "cohort_1_metrics.json").write_text(df[keep].to_json(orient="records", indent=2))

    pd.DataFrame(
        {
            "id": ids,
            "y": y,
            "p_ampscan_rf": p_rf,
            "p_ampscan_cnn": p_cnn,
        }
    ).to_csv(OUT / "cohort_1_ampscan_scores.csv", index=False)
    pd.DataFrame(mac_rows, columns=["id", "seq", "p_macrel"]).drop(columns=["seq"]).to_csv(
        OUT / "cohort_1_macrel_scores.csv", index=False
    )

    md = [
        "# AMPscan v1.0 vs other AMP tools — Cohort 1",
        "",
        "Locked DRAMP/AMPlify homology test (`data/splits/test.fasta`), n = 3230 "
        "(1623 AMP / 1607 non-AMP). **No retraining.** Macrel skips sequences with X "
        "or other non-canonical letters.",
        "",
        "Improvisation vs the 5-cohort Antigravity plan: run **tools that actually "
        "score AMP probability in `amp-data`** first. AI4AMP / zswitten need TensorFlow "
        "(not in this env). AMPlify needs TF 1.12. AmpGram/HemoPred need R. "
        "sAMPpred-GAT needs >100 GB DBs. DBAASP multi-task heads / TSI were **not** "
        "trained — they are not AMPscan v1.",
        "",
        "| model | n | acc | macro-F1 | MCC | ROC-AUC | PR-AUC | ECE-15 | seq/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        md.append(
            f"| {r['model']} | {r['n']} | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | "
            f"{r['mcc']:.4f} | **{r['roc_auc']:.4f}** | {r['pr_auc']:.4f} | "
            f"{r['ece_15']:.4f} | {r['seq_per_s']} |"
        )
    md += [
        "",
        f"Macrel skipped {mac_skip} sequences (non-canonical alphabet).",
        "",
        "ROC figure: `01_cohort1_roc.png`.",
        "",
        "AMPscan RF ROC-AUC should match the locked **0.9515** (rounding).",
        "",
        "Cohort 2–5 (DBAASP OOD, mutations, hemolysis vs HemoPI) need extra adapters "
        "and are **not** claimed in this snapshot.",
    ]
    (OUT / "AMPscan_v1.0_benchmark_report.md").write_text("\n".join(md) + "\n")
    print("Wrote", OUT / "AMPscan_v1.0_benchmark_report.md")
    print(df[keep].to_string(index=False))


if __name__ == "__main__":
    main()
