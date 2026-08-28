"""Classification metrics for the AMPscan v1 tool benchmark. No retraining."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    roc_auc_score,
    roc_curve,
)


def ece_15(y: np.ndarray, p: np.ndarray) -> float:
    y = y.astype(float)
    p = np.clip(p.astype(float), 0.0, 1.0)
    bins = np.linspace(0.0, 1.0, 16)
    ece = 0.0
    n = len(y)
    for i in range(15):
        lo, hi = bins[i], bins[i + 1]
        if i == 14:
            m = (p >= lo) & (p <= hi)
        else:
            m = (p >= lo) & (p < hi)
        if not np.any(m):
            continue
        ece += (m.sum() / n) * abs(y[m].mean() - p[m].mean())
    return float(ece)


def summarize(y: np.ndarray, p: np.ndarray, thresh: float = 0.5) -> dict:
    p = np.clip(np.asarray(p, dtype=float), 0.0, 1.0)
    y = np.asarray(y, dtype=int)
    pred = (p >= thresh).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    fpr, tpr, thr = roc_curve(y, p)
    # sensitivity at 90% specificity (FPR <= 0.10)
    ok = np.where(fpr <= 0.10)[0]
    sens90 = float(tpr[ok[-1]]) if len(ok) else float("nan")
    return {
        "n": int(len(y)),
        "n_pos": int(y.sum()),
        "n_neg": int((y == 0).sum()),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "mcc": float(matthews_corrcoef(y, pred)),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece_15": ece_15(y, p),
        "sens_at_90spec": sens90,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "roc_fpr": fpr,
        "roc_tpr": tpr,
    }
