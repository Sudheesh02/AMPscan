#!/usr/bin/env python3
"""Phase 5: calibrate locked models. No retraining, no architecture changes.

- ESM-2 linear and 1D-CNN: temperature scaling (one scalar T) on homology val
- Phase 2 RF: Platt scaling (logistic on RF probabilities) on homology val
Random-split ECE uses the same recipe on that split's own val (fair control).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

SEED = 42
N_BINS = 15

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from run_cnn1d import CNN1D  # locked architecture, weights loaded read-only

FEAT = ROOT / "data" / "processed" / "features"
EMB = ROOT / "data" / "processed" / "embeddings" / "esm2_35M"
CNN_T = ROOT / "data" / "processed" / "cnn1d"
SCORE_DIR = ROOT / "data" / "processed" / "calibration"
CAL_DIR = ROOT / "models" / "calibration"
REPORT = ROOT / "reports" / "calibration"


def sigmoid(z):
    z = np.clip(z, -60, 60)
    return 1.0 / (1.0 + np.exp(-z))


def nll_logits(logits, y, T):
    p = np.clip(sigmoid(logits / T), 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_temperature(logits, y):
    y = y.astype(np.float64)
    logits = logits.astype(np.float64)

    def obj(t):
        return nll_logits(logits, y, t)

    res = minimize_scalar(obj, bounds=(0.05, 10.0), method="bounded", options={"xatol": 1e-5})
    return float(res.x), float(res.fun)


def ece_bins(y, p, n_bins=N_BINS):
    y = y.astype(np.float64)
    p = np.clip(p.astype(np.float64), 0, 1)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    rows = []
    n = len(y)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            m = (p >= lo) & (p <= hi)
        else:
            m = (p >= lo) & (p < hi)
        cnt = int(m.sum())
        if cnt == 0:
            rows.append(
                {"bin": i, "lo": float(lo), "hi": float(hi), "n": 0, "conf": None, "acc": None}
            )
            continue
        conf = float(p[m].mean())
        acc = float(y[m].mean())
        ece += (cnt / n) * abs(acc - conf)
        rows.append(
            {
                "bin": i,
                "lo": float(lo),
                "hi": float(hi),
                "n": cnt,
                "conf": conf,
                "acc": acc,
            }
        )
    return float(ece), rows


def reliability_plot(y, p_unc, p_cal, title, path):
    def points(y, p):
        edges = np.linspace(0.0, 1.0, N_BINS + 1)
        xs, ys, ss = [], [], []
        for i in range(N_BINS):
            lo, hi = edges[i], edges[i + 1]
            m = (p >= lo) & (p <= hi if i == N_BINS - 1 else p < hi)
            if m.sum() == 0:
                continue
            xs.append(float(p[m].mean()))
            ys.append(float(y[m].mean()))
            ss.append(20 + 80 * (m.mean()))
        return xs, ys, ss

    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=1, label="perfect")
    xu, yu, su = points(y, p_unc)
    xc, yc, sc = points(y, p_cal)
    ax.scatter(xu, yu, s=su, c="#d95f02", label="uncalibrated", zorder=3)
    ax.scatter(xc, yc, s=sc, c="#1b9e77", label="calibrated", zorder=4)
    ax.set_xlabel("Mean predicted probability (AMP)")
    ax.set_ylabel("Empirical AMP frequency")
    ax.set_title(title)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def load_npz(path):
    z = np.load(path, allow_pickle=True)
    return {k: z[k] for k in z.files}


def rf_proba(split, fold):
    pack = load_npz(FEAT / f"{split}_{fold}.npz")
    rf = joblib.load(ROOT / "models" / "baseline" / f"{split}_rf.joblib")
    p = rf.predict_proba(pack["X"])[:, 1]
    return pack["y"].astype(np.int8), p.astype(np.float64)


def esm_logits(split, fold):
    pack = load_npz(EMB / f"{split}_{fold}.npz")
    scaler = joblib.load(ROOT / "models" / "esm2_35M" / f"{split}_scaler.joblib")
    clf = joblib.load(ROOT / "models" / "esm2_35M" / f"{split}_logreg.joblib")
    Xs = scaler.transform(pack["X"])
    logits = clf.decision_function(Xs)
    return pack["y"].astype(np.int8), logits.astype(np.float64)


@torch.no_grad()
def cnn_logits(split, fold):
    pack = load_npz(CNN_T / f"{split}_{fold}.npz")
    ckpt = torch.load(
        ROOT / "models" / "cnn1d" / f"{split}_cnn1d.pt",
        map_location="cpu",
        weights_only=False,
    )
    model = CNN1D(dropout=float(ckpt.get("dropout", 0.2)))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    idx = torch.from_numpy(pack["idx"].astype(np.int64))
    outs = []
    for i in range(0, len(idx), 256):
        outs.append(model(idx[i : i + 256]).numpy())
    return pack["y"].astype(np.int8), np.concatenate(outs).astype(np.float64)


def pack_metrics(y, p_unc, p_cal):
    ece_u, bins_u = ece_bins(y, p_unc)
    ece_c, bins_c = ece_bins(y, p_cal)
    return {
        "n": int(len(y)),
        "ece_uncal": ece_u,
        "ece_cal": ece_c,
        "brier_uncal": float(brier_score_loss(y, p_unc)),
        "brier_cal": float(brier_score_loss(y, p_cal)),
        "roc_auc_uncal": float(roc_auc_score(y, p_unc)),
        "roc_auc_cal": float(roc_auc_score(y, p_cal)),
        "bins_uncal": bins_u,
        "bins_cal": bins_c,
        "n_bins": N_BINS,
    }


def calibrate_split(split: str):
    # RF: Platt on probabilities
    y_va, p_va = rf_proba(split, "val")
    y_te, p_te = rf_proba(split, "test")
    platt = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000, random_state=SEED)
    platt.fit(p_va.reshape(-1, 1), y_va)
    a = float(platt.coef_[0, 0])
    b = float(platt.intercept_[0])
    p_va_cal = platt.predict_proba(p_va.reshape(-1, 1))[:, 1]
    p_te_cal = platt.predict_proba(p_te.reshape(-1, 1))[:, 1]
    rf = {
        "model": "rf",
        "method": "platt_on_probability",
        "a": a,
        "b": b,
        "val": pack_metrics(y_va, p_va, p_va_cal),
        "test": pack_metrics(y_te, p_te, p_te_cal),
    }
    joblib.dump(platt, CAL_DIR / f"{split}_rf_platt.joblib")
    (CAL_DIR / f"{split}_rf_platt.json").write_text(
        json.dumps(
            {
                "method": "platt_on_probability",
                "p_cal": "sigmoid(a * p_rf + b)",
                "a": a,
                "b": b,
                "fit_on": f"{split} val",
                "not_temperature_scaling": True,
            },
            indent=2,
        )
        + "\n"
    )

    # ESM temperature
    y_va, z_va = esm_logits(split, "val")
    y_te, z_te = esm_logits(split, "test")
    T_esm, nll = fit_temperature(z_va, y_va)
    esm = {
        "model": "esm2_35M_linear",
        "method": "temperature_scaling",
        "T": T_esm,
        "val_nll_at_T": nll,
        "val": pack_metrics(y_va, sigmoid(z_va), sigmoid(z_va / T_esm)),
        "test": pack_metrics(y_te, sigmoid(z_te), sigmoid(z_te / T_esm)),
    }
    (CAL_DIR / f"{split}_esm_temperature.json").write_text(
        json.dumps(
            {
                "method": "temperature_scaling",
                "T": T_esm,
                "p_cal": "sigmoid(logit / T)",
                "fit_on": f"{split} val",
                "val_nll": nll,
            },
            indent=2,
        )
        + "\n"
    )
    np.savez_compressed(
        SCORE_DIR / f"{split}_esm_scores.npz",
        y_val=y_va,
        logit_val=z_va,
        y_test=y_te,
        logit_test=z_te,
        T=np.array([T_esm]),
    )

    # CNN temperature
    y_va, z_va = cnn_logits(split, "val")
    y_te, z_te = cnn_logits(split, "test")
    T_cnn, nll_c = fit_temperature(z_va, y_va)
    cnn = {
        "model": "cnn1d",
        "method": "temperature_scaling",
        "T": T_cnn,
        "val_nll_at_T": nll_c,
        "val": pack_metrics(y_va, sigmoid(z_va), sigmoid(z_va / T_cnn)),
        "test": pack_metrics(y_te, sigmoid(z_te), sigmoid(z_te / T_cnn)),
    }
    (CAL_DIR / f"{split}_cnn_temperature.json").write_text(
        json.dumps(
            {
                "method": "temperature_scaling",
                "T": T_cnn,
                "p_cal": "sigmoid(logit / T)",
                "fit_on": f"{split} val",
                "val_nll": nll_c,
            },
            indent=2,
        )
        + "\n"
    )
    np.savez_compressed(
        SCORE_DIR / f"{split}_cnn_scores.npz",
        y_val=y_va,
        logit_val=z_va,
        y_test=y_te,
        logit_test=z_te,
        T=np.array([T_cnn]),
    )
    np.savez_compressed(
        SCORE_DIR / f"{split}_rf_scores.npz",
        y_val=rf["val"] and y_va,  # placeholder overwritten below
    )

    # save RF scores properly
    y_va_rf, p_va_rf = rf_proba(split, "val")
    y_te_rf, p_te_rf = rf_proba(split, "test")
    np.savez_compressed(
        SCORE_DIR / f"{split}_rf_scores.npz",
        y_val=y_va_rf,
        p_val=p_va_rf,
        y_test=y_te_rf,
        p_test=p_te_rf,
        a=np.array([a]),
        b=np.array([b]),
    )

    # reliability on TEST
    reliability_plot(
        y_te_rf,
        p_te_rf,
        p_te_cal,
        f"{split} RF (Platt) test",
        REPORT / f"reliability_{split}_rf_test.png",
    )
    reliability_plot(
        y_te,
        sigmoid(load_npz(SCORE_DIR / f"{split}_esm_scores.npz")["logit_test"]),
        sigmoid(load_npz(SCORE_DIR / f"{split}_esm_scores.npz")["logit_test"] / T_esm),
        f"{split} ESM-2 linear (T={T_esm:.3f}) test",
        REPORT / f"reliability_{split}_esm_test.png",
    )
    z_te_cnn = load_npz(SCORE_DIR / f"{split}_cnn_scores.npz")["logit_test"]
    y_te_cnn = load_npz(SCORE_DIR / f"{split}_cnn_scores.npz")["y_test"]
    reliability_plot(
        y_te_cnn,
        sigmoid(z_te_cnn),
        sigmoid(z_te_cnn / T_cnn),
        f"{split} 1D-CNN (T={T_cnn:.3f}) test",
        REPORT / f"reliability_{split}_cnn_test.png",
    )

    return {"rf": rf, "esm2_35M_linear": esm, "cnn1d": cnn}


def write_docs(all_res):
    h = all_res["homology"]
    r = all_res["random"]

    def line(name, block):
        t = block["test"]
        return (
            f"| {name} | {t['ece_uncal']:.4f} | {t['ece_cal']:.4f} | "
            f"{t['brier_uncal']:.4f} | {t['brier_cal']:.4f} | "
            f"{t['roc_auc_uncal']:.4f} | {t['roc_auc_cal']:.4f} |"
        )

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = f"""# Phase 5 — calibrated confidence

Built: {built}

Locked Phase 2–4 weights were **not** modified. This phase only fits a scalar
temperature T (ESM-2 linear, 1D-CNN) or a 2-parameter Platt map (RF) on
**validation**, then evaluates on **test**.

## Methods

- **Temperature scaling** (ESM-2, CNN): `p = sigmoid(logit / T)`, T > 0 fit by
  NLL on val. Monotone in the logit, so ROC-AUC is unchanged.
- **Platt scaling** (RF only): `p = sigmoid(a * p_rf + b)` fit by logistic
  regression on val RF probabilities. This is **not** temperature scaling.
- ECE: equal-width, **{N_BINS} bins** on [0, 1], weighted by bin count.
- Brier: mean squared error of predicted AMP probability.

## Homology test

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | uncal ROC-AUC | cal ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{line("Phase 2 RF (Platt)", h["rf"])}
{line("Phase 3 ESM-2 35M linear (T)", h["esm2_35M_linear"])}
{line("Phase 4 1D-CNN (T)", h["cnn1d"])}

Fitted on homology val: RF a={h["rf"]["a"]:.4f}, b={h["rf"]["b"]:.4f};
ESM T={h["esm2_35M_linear"]["T"]:.4f}; CNN T={h["cnn1d"]["T"]:.4f}.

## Random-split test (optional control)

Same recipe, fit on that split's own val using the locked random-split models.

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | uncal ROC-AUC | cal ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{line("RF (Platt)", r["rf"])}
{line("ESM-2 35M linear (T)", r["esm2_35M_linear"])}
{line("1D-CNN (T)", r["cnn1d"])}

## Files

- Parameters: `models/calibration/`
- Scores: `data/processed/calibration/` (new folder)
- Plots/tables: `reports/calibration/`
"""
    (REPORT / "SUMMARY.md").write_text(summary, encoding="utf-8")

    report = f"""# Phase 5 report — calibrated confidence

**Status:** complete  
**Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%d")}  
**Scope:** temperature scaling (ESM-2, CNN) and Platt scaling (RF). No IG, Streamlit, or new models.

Locked directories `models/baseline/`, `models/esm2_35M/`, `models/cnn1d/` weights
and earlier phase reports were read, not rewritten.

## Setup

| Item | Value |
| --- | --- |
| Fit set | homology **val** (primary) |
| Eval set | homology **test** |
| ECE bins | {N_BINS}, equal-width |
| ESM / CNN | one scalar T, NLL on val logits |
| RF | Platt logistic on `p_rf` (not temperature) |
| Seed | {SEED} |

## Homology test

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | ROC-AUC uncal | ROC-AUC cal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{line("Phase 2 RF (Platt)", h["rf"])}
{line("Phase 3 ESM-2 35M linear (T)", h["esm2_35M_linear"])}
{line("Phase 4 1D-CNN (T)", h["cnn1d"])}

ROC-AUC is essentially unchanged after calibration (temperature is a monotone
rescaling of logits; Platt `a` was {h["rf"]["a"]:.3f}, so rank order is preserved).

## Random-split control

| model | uncal ECE | cal ECE | Brier uncal | Brier cal | ROC-AUC cal |
| --- | ---: | ---: | ---: | ---: | ---: |
| RF | {r["rf"]["test"]["ece_uncal"]:.4f} | {r["rf"]["test"]["ece_cal"]:.4f} | {r["rf"]["test"]["brier_uncal"]:.4f} | {r["rf"]["test"]["brier_cal"]:.4f} | {r["rf"]["test"]["roc_auc_cal"]:.4f} |
| ESM-2 linear | {r["esm2_35M_linear"]["test"]["ece_uncal"]:.4f} | {r["esm2_35M_linear"]["test"]["ece_cal"]:.4f} | {r["esm2_35M_linear"]["test"]["brier_uncal"]:.4f} | {r["esm2_35M_linear"]["test"]["brier_cal"]:.4f} | {r["esm2_35M_linear"]["test"]["roc_auc_cal"]:.4f} |
| 1D-CNN | {r["cnn1d"]["test"]["ece_uncal"]:.4f} | {r["cnn1d"]["test"]["ece_cal"]:.4f} | {r["cnn1d"]["test"]["brier_uncal"]:.4f} | {r["cnn1d"]["test"]["brier_cal"]:.4f} | {r["cnn1d"]["test"]["roc_auc_cal"]:.4f} |

## Parameters (homology)

- RF Platt: a={h["rf"]["a"]:.6f}, b={h["rf"]["b"]:.6f}
- ESM T={h["esm2_35M_linear"]["T"]:.6f}
- CNN T={h["cnn1d"]["T"]:.6f}

T > 1 softens over-confident logits; T < 1 sharpens under-confident ones.

## Files

- `models/calibration/`
- `reports/calibration/SUMMARY.md`
- `reports/phase_5_report.md`
- `data/processed/calibration/*.npz`

## What this does not claim

Calibration adjusts **confidence**, not biology. It does not change the homology-split
ranking story from Phases 2–4.
"""
    (ROOT / "reports" / "phase_5_report.md").write_text(report, encoding="utf-8")


def main():
    np.random.seed(SEED)
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    SCORE_DIR.mkdir(parents=True, exist_ok=True)

    all_res = {}
    for split in ("homology", "random"):
        print(f"calibrating {split}", flush=True)
        all_res[split] = calibrate_split(split)

    slim = json.loads(json.dumps(all_res))
    (REPORT / "metrics.json").write_text(json.dumps(slim, indent=2) + "\n")

    keys = [
        "split",
        "model",
        "method",
        "ece_uncal",
        "ece_cal",
        "brier_uncal",
        "brier_cal",
        "roc_auc_uncal",
        "roc_auc_cal",
    ]
    with (REPORT / "metrics.csv").open("w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for split, block in all_res.items():
            for name, rec in block.items():
                t = rec["test"]
                f.write(
                    f"{split},{name},{rec['method']},"
                    f"{t['ece_uncal']:.6f},{t['ece_cal']:.6f},"
                    f"{t['brier_uncal']:.6f},{t['brier_cal']:.6f},"
                    f"{t['roc_auc_uncal']:.6f},{t['roc_auc_cal']:.6f}\n"
                )

    write_docs(all_res)

    print()
    print("=" * 96)
    print("HOMOLOGY TEST  uncal ECE | cal ECE | Brier uncal/cal | ROC-AUC uncal/cal")
    print("=" * 96)
    print(f"{'model':<28} {'ECE_u':>8} {'ECE_c':>8} {'Br_u':>8} {'Br_c':>8} {'AUC_u':>8} {'AUC_c':>8}")
    print("-" * 96)
    labels = [
        ("Phase2 RF (Platt)", all_res["homology"]["rf"]),
        ("Phase3 ESM-2 linear (T)", all_res["homology"]["esm2_35M_linear"]),
        ("Phase4 1D-CNN (T)", all_res["homology"]["cnn1d"]),
    ]
    for lab, rec in labels:
        t = rec["test"]
        print(
            f"{lab:<28} {t['ece_uncal']:8.4f} {t['ece_cal']:8.4f} "
            f"{t['brier_uncal']:8.4f} {t['brier_cal']:8.4f} "
            f"{t['roc_auc_uncal']:8.4f} {t['roc_auc_cal']:8.4f}"
        )
    print("=" * 96)
    print(f"homology T_esm={all_res['homology']['esm2_35M_linear']['T']:.4f}  "
          f"T_cnn={all_res['homology']['cnn1d']['T']:.4f}  "
          f"RF a,b=({all_res['homology']['rf']['a']:.4f},{all_res['homology']['rf']['b']:.4f})")
    print(f"wrote {CAL_DIR}")
    print(f"wrote {REPORT}")
    print(f"wrote {ROOT / 'reports' / 'phase_5_report.md'}")


if __name__ == "__main__":
    main()
