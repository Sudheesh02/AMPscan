#!/usr/bin/env python3
"""Phase 4: 1D-CNN on one-hot peptides (homology train; random-split control).

Does not touch locked Phase 1–3 artifacts. Input is raw sequences, not ESM
embeddings. Light val tuning on homology only; same hyperparameters then
used to train a separate random-split model for the leakage table.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from torch.utils.data import DataLoader, Dataset

SEED = 42
MAX_LEN = 100
AA21 = "ACDEFGHIKLMNPQRSTVWYX"  # X is 21st channel
AA_INDEX = {a: i for i, a in enumerate(AA21)}
N_CHANNELS = len(AA21)

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "splits"
TENSOR_DIR = ROOT / "data" / "processed" / "cnn1d"
MODEL_DIR = ROOT / "models" / "cnn1d"
REPORT_DIR = ROOT / "reports" / "cnn1d"
BASELINE_METRICS = ROOT / "reports" / "baseline" / "metrics.json"
ESM_METRICS = ROOT / "reports" / "esm2_35M" / "metrics.json"


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


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


def encode_seqs(seqs):
    """Integer codes length-padded with -1 (pad). Shape (N, MAX_LEN)."""
    idx = np.full((len(seqs), MAX_LEN), -1, dtype=np.int16)
    for i, s in enumerate(seqs):
        for j, a in enumerate(s[:MAX_LEN]):
            idx[i, j] = AA_INDEX.get(a, 20 if a == "X" else -1)
            if a == "X":
                idx[i, j] = 20
    return idx


def one_hot(idx_batch: torch.Tensor) -> torch.Tensor:
    """idx_batch: (B, L) int, -1 = pad. Returns (B, 21, L) float32."""
    b, l = idx_batch.shape
    x = torch.zeros(b, N_CHANNELS, l, device=idx_batch.device, dtype=torch.float32)
    valid = idx_batch >= 0
    if valid.any():
        bi, li = torch.where(valid)
        x[bi, idx_batch[valid].long(), li] = 1.0
    return x


class PepDS(Dataset):
    def __init__(self, idx, y):
        self.idx = torch.from_numpy(idx.astype(np.int64))
        self.y = torch.from_numpy(y.astype(np.float32))

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        return self.idx[i], self.y[i]


class CNN1D(nn.Module):
    """3× Conv1d + global max pool + small dense head."""

    def __init__(self, dropout: float = 0.3):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(N_CHANNELS, 64, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(64, 128, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self, idx):
        x = one_hot(idx)
        h = self.conv(x)
        h = h.amax(dim=-1)
        return self.head(h).squeeze(-1)


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


@torch.no_grad()
def predict_proba(model, idx, device, batch=256):
    model.eval()
    out = []
    x = torch.from_numpy(idx.astype(np.int64))
    for i in range(0, len(x), batch):
        xb = x[i : i + batch].to(device)
        logits = model(xb)
        out.append(torch.sigmoid(logits).float().cpu().numpy())
    return np.concatenate(out, axis=0)


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


def plot_roc_pr(name, y, prob, tag: str):
    fpr, tpr, _ = roc_curve(y, prob)
    rec, prec, _ = precision_recall_curve(y, prob)
    auc = roc_auc_score(y, prob)
    ap = average_precision_score(y, prob)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.plot(fpr, tpr, label=f"{name}  AUC={auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(f"{tag} ROC (test)")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / f"roc_{tag}_test.png", dpi=140)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.plot(rec, prec, label=f"{name}  AP={ap:.3f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"{tag} PR (test)")
    ax.legend(loc="lower left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / f"pr_{tag}_test.png", dpi=140)
    plt.close(fig)


def train_one(idx_tr, y_tr, idx_va, y_va, dropout, device, max_epochs=40, patience=8, lr=1e-3):
    set_seed(SEED)
    pos = float((y_tr == 1).sum())
    neg = float((y_tr == 0).sum())
    pos_weight = torch.tensor([neg / max(pos, 1.0)], dtype=torch.float32, device=device)
    model = CNN1D(dropout=dropout).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    loader = DataLoader(
        PepDS(idx_tr, y_tr),
        batch_size=128,
        shuffle=True,
        drop_last=False,
        generator=torch.Generator().manual_seed(SEED),
    )
    best_auc, best_state, wait = -1.0, None, 0
    history = []
    for epoch in range(1, max_epochs + 1):
        model.train()
        tot = 0.0
        n = 0
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            tot += float(loss.item()) * len(yb)
            n += len(yb)
        val_prob = predict_proba(model, idx_va, device)
        auc = float(roc_auc_score(y_va, val_prob))
        history.append({"epoch": epoch, "train_loss": tot / max(n, 1), "val_roc_auc": auc})
        if auc > best_auc + 1e-4:
            best_auc = auc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break
    model.load_state_dict(best_state)
    return model, best_auc, history


def eval_split(model, feat, split_name, device):
    rows = []
    test_prob = test_y = None
    for fold in ("val", "test"):
        prob = predict_proba(model, feat[fold]["idx"], device)
        y = feat[fold]["y"]
        pred = (prob >= 0.5).astype(np.int8)
        m = metrics_block(y, prob, pred)
        m.update({"split": split_name, "model": "cnn1d", "fold": fold})
        rows.append(m)
        cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]], dtype=int)
        plot_confusion(
            cm,
            f"{split_name} cnn1d {fold}",
            REPORT_DIR / f"cm_{split_name}_cnn1d_{fold}.png",
        )
        if fold == "test":
            test_prob, test_y = prob, y
    plot_roc_pr("cnn1d", test_y, test_prob, f"{split_name}_cnn1d")
    return rows


def load_split(prefix: str):
    out = {}
    for fold in ("train", "val", "test"):
        ids, y, seqs = parse_fasta(SPLITS / f"{prefix}{fold}.fasta")
        idx = encode_seqs(seqs)
        out[fold] = {"ids": ids, "y": y, "idx": idx, "seqs": seqs}
    return out


def pick(rows, split, model, fold):
    for r in rows:
        if r["split"] == split and r["model"] == model and r["fold"] == fold:
            return r
    return None


def write_reports(rows, best_drop, ver, hist_h, overlap):
    rf = json.loads(BASELINE_METRICS.read_text(encoding="utf-8"))
    esm = json.loads(ESM_METRICS.read_text(encoding="utf-8"))
    rf_h = pick(rf, "homology", "rf", "test")
    esm_h = pick(esm, "homology", "linear", "test")
    cnn_h = pick(rows, "homology", "cnn1d", "test")
    rf_r = pick(rf, "random", "rf", "test")
    esm_r = pick(esm, "random", "linear", "test")
    cnn_r = pick(rows, "random", "cnn1d", "test")

    def fmt(x):
        return f"{x:.4f}" if isinstance(x, float) else str(x)

    summary = [
        "# Phase 4 — 1D-CNN on one-hot peptides",
        "",
        f"Built: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "Homology train only for the primary model. A second CNN with the same",
        "hyperparameters is trained on the random-split train fold for the leakage table",
        "(same protocol as Phases 2–3). ESM embeddings are **not** used as input.",
        "",
        "## Architecture",
        "",
        "- Input: 21-channel one-hot (20 standard AA + **X**), length padded to 100 with zeros",
        "- Conv1d 21→64 (k=5) → 64→128 (k=5) → 128→128 (k=3), ReLU, dropout",
        "- Global max pool → Linear 128→64→1",
        f"- Selected dropout after homology val sweep: **{best_drop}**",
        "- Adam 1e-3, weight_decay 1e-4, pos_weight for class balance, seed 42",
        "- Early stopping on val ROC-AUC (patience 8, max 40 epochs)",
        "",
        "## Homology test (primary)",
        "",
        "| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| Phase 2 RF | {fmt(rf_h['accuracy'])} | {fmt(rf_h['macro_f1'])} | {fmt(rf_h['roc_auc'])} | {fmt(rf_h['pr_auc'])} | {rf_h['tn']} | {rf_h['fp']} | {rf_h['fn']} | {rf_h['tp']} |",
        f"| Phase 3 ESM-2 35M linear | {fmt(esm_h['accuracy'])} | {fmt(esm_h['macro_f1'])} | {fmt(esm_h['roc_auc'])} | {fmt(esm_h['pr_auc'])} | {esm_h['tn']} | {esm_h['fp']} | {esm_h['fn']} | {esm_h['tp']} |",
        f"| Phase 4 1D-CNN | {fmt(cnn_h['accuracy'])} | {fmt(cnn_h['macro_f1'])} | {fmt(cnn_h['roc_auc'])} | {fmt(cnn_h['pr_auc'])} | {cnn_h['tn']} | {cnn_h['fp']} | {cnn_h['fn']} | {cnn_h['tp']} |",
        "",
        "## Random-split test (leakage control, separately trained)",
        "",
        "| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Phase 2 RF | {fmt(rf_r['accuracy'])} | {fmt(rf_r['macro_f1'])} | {fmt(rf_r['roc_auc'])} | {fmt(rf_r['pr_auc'])} |",
        f"| Phase 3 ESM-2 35M linear | {fmt(esm_r['accuracy'])} | {fmt(esm_r['macro_f1'])} | {fmt(esm_r['roc_auc'])} | {fmt(esm_r['pr_auc'])} |",
        f"| Phase 4 1D-CNN | {fmt(cnn_r['accuracy'])} | {fmt(cnn_r['macro_f1'])} | {fmt(cnn_r['roc_auc'])} | {fmt(cnn_r['pr_auc'])} |",
        "",
        f"Homology-train ∩ random-test IDs: {overlap['hom_train_and_rand_test']} / {overlap['rand_test']}.",
        "That is why a **separately trained** random-split CNN is used for the leakage table.",
        "",
        "## Versions",
        "",
    ]
    for k, v in ver.items():
        summary.append(f"- {k}: `{v}`")
    summary += [
        "",
        "## Files",
        "",
        "- Weights: `models/cnn1d/`",
        "- Metrics/plots: `reports/cnn1d/`",
        "- Integer encodings (new folder only): `data/processed/cnn1d/`",
        "",
    ]
    (REPORT_DIR / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    report = [
        "# Phase 4 report — 1D-CNN",
        "",
        f"**Status:** complete  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  ",
        "**Scope:** small 1D-CNN on 21-channel one-hot peptides. No ESM input, no IG, no Streamlit, no temperature scaling.",
        "",
        "Locked Phase 1–3 paths were not modified.",
        "",
        "## Setup",
        "",
        "| Item | Value |",
        "| --- | --- |",
        "| Input | homology `data/splits/{train,val,test}.fasta` |",
        "| Alphabet | 20 AA + X (21st channel); pad = all-zero columns |",
        "| Max length | 100 |",
        f"| Conv | 21→64 (k=5), 64→128 (k=5), 128→128 (k=3) |",
        "| Pool | global max |",
        "| Head | 128→64→1, ReLU, dropout |",
        f"| Dropout (val-selected) | {best_drop} |",
        "| Loss | BCEWithLogits + pos_weight |",
        "| Seed | 42 |",
        f"| Device | {ver.get('device')} |",
        "",
        "## Homology test comparison",
        "",
        "| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| Phase 2 RF (locked) | {fmt(rf_h['accuracy'])} | {fmt(rf_h['macro_f1'])} | {fmt(rf_h['roc_auc'])} | {fmt(rf_h['pr_auc'])} | {rf_h['tn']} | {rf_h['fp']} | {rf_h['fn']} | {rf_h['tp']} |",
        f"| Phase 3 ESM-2 35M linear (locked) | {fmt(esm_h['accuracy'])} | {fmt(esm_h['macro_f1'])} | {fmt(esm_h['roc_auc'])} | {fmt(esm_h['pr_auc'])} | {esm_h['tn']} | {esm_h['fp']} | {esm_h['fn']} | {esm_h['tp']} |",
        f"| Phase 4 1D-CNN | {fmt(cnn_h['accuracy'])} | {fmt(cnn_h['macro_f1'])} | {fmt(cnn_h['roc_auc'])} | {fmt(cnn_h['pr_auc'])} | {cnn_h['tn']} | {cnn_h['fp']} | {cnn_h['fn']} | {cnn_h['tp']} |",
        "",
        "## Leakage control (random split, separately trained CNN)",
        "",
        f"| model | ROC-AUC | PR-AUC | acc |",
        "| --- | ---: | ---: | ---: |",
        f"| Phase 2 RF | {fmt(rf_r['roc_auc'])} | {fmt(rf_r['pr_auc'])} | {fmt(rf_r['accuracy'])} |",
        f"| Phase 3 ESM-2 35M linear | {fmt(esm_r['roc_auc'])} | {fmt(esm_r['pr_auc'])} | {fmt(esm_r['accuracy'])} |",
        f"| Phase 4 1D-CNN | {fmt(cnn_r['roc_auc'])} | {fmt(cnn_r['pr_auc'])} | {fmt(cnn_r['accuracy'])} |",
        "",
        f"CNN leakage gap (random − homology ROC-AUC): **{cnn_r['roc_auc'] - cnn_h['roc_auc']:+.4f}**.",
        "",
        "## Light val tuning",
        "",
        "Tried dropout ∈ {0.20, 0.35} on homology val ROC-AUC; winner reused for the random-split run.",
        "",
        "## Files",
        "",
        "- `models/cnn1d/homology_cnn1d.pt`, `models/cnn1d/random_cnn1d.pt`",
        "- `reports/cnn1d/SUMMARY.md`, `metrics.csv`, plots",
        "- `reports/phase_4_report.md`",
        "- `data/processed/cnn1d/*.npz` (integer encodings only; new folder)",
        "",
        "## What this does not claim",
        "",
        "A 1D-CNN motif detector under a 30% homology split, not a wet-lab AMP assay.",
        "",
    ]
    (ROOT / "reports" / "phase_4_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main():
    set_seed(SEED)
    TENSOR_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}", flush=True)

    homology = load_split("")
    random_feat = load_split("random_")
    for name, feat in (("homology", homology), ("random", random_feat)):
        for fold in ("train", "val", "test"):
            np.savez_compressed(
                TENSOR_DIR / f"{name}_{fold}.npz",
                ids=np.asarray(feat[fold]["ids"]),
                y=feat[fold]["y"],
                idx=feat[fold]["idx"],
                alphabet=np.array(AA21),
            )

    hom_tr = set(homology["train"]["ids"])
    rand_te = set(random_feat["test"]["ids"])
    overlap = {
        "hom_train_and_rand_test": len(hom_tr & rand_te),
        "rand_test": len(rand_te),
    }
    print(f"overlap homology-train ∩ random-test = {overlap}", flush=True)

    # Light val sweep on homology only
    candidates = [0.20, 0.35]
    sweep = []
    best_drop, best_auc, best_model, best_hist = None, -1.0, None, None
    for drop in candidates:
        print(f"homology sweep dropout={drop}", flush=True)
        model, auc, hist = train_one(
            homology["train"]["idx"],
            homology["train"]["y"],
            homology["val"]["idx"],
            homology["val"]["y"],
            dropout=drop,
            device=device,
        )
        sweep.append({"dropout": drop, "val_roc_auc": auc, "epochs": len(hist)})
        print(f"  val ROC-AUC={auc:.4f} epochs={len(hist)}", flush=True)
        if auc > best_auc:
            best_auc, best_drop, best_model, best_hist = auc, drop, model, hist

    torch.save(
        {
            "state_dict": best_model.state_dict(),
            "dropout": best_drop,
            "alphabet": AA21,
            "max_len": MAX_LEN,
            "seed": SEED,
        },
        MODEL_DIR / "homology_cnn1d.pt",
    )

    print(f"training random-split CNN with dropout={best_drop}", flush=True)
    rand_model, rand_auc, rand_hist = train_one(
        random_feat["train"]["idx"],
        random_feat["train"]["y"],
        random_feat["val"]["idx"],
        random_feat["val"]["y"],
        dropout=best_drop,
        device=device,
    )
    print(f"  random val ROC-AUC={rand_auc:.4f}", flush=True)
    torch.save(
        {
            "state_dict": rand_model.state_dict(),
            "dropout": best_drop,
            "alphabet": AA21,
            "max_len": MAX_LEN,
            "seed": SEED,
        },
        MODEL_DIR / "random_cnn1d.pt",
    )

    rows = []
    rows.extend(eval_split(best_model, homology, "homology", device))
    rows.extend(eval_split(rand_model, random_feat, "random", device))

    # Also score the homology-trained weights on random test (requested), but do not
    # use those numbers as the leakage table — overlap makes them leaky.
    leaky_prob = predict_proba(best_model, random_feat["test"]["idx"], device)
    leaky = metrics_block(
        random_feat["test"]["y"],
        leaky_prob,
        (leaky_prob >= 0.5).astype(np.int8),
    )
    leaky.update(
        {
            "split": "random_scored_by_homology_cnn",
            "model": "cnn1d",
            "fold": "test",
            "note": "NOT a valid leakage comparison; IDs overlap homology train",
        }
    )
    rows.append(leaky)

    ver = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "seed": SEED,
        "dropout": best_drop,
        "homology_val_roc_auc": best_auc,
        "random_val_roc_auc": rand_auc,
        "sweep": sweep,
        "n_params": int(sum(p.numel() for p in best_model.parameters())),
        "input": "21-channel one-hot (20 AA + X), not ESM",
    }
    (MODEL_DIR / "config.json").write_text(json.dumps(ver, indent=2) + "\n")
    (REPORT_DIR / "versions.json").write_text(json.dumps(ver, indent=2) + "\n")
    (REPORT_DIR / "metrics.json").write_text(json.dumps(rows, indent=2) + "\n")
    (REPORT_DIR / "train_history_homology.json").write_text(
        json.dumps(best_hist, indent=2) + "\n"
    )
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
    with (REPORT_DIR / "metrics.csv").open("w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            if r["fold"] != "test" and r["split"].startswith("random_scored"):
                continue
            f.write(
                ",".join(
                    str(r[k]) if not isinstance(r.get(k), float) else f"{r[k]:.6f}"
                    for k in keys
                )
                + "\n"
            )

    write_reports(rows, best_drop, ver, best_hist, overlap)

    cnn_h = pick(rows, "homology", "cnn1d", "test")
    rf = json.loads(BASELINE_METRICS.read_text(encoding="utf-8"))
    esm = json.loads(ESM_METRICS.read_text(encoding="utf-8"))
    rf_h = pick(rf, "homology", "rf", "test")
    esm_h = pick(esm, "homology", "linear", "test")
    print()
    print("=" * 96)
    print("HOMOLOGY TEST  RF vs ESM-2 35M vs 1D-CNN")
    print("=" * 96)
    print(f"{'model':<28} {'acc':>8} {'macroF1':>8} {'ROC-AUC':>8} {'PR-AUC':>8}  {'TN':>5} {'FP':>5} {'FN':>5} {'TP':>5}")
    print("-" * 96)
    for label, r in (
        ("Phase2 RF", rf_h),
        ("Phase3 ESM-2 35M linear", esm_h),
        ("Phase4 1D-CNN", cnn_h),
    ):
        print(
            f"{label:<28} {r['accuracy']:8.4f} {r['macro_f1']:8.4f} "
            f"{r['roc_auc']:8.4f} {r['pr_auc']:8.4f}  "
            f"{r['tn']:5d} {r['fp']:5d} {r['fn']:5d} {r['tp']:5d}"
        )
    print("=" * 96)
    cnn_r = pick(rows, "random", "cnn1d", "test")
    print(f"random-split CNN test ROC-AUC={cnn_r['roc_auc']:.4f}  (separately trained)")
    print(f"wrote {MODEL_DIR}")
    print(f"wrote {REPORT_DIR}")
    print(f"wrote {ROOT / 'reports' / 'phase_4_report.md'}")


if __name__ == "__main__":
    main()
