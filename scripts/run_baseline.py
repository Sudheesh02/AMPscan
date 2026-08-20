#!/usr/bin/env python3
"""Classical AMP vs non-AMP baselines (Phase 2).

Extract AAC + DPC + physicochemical features, train L2 logistic regression
and a 200-tree random forest on the homology split and (separately) the
random-split control. Does not modify existing locked data files; only
writes new files under data/processed/features/, models/baseline/, and
reports/baseline/.
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler

SEED = 42
AA20 = "ACDEFGHIKLMNPQRSTVWY"
AA_INDEX = {a: i for i, a in enumerate(AA20)}
DIPEPTIDES = [a + b for a in AA20 for b in AA20]

# Kyte–Doolittle hydropathy (GRAVY)
KD = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# Eisenberg consensus hydrophobicity (hydrophobic moment)
EISENBERG = {
    "A": 0.62, "R": -2.53, "N": -0.78, "D": -0.90, "C": 0.29,
    "Q": -0.85, "E": -0.74, "G": 0.48, "H": -0.40, "I": 1.38,
    "L": 1.06, "K": -1.50, "M": 0.64, "F": 1.19, "P": 0.12,
    "S": -0.18, "T": -0.05, "W": 0.81, "Y": 0.26, "V": 1.08,
}

# Side-chain pKa (IPC / typical peptide values) + termini
PKA_POS = {"K": 10.54, "R": 12.48, "H": 6.04}  # charge -> +1 when protonated
PKA_NEG = {"D": 3.90, "E": 4.07, "C": 8.18, "Y": 10.46}  # charge -> -1 when deprotonated
PKA_NTERM = 9.69
PKA_CTERM = 2.34
PH = 7.0
HELIX_DELTA = math.radians(100.0)  # alpha-helix hydrophobic moment

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "splits"
FEAT_DIR = ROOT / "data" / "processed" / "features"
MODEL_DIR = ROOT / "models" / "baseline"
REPORT_DIR = ROOT / "reports" / "baseline"

PHYSCHEM_NAMES = [
    "length",
    "net_charge_pH7",
    "GRAVY",
    "hydrophobic_moment",
    "aromatic_fraction",
]
FEATURE_NAMES = (
    [f"AAC_{a}" for a in AA20]
    + [f"DPC_{ab}" for ab in DIPEPTIDES]
    + PHYSCHEM_NAMES
)


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)


def parse_fasta(path: Path):
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
    return ids, np.asarray(labels, dtype=np.int8), seqs


def net_charge_pH7(seq: str) -> float:
    """Henderson–Hasselbalch net charge at pH 7, including N/C termini."""
    charge = 1.0 / (1.0 + 10.0 ** (PH - PKA_NTERM))  # N-term
    charge += -1.0 / (1.0 + 10.0 ** (PKA_CTERM - PH))  # C-term
    for aa in seq:
        if aa in PKA_POS:
            charge += 1.0 / (1.0 + 10.0 ** (PH - PKA_POS[aa]))
        elif aa in PKA_NEG:
            charge += -1.0 / (1.0 + 10.0 ** (PKA_NEG[aa] - PH))
    return charge


def gravy(seq: str) -> float:
    vals = [KD[a] for a in seq if a in KD]
    return float(sum(vals) / len(vals)) if vals else 0.0


def hydrophobic_moment(seq: str) -> float:
    """Eisenberg hydrophobic moment, 100°/residue (alpha helix), mean-normalized."""
    hs = [EISENBERG[a] for a in seq if a in EISENBERG]
    n = len(hs)
    if n == 0:
        return 0.0
    sc = ss = 0.0
    for i, h in enumerate(hs):
        ang = i * HELIX_DELTA
        sc += h * math.cos(ang)
        ss += h * math.sin(ang)
    return math.sqrt(sc * sc + ss * ss) / n


def aromatic_fraction(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(1 for a in seq if a in "FWY") / len(seq)


def featurize_one(seq: str) -> np.ndarray:
    L = len(seq)
    aac = np.zeros(20, dtype=np.float64)
    dpc = np.zeros(400, dtype=np.float64)
    for a in seq:
        i = AA_INDEX.get(a)
        if i is not None:
            aac[i] += 1.0
    if L:
        aac /= L
    if L >= 2:
        valid = 0
        for i in range(L - 1):
            a = AA_INDEX.get(seq[i])
            b = AA_INDEX.get(seq[i + 1])
            if a is None or b is None:
                continue
            dpc[a * 20 + b] += 1.0
            valid += 1
        if valid:
            dpc /= valid
    phys = np.array(
        [
            float(L),
            net_charge_pH7(seq),
            gravy(seq),
            hydrophobic_moment(seq),
            aromatic_fraction(seq),
        ],
        dtype=np.float64,
    )
    return np.concatenate([aac, dpc, phys])


def featurize_many(seqs):
    X = np.zeros((len(seqs), len(FEATURE_NAMES)), dtype=np.float32)
    for i, s in enumerate(seqs):
        X[i] = featurize_one(s)
    return X


def load_split_fasta(prefix: str, fold: str):
    """prefix='' for homology, 'random_' for random control."""
    path = SPLITS / f"{prefix}{fold}.fasta"
    return parse_fasta(path)


def metrics_block(y_true, y_prob, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "n": int(len(y_true)),
        "n_pos": int(np.sum(y_true == 1)),
        "n_neg": int(np.sum(y_true == 0)),
    }


def plot_confusion(cm, title, path: Path):
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], labels=["non-AMP", "AMP"])
    ax.set_yticks([0, 1], labels=["non-AMP", "AMP"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    vmax = cm.max() if cm.max() else 1
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > vmax / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_roc_pr(curves, path_roc: Path, path_pr: Path, title_prefix: str):
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    for name, fpr, tpr, auc in curves["roc"]:
        ax.plot(fpr, tpr, label=f"{name}  AUC={auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(f"{title_prefix} ROC (test)")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path_roc, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    for name, rec, prec, ap in curves["pr"]:
        ax.plot(rec, prec, label=f"{name}  AP={ap:.3f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"{title_prefix} PR (test)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path_pr, dpi=140)
    plt.close(fig)


def save_npz(path: Path, ids, y, X):
    np.savez_compressed(
        path,
        ids=np.asarray(ids),
        y=y,
        X=X,
        feature_names=np.asarray(FEATURE_NAMES),
    )


def train_eval_one_split(split_name: str, prefix: str, feat: dict):
    """Train on this split's train fold; evaluate val and test."""
    Xtr, ytr = feat["train"]["X"], feat["train"]["y"]
    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(Xtr)

    lr = LogisticRegression(
        C=1.0,  # L2 is the sklearn 1.9 default; do not pass deprecated penalty=
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=SEED,
    )
    rf = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=4,
    )
    lr.fit(Xtr_s, ytr)
    rf.fit(Xtr, ytr)

    joblib.dump(scaler, MODEL_DIR / f"{split_name}_scaler.joblib")
    joblib.dump(lr, MODEL_DIR / f"{split_name}_logreg.joblib")
    joblib.dump(rf, MODEL_DIR / f"{split_name}_rf.joblib")

    results = []
    roc_bundle = {"roc": [], "pr": []}
    for fold in ("val", "test"):
        X = feat[fold]["X"]
        y = feat[fold]["y"]
        Xs = scaler.transform(X)
        for model_name, prob in (
            ("logreg", lr.predict_proba(Xs)[:, 1]),
            ("rf", rf.predict_proba(X)[:, 1]),
        ):
            pred = (prob >= 0.5).astype(np.int8)
            m = metrics_block(y, prob, pred)
            m.update(
                {
                    "split": split_name,
                    "model": model_name,
                    "fold": fold,
                }
            )
            results.append(m)
            cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]], dtype=int)
            plot_confusion(
                cm,
                f"{split_name} {model_name} {fold}",
                REPORT_DIR / f"cm_{split_name}_{model_name}_{fold}.png",
            )
            if fold == "test":
                fpr, tpr, _ = roc_curve(y, prob)
                rec, prec, _ = precision_recall_curve(y, prob)
                roc_bundle["roc"].append((model_name, fpr, tpr, m["roc_auc"]))
                roc_bundle["pr"].append((model_name, rec, prec, m["pr_auc"]))

    plot_roc_pr(
        roc_bundle,
        REPORT_DIR / f"roc_{split_name}_test.png",
        REPORT_DIR / f"pr_{split_name}_test.png",
        split_name.replace("_", " "),
    )
    return results


def versions():
    import sklearn
    import scipy
    import matplotlib as mpl

    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "matplotlib": mpl.__version__,
        "joblib": joblib.__version__,
        "seed": SEED,
    }


def write_summary(rows, ver, n_feat):
    def fmt(x):
        return f"{x:.4f}" if isinstance(x, float) else str(x)

    lines = [
        "# Classical baseline — AMP vs non-AMP",
        "",
        f"Built: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "Phase 2 only: logistic regression (L2) and random forest. No ESM, CNN, or app.",
        "",
        "## Setup",
        "",
        f"- Seed: `{SEED}`",
        f"- Features: {n_feat}-dim = AAC(20) + DPC(400) + physchem(5)",
        "  - AAC: 20 standard amino-acid frequencies (length-normalized; X ignored in counts)",
        "  - DPC: 400 dipeptide frequencies over valid 20×20 pairs",
        "  - Physchem: length; net charge at pH 7 (Henderson–Hasselbalch, N/C termini + D/E/C/Y/H/K/R);",
        "    GRAVY (Kyte–Doolittle mean); Eisenberg hydrophobic moment (100°/residue); aromatic fraction (F+W+Y)/L",
        "- Logistic regression: L2, C=1.0, `class_weight=balanced`, features StandardScaled on train",
        "- Random forest: 200 trees, `class_weight=balanced`, unscaled features, `n_jobs=4`",
        "- Positive class = AMP (label 1). Threshold = 0.5 for accuracy / F1 / confusion matrix.",
        "- Homology split: cluster-aware 70/15/15 from Phase 1. Random split: leakage control.",
        "- Models are trained **separately** on each split's train fold (fair leakage comparison).",
        "",
        "## Package versions",
        "",
    ]
    for k, v in ver.items():
        lines.append(f"- {k}: `{v}`")
    lines += [
        "",
        "## Test-set results",
        "",
        "| split | model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    test_rows = [r for r in rows if r["fold"] == "test"]
    for r in test_rows:
        lines.append(
            f"| {r['split']} | {r['model']} | {fmt(r['accuracy'])} | {fmt(r['macro_f1'])} | "
            f"{fmt(r['roc_auc'])} | {fmt(r['pr_auc'])} | {r['tn']} | {r['fp']} | {r['fn']} | {r['tp']} |"
        )
    lines += [
        "",
        "## Validation-set results",
        "",
        "| split | model | accuracy | macro-F1 | ROC-AUC | PR-AUC |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        if r["fold"] != "val":
            continue
        lines.append(
            f"| {r['split']} | {r['model']} | {fmt(r['accuracy'])} | {fmt(r['macro_f1'])} | "
            f"{fmt(r['roc_auc'])} | {fmt(r['pr_auc'])} |"
        )
    lines += [
        "",
        "## How to read the leakage gap",
        "",
        "The random split assigns homologous peptides to different folds, so test metrics",
        "are typically **higher** than on the homology split. The homology-split numbers",
        "are the honest estimate of generalization to distant sequences. A large gap means",
        "the model is partly memorizing family-level patterns rather than a transferable AMP motif.",
        "",
        "## Files",
        "",
        "- Features: `data/processed/features/*.npz` (new directory; existing data files untouched)",
        "- Models: `models/baseline/{homology,random}_{logreg,rf,scaler}.joblib`",
        "- Metrics: `reports/baseline/metrics.json`, `reports/baseline/metrics.csv`",
        "- Plots: `reports/baseline/cm_*.png`, `roc_*_test.png`, `pr_*_test.png`",
        "",
    ]
    (REPORT_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    set_seed(SEED)
    FEAT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    (FEAT_DIR / "feature_names.json").write_text(
        json.dumps(
            {
                "n_features": len(FEATURE_NAMES),
                "aac": [f"AAC_{a}" for a in AA20],
                "dpc": [f"DPC_{ab}" for ab in DIPEPTIDES],
                "physchem": PHYSCHEM_NAMES,
                "notes": {
                    "net_charge": "Henderson-Hasselbalch at pH 7; N/C termini + D,E,C,Y,H,K,R",
                    "GRAVY": "Kyte-Doolittle mean over standard 20 AA",
                    "hydrophobic_moment": "Eisenberg scale, 100 deg/residue, divided by length",
                    "DPC_norm": "counts / number of valid 20x20 overlapping pairs",
                    "X_residues": "ignored in AAC/DPC/GRAVY/moment counts; still count in length and aromatic denom",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    all_feat = {}
    for split_name, prefix in (("homology", ""), ("random", "random_")):
        print(f"Extracting features: {split_name}")
        all_feat[split_name] = {}
        for fold in ("train", "val", "test"):
            ids, y, seqs = load_split_fasta(prefix, fold)
            X = featurize_many(seqs)
            out = FEAT_DIR / f"{split_name}_{fold}.npz"
            save_npz(out, ids, y, X)
            all_feat[split_name][fold] = {"ids": ids, "y": y, "X": X}
            print(f"  {fold}: n={len(y)} pos={int(y.sum())} neg={int((y == 0).sum())} -> {out}")

    rows = []
    for split_name, prefix in (("homology", ""), ("random", "random_")):
        print(f"Training models: {split_name}")
        rows.extend(train_eval_one_split(split_name, prefix, all_feat[split_name]))

    ver = versions()
    (REPORT_DIR / "versions.json").write_text(json.dumps(ver, indent=2) + "\n")
    (REPORT_DIR / "metrics.json").write_text(json.dumps(rows, indent=2) + "\n")

    csv_path = REPORT_DIR / "metrics.csv"
    keys = [
        "split",
        "model",
        "fold",
        "accuracy",
        "macro_f1",
        "roc_auc",
        "pr_auc",
        "tn",
        "fp",
        "fn",
        "tp",
        "n",
        "n_pos",
        "n_neg",
    ]
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(str(r[k]) if not isinstance(r[k], float) else f"{r[k]:.6f}" for k in keys) + "\n")

    write_summary(rows, ver, len(FEATURE_NAMES))

    # stdout table (test only)
    print()
    print("=" * 88)
    print("TEST RESULTS  homology split vs random-split control")
    print("=" * 88)
    hdr = f"{'split':<12} {'model':<8} {'acc':>8} {'macroF1':>8} {'ROC-AUC':>8} {'PR-AUC':>8}  {'TN':>5} {'FP':>5} {'FN':>5} {'TP':>5}"
    print(hdr)
    print("-" * 88)
    for r in rows:
        if r["fold"] != "test":
            continue
        print(
            f"{r['split']:<12} {r['model']:<8} {r['accuracy']:8.4f} {r['macro_f1']:8.4f} "
            f"{r['roc_auc']:8.4f} {r['pr_auc']:8.4f}  {r['tn']:5d} {r['fp']:5d} {r['fn']:5d} {r['tp']:5d}"
        )
    print("=" * 88)
    print(f"versions: {ver}")
    print(f"wrote {FEAT_DIR}")
    print(f"wrote {MODEL_DIR}")
    print(f"wrote {REPORT_DIR}")


if __name__ == "__main__":
    main()
