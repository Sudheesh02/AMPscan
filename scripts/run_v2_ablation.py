#!/usr/bin/env python3
"""Train & calibrate v2 length-debiased models (424-D RF + CUDA 1D-CNN) and run v1.1 vs v2 ablation."""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from scipy.optimize import minimize_scalar
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))

from features import CNN1D, MAX_LEN, featurize_many  # noqa: E402
from scoring import get_artifacts, sigmoid_np  # noqa: E402

SEED = 42
AA21 = "ACDEFGHIKLMNPQRSTVWYX"
AA21_IDX = {a: i for i, a in enumerate(AA21)}
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_labeled_fasta(path: Path) -> tuple[list[str], np.ndarray]:
    seqs, labels = [], []
    hdr, buf = None, []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    seqs.append("".join(buf).strip().upper().translate(MAP))
                    labels.append(1 if "LABEL=1" in hdr else 0)
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            seqs.append("".join(buf).strip().upper().translate(MAP))
            labels.append(1 if "LABEL=1" in hdr else 0)
    return seqs, np.asarray(labels, dtype=np.int64)


def encode_idx(seqs: list[str]) -> torch.Tensor:
    arr = np.full((len(seqs), MAX_LEN), -1, dtype=np.int64)
    for i, s in enumerate(seqs):
        for j, a in enumerate(s[:MAX_LEN]):
            idx = AA21_IDX.get(a)
            if idx is not None:
                arr[i, j] = idx
    return torch.from_numpy(arr)


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob <= hi if i == n_bins - 1 else y_prob < hi)
        if mask.any():
            ece += (mask.sum() / n) * abs(float(y_true[mask].mean()) - float(y_prob[mask].mean()))
    return float(ece)


def eval_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    y_pred = (y_prob >= 0.5).astype(np.int64)
    return {
        "n": int(len(y_true)),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "f1": round(float(f1_score(y_true, y_pred)), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "ece": round(compute_ece(y_true, y_prob), 4),
    }


def train_cnn_v2(
    idx_tr: torch.Tensor,
    y_tr: np.ndarray,
    idx_va: torch.Tensor,
    y_va: np.ndarray,
    device: str,
    max_epochs: int = 35,
    patience: int = 7,
) -> tuple[CNN1D, float]:
    model = CNN1D(dropout=0.2).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    crit = nn.BCEWithLogitsLoss()
    ds_tr = TensorDataset(idx_tr, torch.from_numpy(y_tr.astype(np.float32)))
    dl_tr = DataLoader(ds_tr, batch_size=128, shuffle=True)

    best_loss = float("inf")
    best_state = None
    wait = 0

    for _epoch in range(max_epochs):
        model.train()
        for xb, yb in dl_tr:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            logits_va = []
            for i in range(0, len(idx_va), 256):
                logits_va.append(model(idx_va[i : i + 256].to(device)).cpu())
            l_va = torch.cat(logits_va)
            val_loss = float(crit(l_va, torch.from_numpy(y_va.astype(np.float32))))
        if val_loss < best_loss - 1e-4:
            best_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    assert best_state is not None
    model.load_state_dict(best_state)
    model.to(device).eval()

    # Temperature scaling on val logits
    with torch.no_grad():
        logits_va = []
        for i in range(0, len(idx_va), 256):
            logits_va.append(model(idx_va[i : i + 256].to(device)).cpu().numpy())
        z_va = np.concatenate(logits_va)

    def nll(T: float) -> float:
        p = np.clip(sigmoid_np(z_va / T), 1e-7, 1.0 - 1e-7)
        return float(-np.mean(y_va * np.log(p) + (1 - y_va) * np.log(1 - p)))

    res = minimize_scalar(nll, bounds=(0.2, 5.0), method="bounded")
    return model, float(res.x)


@torch.no_grad()
def predict_cnn(model: CNN1D, idx: torch.Tensor, temp: float, device: str) -> np.ndarray:
    model.eval()
    logits = []
    for i in range(0, len(idx), 256):
        logits.append(model(idx[i : i + 256].to(device)).cpu().numpy())
    return sigmoid_np(np.concatenate(logits) / temp)


def main() -> None:
    set_seed()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training v2 models on device={device}", flush=True)

    s_v2 = ROOT / "data" / "splits_v2"
    tr_seqs, y_tr = load_labeled_fasta(s_v2 / "train.fasta")
    va_seqs, y_va = load_labeled_fasta(s_v2 / "val.fasta")

    # 1. Train v2 RF (424-D no-length + hydrophobic_moment_v2)
    X_tr = featurize_many(tr_seqs, include_length=False, v2_hmoment=True)
    X_va = featurize_many(va_seqs, include_length=False, v2_hmoment=True)
    rf_v2 = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1)
    rf_v2.fit(X_tr, y_tr)
    rf_v2.n_jobs = 1

    p_va_raw = rf_v2.predict_proba(X_va)[:, 1].reshape(-1, 1)
    platt = LogisticRegression(C=1e6, solver="lbfgs")
    platt.fit(p_va_raw, y_va)
    platt_a = float(platt.coef_[0, 0])
    platt_b = float(platt.intercept_[0])

    # 2. Train v2 1D-CNN
    idx_tr = encode_idx(tr_seqs)
    idx_va = encode_idx(va_seqs)
    cnn_v2, temp_v2 = train_cnn_v2(idx_tr, y_tr, idx_va, y_va, device=device)

    out_models = ROOT / "models" / "v2"
    out_models.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf_v2, out_models / "rf_v2.joblib")
    (out_models / "rf_v2_platt.json").write_text(
        json.dumps({"a": platt_a, "b": platt_b, "n_features": 424}, indent=2),
        encoding="utf-8",
    )
    torch.save({"dropout": 0.2, "state_dict": cnn_v2.state_dict()}, out_models / "cnn1d_v2.pt")
    (out_models / "cnn1d_v2_temp.json").write_text(json.dumps({"T": temp_v2}, indent=2), encoding="utf-8")

    # 3. Evaluate v1.1 vs v2 on 3 test sets
    art_v1 = get_artifacts()
    eval_sets = {
        "v1_homology_test": ROOT / "data" / "splits" / "test.fasta",
        "v2_length_matched_test": ROOT / "data" / "splits_v2" / "test.fasta",
        "cohort_2b_fair_ood": ROOT / "data" / "splits" / "dbaasp_ood" / "cohort2b_fair.fasta",
    }

    results: dict = {}
    for name, path in eval_sets.items():
        seqs, y = load_labeled_fasta(path)
        p_v1_rf = art_v1.rf_calibrated_many(seqs)
        p_v1_cnn = art_v1.cnn_calibrated_many(seqs)

        X_v2 = featurize_many(seqs, include_length=False, v2_hmoment=True)
        p_v2_rf = sigmoid_np(platt_a * rf_v2.predict_proba(X_v2)[:, 1] + platt_b)
        p_v2_cnn = predict_cnn(cnn_v2, encode_idx(seqs), temp_v2, device=device)

        results[name] = {
            "v1.1_rf_425d": eval_metrics(y, p_v1_rf),
            "v2_rf_424d_debiased": eval_metrics(y, p_v2_rf),
            "v1.1_cnn": eval_metrics(y, p_v1_cnn),
            "v2_cnn_debiased": eval_metrics(y, p_v2_cnn),
        }

    rep_dir = ROOT / "reports" / "v2_ablation"
    rep_dir.mkdir(parents=True, exist_ok=True)
    (rep_dir / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# AMPscan v1.1 vs v2 (Length-Debiased) Ablation Report\n",
        "- **v1.1**: Trained on `data/splits/train.fasta` (14,904 seqs; pos median 20 aa vs neg median 61 aa; 425-D with raw `length`).",
        "- **v2**: Trained on `data/splits_v2/train.fasta` (7,720 seqs; 5-aa bin length-matched, pos/neg median 32 aa; 424-D without raw `length` + fixed `hydrophobic_moment_v2`).\n",
        "| Benchmark | Model | N | ROC-AUC | PR-AUC | F1 | Accuracy | ECE |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bname, models in results.items():
        for mname, m in models.items():
            lines.append(
                f"| `{bname}` | `{mname}` | {m['n']} | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} | {m['f1']:.4f} | {m['accuracy']:.4f} | {m['ece']:.4f} |"
            )
    (rep_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
