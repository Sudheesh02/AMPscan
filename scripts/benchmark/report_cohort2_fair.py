#!/usr/bin/env python3
"""Write Cohort 2b fair report. Headline is length-matched; 0.993 stays in the attic."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
from metrics_engine import summarize  # noqa: E402

OUT = ROOT / "reports" / "benchmarks"
META = ROOT / "data" / "splits" / "dbaasp_ood" / "cohort2b_meta.json"

TOOLS = [
    ("AMPscan RF (Platt)", "cohort_2b_ampscan_scores.csv", "p_ampscan_rf", "cohort2b_ampscan_meta.txt"),
    ("AMPscan 1D-CNN (T)", "cohort_2b_ampscan_scores.csv", "p_ampscan_cnn", "cohort2b_ampscan_meta.txt"),
    ("Macrel", "cohort_2b_macrel_scores.csv", "p_macrel", "cohort2b_macrel_meta.txt"),
    ("AI4AMP PC6", "cohort_2b_ai4amp_scores.csv", "p_ai4amp", "cohort2b_ai4amp_meta.txt"),
    ("AMPlify balanced", "cohort_2b_amplify_scores.csv", "p_amplify", "cohort2b_amplify_meta.txt"),
]


def parse_meta(path: Path):
    d = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def main():
    meta = json.loads(META.read_text()) if META.is_file() else {}
    labels = pd.read_csv(OUT / "cohort_2b_ampscan_scores.csv")
    labels["id"] = labels["id"].astype(str)
    ymap = dict(zip(labels["id"], labels["y"].astype(int)))
    idx_path = ROOT / "data" / "splits" / "dbaasp_ood" / "cohort2b_index.csv"
    idx = pd.read_csv(idx_path) if idx_path.is_file() else None

    rows, summaries = [], {}
    for name, csv_name, col, meta_name in TOOLS:
        path = OUT / csv_name
        if not path.is_file():
            print("missing", csv_name)
            continue
        df = pd.read_csv(path)
        df["id"] = df["id"].astype(str)
        sub = df[["id", col]].dropna()
        sub["y"] = sub["id"].map(ymap)
        sub = sub.dropna(subset=["y"])
        s = summarize(sub["y"].to_numpy(dtype=int), sub[col].to_numpy(dtype=float))
        summaries[name] = s
        md = parse_meta(OUT / "cache" / meta_name)
        rec = {k: v for k, v in s.items() if k not in ("roc_fpr", "roc_tpr")}
        rec["model"] = name
        rec["skip"] = int(md.get("skip", 0))
        rec["wall_s"] = float(md["wall_s"]) if "wall_s" in md else None
        rows.append(rec)
        print(f"{name} n={s['n']} roc={s['roc_auc']:.4f} acc={s['accuracy']:.4f}")

    if summaries:
        fig, ax = plt.subplots(figsize=(5.8, 4.6))
        for name, s in summaries.items():
            ax.plot(s["roc_fpr"], s["roc_tpr"], label=f"{name}  {s['roc_auc']:.3f}")
        ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title("Cohort 2b — length-matched DBAASP OOD (fragment negs)")
        ax.legend(loc="lower right", fontsize=7)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        fig.tight_layout()
        fig.savefig(OUT / "02b_cohort2b_roc.png", dpi=180)
        plt.close(fig)

    pos_med = meta.get("pos_len_median")
    neg_med = meta.get("neg_len_median")
    md = [
        "# Cohort 2b — length-matched DBAASP OOD (fair-ish)",
        "",
        "**Locked AMPscan v1 metric is still Cohort 1 RF ROC-AUC 0.9515.**",
        "",
        "Negatives are mostly **random windows** from unused long UniProt-style non-AMPs "
        f"(`n_neg_fragment={meta.get('n_neg_fragment')}`, intact unused shorts "
        f"`n_neg_intact={meta.get('n_neg_intact')}`). Not experimentally inactive peptides.",
        "",
        f"Length medians: DBAASP pos **{pos_med}** vs neg **{neg_med}** "
        f"(gap {meta.get('len_median_gap')}). Gap must be ≤ 8 aa.",
        "",
        "MMseqs vs AMPscan train and vs DBAASP novels: `--min-seq-id 0.3 -c 0.8 --cov-mode 1`.",
        "",
        "| model | n | skip | acc | MCC | ROC-AUC | PR-AUC | ECE-15 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        md.append(
            f"| {r['model']} | {r['n']} | {r.get('skip', 0)} | {r['accuracy']:.4f} | "
            f"{r['mcc']:.4f} | **{r['roc_auc']:.4f}** | {r['pr_auc']:.4f} | {r['ece_15']:.4f} |"
        )
    md += [
        "",
        "ROC: `02b_cohort2b_roc.png`.",
        "",
        "## Do not quote",
        "",
        "The earlier full Cohort 2 RF ROC **0.9935** (`cohort_2_dbaasp_ood_results.md`) used "
        "14-aa DBAASP vs 76-aa leftovers. That table is length-confounded.",
        "",
        "If 2b ROC is still ~0.99, the fragment windows are still too easy (composition). "
        "Say that. Do not call it SOTA.",
    ]
    if idx is not None:
        md += [
            "",
            "## Length check",
            "",
            idx.groupby("y")["len"].describe().to_string(),
        ]
    (OUT / "cohort_2b_fair_results.md").write_text("\n".join(md) + "\n")
    print("wrote", OUT / "cohort_2b_fair_results.md")


if __name__ == "__main__":
    main()
