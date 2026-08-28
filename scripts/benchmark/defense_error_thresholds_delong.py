#!/usr/bin/env python3
"""Cohort 1 defense ammo: error analysis, operating points, bootstrap AUC diffs.

Frozen scores only. Does not retrain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from run_baseline import aromatic_fraction, gravy, hydrophobic_moment, net_charge_pH7  # noqa: E402

OUT = ROOT / "reports" / "benchmarks"
SPLITS = ROOT / "data" / "splits"
SEED = 42
N_BOOT = 2000
THRESH = (0.5, 0.8, 0.9, 0.95)


def parse_test():
    ids, y, seqs = [], [], []
    hdr, buf = None, []
    path = SPLITS / "test.fasta"
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    ids.append(hdr.split()[0])
                    y.append(1 if "LABEL=1" in hdr else 0)
                    seqs.append("".join(buf).upper())
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            ids.append(hdr.split()[0])
            y.append(1 if "LABEL=1" in hdr else 0)
            seqs.append("".join(buf).upper())
    return pd.DataFrame({"id": ids, "y": y, "seq": seqs})


def phys(seq: str):
    return {
        "len": len(seq),
        "charge": float(net_charge_pH7(seq)),
        "gravy": float(gravy(seq)),
        "muh": float(hydrophobic_moment(seq)),
        "aromatic": float(aromatic_fraction(seq)),
        "n_cys": seq.count("C"),
        "n_kr": seq.count("K") + seq.count("R"),
        "n_de": seq.count("D") + seq.count("E"),
    }


def operating_rows(name, y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    rows = []
    for t in THRESH:
        pred = (p >= t).astype(int)
        rows.append(
            {
                "model": name,
                "threshold": t,
                "n": int(len(y)),
                "n_called_amp": int(pred.sum()),
                "precision": float(precision_score(y, pred, zero_division=0)),
                "recall": float(recall_score(y, pred, zero_division=0)),
                "specificity": float(((y == 0) & (pred == 0)).sum() / max((y == 0).sum(), 1)),
                "roc_auc": float(roc_auc_score(y, p)),
                "pr_auc": float(average_precision_score(y, p)),
            }
        )
    return rows


def bootstrap_auc_diff(y, p_a, p_b, rng, n=N_BOOT):
    """Paired bootstrap of AUC(A)-AUC(B). Returns mean, 95% CI, P(diff>0)."""
    y = np.asarray(y, dtype=int)
    p_a = np.asarray(p_a, dtype=float)
    p_b = np.asarray(p_b, dtype=float)
    n_obs = len(y)
    diffs = np.empty(n)
    for i in range(n):
        ix = rng.randint(0, n_obs, n_obs)
        diffs[i] = roc_auc_score(y[ix], p_a[ix]) - roc_auc_score(y[ix], p_b[ix])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "n": int(n_obs),
        "auc_a": float(roc_auc_score(y, p_a)),
        "auc_b": float(roc_auc_score(y, p_b)),
        "diff": float(roc_auc_score(y, p_a) - roc_auc_score(y, p_b)),
        "boot_mean_diff": float(diffs.mean()),
        "ci95_lo": float(lo),
        "ci95_hi": float(hi),
        "frac_boot_diff_gt0": float((diffs > 0).mean()),
        "ci_excludes_0": bool(lo > 0 or hi < 0),
        "n_boot": n,
        "seed": SEED,
    }


def summarize_group(df, cols):
    out = {}
    for c in cols:
        out[f"{c}_mean"] = float(df[c].mean())
        out[f"{c}_median"] = float(df[c].median())
    return out


def main():
    rng = np.random.RandomState(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    test = parse_test()
    rf = pd.read_csv(OUT / "cohort_1_ampscan_scores.csv")
    rf["id"] = rf["id"].astype(str)
    test["id"] = test["id"].astype(str)
    df = test.merge(rf, on=["id", "y"])
    df["pred"] = (df["p_ampscan_rf"] >= 0.5).astype(int)
    df["bucket"] = np.where(
        df["y"] == 1,
        np.where(df["pred"] == 1, "TP", "FN"),
        np.where(df["pred"] == 1, "FP", "TN"),
    )
    phys_df = pd.DataFrame([phys(s) for s in df["seq"]])
    df = pd.concat([df.reset_index(drop=True), phys_df], axis=1)

    cols = ["len", "charge", "gravy", "muh", "aromatic", "n_cys", "n_kr", "n_de"]
    bucket_rows = []
    for b, g in df.groupby("bucket"):
        rec = {"bucket": b, "n": int(len(g))}
        rec.update(summarize_group(g, cols))
        bucket_rows.append(rec)
    pd.DataFrame(bucket_rows).to_csv(OUT / "cohort1_error_buckets.csv", index=False)
    fn = df[df["bucket"] == "FN"].sort_values("p_ampscan_rf")
    fp = df[df["bucket"] == "FP"].sort_values("p_ampscan_rf", ascending=False)
    keep = ["id", "y", "p_ampscan_rf", "len", "charge", "gravy", "muh", "aromatic", "n_cys", "seq"]
    fn[keep].head(25).to_csv(OUT / "cohort1_fn_lowest_p.csv", index=False)
    fp[keep].head(25).to_csv(OUT / "cohort1_fp_highest_p.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4))
    for ax, col, title in zip(axes, ["len", "charge", "gravy"], ["length", "net charge pH 7", "GRAVY"]):
        data = [df.loc[df.bucket == b, col].values for b in ["TN", "FP", "FN", "TP"]]
        ax.boxplot(data, showfliers=False)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xticklabels(["TN", "FP", "FN", "TP"])
        ax.set_title(title)
        ax.set_ylabel(col)
    fig.tight_layout()
    fig.savefig(OUT / "cohort1_error_boxplots.png", dpi=160)
    plt.close(fig)

    # operating points
    op_rows = []
    op_rows += operating_rows("AMPscan RF (Platt)", df["y"], df["p_ampscan_rf"])
    op_rows += operating_rows("AMPscan 1D-CNN (T)", df["y"], df["p_ampscan_cnn"])
    for name, csv, col in [
        ("Macrel", "cohort_1_macrel_scores.csv", "p_macrel"),
        ("AMPlify balanced", "cohort_1_amplify_scores.csv", "p_amplify"),
        ("AI4AMP PC6", "cohort_1_ai4amp_scores.csv", "p_ai4amp"),
        ("AmpGram", "cohort_1_ampgram_scores.csv", "p_ampgram"),
    ]:
        t = pd.read_csv(OUT / csv)
        t["id"] = t["id"].astype(str)
        m = df[["id", "y"]].merge(t[["id", col]].dropna(), on="id")
        op_rows += operating_rows(name, m["y"], m[col])
    c2 = pd.read_csv(OUT / "cohort_2b_ampscan_scores.csv")
    op_rows += operating_rows("AMPscan RF · Cohort 2b fragments", c2["y"], c2["p_ampscan_rf"])
    pd.DataFrame(op_rows).to_csv(OUT / "operating_points.csv", index=False)

    # paired bootstrap on common IDs with Macrel / AMPlify
    mac = pd.read_csv(OUT / "cohort_1_macrel_scores.csv")
    mac["id"] = mac["id"].astype(str)
    amp = pd.read_csv(OUT / "cohort_1_amplify_scores.csv")
    amp["id"] = amp["id"].astype(str)
    jmac = df.merge(mac[["id", "p_macrel"]].dropna(), on="id")
    jamp = df.merge(amp[["id", "p_amplify"]].dropna(), on="id")
    delong = {
        "method": "paired bootstrap of ROC-AUC difference, 2000 resamples, seed 42",
        "rf_vs_macrel": bootstrap_auc_diff(jmac["y"], jmac["p_ampscan_rf"], jmac["p_macrel"], rng),
        "rf_vs_amplify": bootstrap_auc_diff(jamp["y"], jamp["p_ampscan_rf"], jamp["p_amplify"], rng),
        "note": "ci_excludes_0 True => difference is distinguishable at ~95%. False => treat as a tie on ranking.",
    }
    (OUT / "delong_bootstrap_auc.json").write_text(json.dumps(delong, indent=2))

    # markdown
    def bucket_line(name):
        r = next(x for x in bucket_rows if x["bucket"] == name)
        return (
            f"| {name} | {r['n']} | {r['len_median']:.0f} | {r['charge_median']:.2f} | "
            f"{r['gravy_median']:.2f} | {r['muh_median']:.2f} | {r['n_cys_mean']:.2f} |"
        )

    mac_d = delong["rf_vs_macrel"]
    amp_d = delong["rf_vs_amplify"]
    md = [
        "# Cohort 1 defense ammo — errors, thresholds, ranking vs Macrel",
        "",
        "Frozen scores. Locked RF ROC-AUC remains **0.9515**. Do not quote 0.993.",
        "",
        "## Who we miss at P ≥ 0.5 (RF Platt)",
        "",
        "| bucket | n | median len | median charge | median GRAVY | median μH | mean Cys |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        bucket_line("TN"),
        bucket_line("FP"),
        bucket_line("FN"),
        bucket_line("TP"),
        "",
        "Boxplots: `cohort1_error_boxplots.png`. Lowest-P FNs: `cohort1_fn_lowest_p.csv`. Highest-P FPs: `cohort1_fp_highest_p.csv`.",
        "",
        "If FNs are less cationic / less hydrophobic than TPs, v2 physchem extras might help. If FNs look like TPs, it is homology/label noise — do not add features.",
        "",
        "## Operating points (precision/recall)",
        "",
        "Cohort 1 is ~50/50. Real screens are AMP-rare. Raise the threshold for precision.",
        "",
        "| model | P≥ | n_called AMP | precision | recall | specificity |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in op_rows:
        if r["model"].startswith("AMPscan RF") or r["model"] in (
            "Macrel",
            "AMPlify balanced",
        ):
            md.append(
                f"| {r['model']} | {r['threshold']:.2f} | {r['n_called_amp']} | "
                f"{r['precision']:.3f} | {r['recall']:.3f} | {r['specificity']:.3f} |"
            )
    md += [
        "",
        "Full table: `operating_points.csv`.",
        "",
        "## Ranking vs Macrel / AMPlify (paired bootstrap, common IDs)",
        "",
        f"- RF vs Macrel: ΔAUC = **{mac_d['diff']:.4f}**, 95% boot CI [{mac_d['ci95_lo']:.4f}, {mac_d['ci95_hi']:.4f}], "
        f"CI excludes 0: **{mac_d['ci_excludes_0']}** (n={mac_d['n']}).",
        f"- RF vs AMPlify: ΔAUC = **{amp_d['diff']:.4f}**, 95% boot CI [{amp_d['ci95_lo']:.4f}, {amp_d['ci95_hi']:.4f}], "
        f"CI excludes 0: **{amp_d['ci_excludes_0']}** (n={amp_d['n']}).",
        "",
        "If RF vs Macrel CI includes 0: say **tied on ranking, we win calibration (ECE 0.023 vs 0.204)**.",
        "JSON: `delong_bootstrap_auc.json`.",
    ]
    (OUT / "defense_ammo.md").write_text("\n".join(md) + "\n")
    print("wrote", OUT / "defense_ammo.md")
    print("RF vs Macrel", json.dumps(mac_d, indent=2))


if __name__ == "__main__":
    main()
