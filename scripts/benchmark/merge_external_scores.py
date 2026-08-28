#!/usr/bin/env python3
"""Join external-tool scores onto locked Cohort 1 labels. Does not retrain."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
from metrics_engine import summarize  # noqa: E402

OUT = ROOT / "reports" / "benchmarks"
CACHE = OUT / "cache"

TOOLS = [
    ("AMPscan RF (Platt)", "cohort_1_ampscan_scores.csv", "p_ampscan_rf", "ampscan_meta.txt"),
    ("AMPscan 1D-CNN (T)", "cohort_1_ampscan_scores.csv", "p_ampscan_cnn", "ampscan_meta.txt"),
    ("Macrel", "cohort_1_macrel_scores.csv", "p_macrel", "macrel_meta.txt"),
    ("AI4AMP PC6", "cohort_1_ai4amp_scores.csv", "p_ai4amp", "ai4amp_meta.txt"),
    ("AMPlify balanced", "cohort_1_amplify_scores.csv", "p_amplify", "amplify_meta.txt"),
    ("AmpGram", "cohort_1_ampgram_scores.csv", "p_ampgram", "ampgram_meta.txt"),
]


def parse_meta(path: Path):
    d = {}
    if not path.is_file():
        return d
    for line in path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def plot_roc(summaries: dict, path: Path, title: str):
    fig, ax = plt.subplots(figsize=(5.8, 4.6))
    for name, s in summaries.items():
        ax.plot(s["roc_fpr"], s["roc_tpr"], label=f"{name}  {s['roc_auc']:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=7)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    labels = pd.read_csv(OUT / "cohort_1_ampscan_scores.csv")
    ymap = dict(zip(labels["id"].astype(str), labels["y"].astype(int)))

    rows = []
    summaries = {}
    notes = []
    for name, csv_name, col, meta_name in TOOLS:
        path = OUT / csv_name
        if not path.is_file():
            notes.append(f"{name}: scores file missing ({csv_name}) — not run.")
            continue
        df = pd.read_csv(path)
        df["id"] = df["id"].astype(str)
        if col not in df.columns:
            notes.append(f"{name}: column {col} missing.")
            continue
        sub = df[["id", col]].dropna()
        sub["y"] = sub["id"].map(ymap)
        sub = sub.dropna(subset=["y"])
        if sub.empty:
            notes.append(f"{name}: no scored rows after NA drop.")
            continue
        y = sub["y"].to_numpy(dtype=int)
        p = sub[col].to_numpy(dtype=float)
        s = summarize(y, p)
        summaries[name] = s
        meta = parse_meta(CACHE / meta_name) if meta_name else {}
        wall = float(meta["wall_s"]) if "wall_s" in meta else None
        n_scored = int(s["n"])
        rec = {k: v for k, v in s.items() if k not in ("roc_fpr", "roc_tpr")}
        rec["model"] = name
        rec["wall_s"] = wall
        rec["seq_per_s"] = (round(n_scored / wall, 2) if wall and wall > 0 else None)
        rec["skip"] = int(meta.get("skip", 0)) if meta else (3230 - n_scored)
        rows.append(rec)
        notes.append(
            f"{name}: n={n_scored} skip={rec['skip']} ROC-AUC={s['roc_auc']:.4f} "
            f"acc={s['accuracy']:.4f} ECE={s['ece_15']:.4f}"
        )

    if not rows:
        raise SystemExit("no tool scores found")

    keep = [
        "model",
        "n",
        "skip",
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
    out_df = pd.DataFrame(rows)
    for c in keep:
        if c not in out_df.columns:
            out_df[c] = None
    out_df[keep].to_csv(OUT / "cohort_1_metrics.csv", index=False)
    (OUT / "cohort_1_metrics.json").write_text(out_df[keep].to_json(orient="records", indent=2))
    plot_roc(summaries, OUT / "01_cohort1_roc.png", "Cohort 1 — locked homology test ROC")

    md = [
        "# AMPscan v1.0 vs other AMP tools — Cohort 1",
        "",
        "Locked DRAMP/AMPlify homology test (`data/splits/test.fasta`), n = 3230 "
        "(1623 AMP / 1607 non-AMP). **No retraining.** Each external tool ran in its "
        "own environment; scores were joined here.",
        "",
        "Skip rules (tool-native, not ours):",
        "",
        "- Macrel / AMPlify: non-20 amino acids (48 sequences with X on this split).",
        "- AmpGram: length < 10 (200 sequences) and non-20 AA.",
        "- AI4AMP PC6: unknown letters or length > 200 (X is a valid pad token).",
        "",
        "| model | n | skip | acc | macro-F1 | MCC | ROC-AUC | PR-AUC | ECE-15 | seq/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        sps = r["seq_per_s"] if r["seq_per_s"] is not None else "—"
        skip = r.get("skip") if r.get("skip") is not None else "—"
        md.append(
            f"| {r['model']} | {r['n']} | {skip} | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | "
            f"{r['mcc']:.4f} | **{r['roc_auc']:.4f}** | {r['pr_auc']:.4f} | "
            f"{r['ece_15']:.4f} | {sps} |"
        )
    md += [
        "",
        "ROC figure: `01_cohort1_roc.png`.",
        "",
        "AMPscan RF ROC-AUC **0.9515** is the locked homology-test number. Accuracy "
        "**0.8765** is Platt-calibrated RF at 0.5 (locked table 0.8734 was uncalibrated).",
        "",
        "On this split AMPscan RF ranks first. Macrel is close on ROC (**0.949**) but "
        "conservative (acc **0.785**, ECE **0.204**). AMPlify is next (**0.928**). "
        "AI4AMP and AmpGram sit around **0.79** — usable, not competitive here.",
        "",
        "## Separate envs (what actually broke)",
        "",
        "- **AI4AMP**: original `requirements.txt` pins both TF 2.1 and TF-GPU 1.9. "
        "Used conda env `amp-tf` (Python 3.9, TF/Keras 2.10 CPU). Encoder imported "
        "`gensim` we did not need; adapter loads the PC6 table itself.",
        "- **AMPlify**: advertised TF 1.12 / Python 3.6. Same `amp-tf` env loaded the "
        "five balanced `.h5` weights through the cloned custom layers. RTX 5060 is too "
        "new for TF 2.10 CUDA, so this ran on CPU (~3.5 min).",
        "- **AmpGram**: system R could not compile `biogram` (needs `libgmp-dev`; no "
        "sudo). Conda env `amp-r` with prebuilt `r-gmp`. AmpGram's DESCRIPTION still "
        "Imports shiny/devtools; we sourced predict internals + `AmpGramModel`. "
        "3001 peptides × 13k n-gram regexes took **~54 min**.",
        "- **hemopi2**: hemolysis, not AMP vs non-AMP. Pickle is sklearn **1.3.1**; "
        "`amp-data` is 1.9.0 so it will not load there. Do not put it on this ROC.",
        "- **sAMPpred-GAT**: still skipped (>100 GB DBs).",
        "",
        "## Run log",
        "",
    ]
    md.extend(f"- {n}" for n in notes)
    md += [
        "",
        "## Not in this table",
        "",
        "- **hemopi2 / HemoPred**: hemolysis, not AMP vs non-AMP. Do not mix into this ROC.",
        "- **zswitten Antimicrobial-Peptides**: MIC regression (GRAMPA), different label.",
        "- **sAMPpred-GAT**: needs >100 GB BLAST/trRosetta databases. Still skipped.",
        "- DBAASP multi-task / TSI / pathogen radar: **not trained**, not AMPscan v1.",
        "",
        "Scripts: `scripts/benchmark/run_v1_benchmark.py` (AMPscan + Macrel), "
        "`scripts/benchmark/adapters/score_*.py|R`, `merge_external_scores.py`.",
    ]
    (OUT / "AMPscan_v1.0_benchmark_report.md").write_text("\n".join(md) + "\n")
    print("\n".join(notes))
    print("Wrote", OUT / "AMPscan_v1.0_benchmark_report.md")
    print(out_df[keep].to_string(index=False))


if __name__ == "__main__":
    main()
