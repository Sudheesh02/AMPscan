#!/usr/bin/env python3
"""Phase 3: frozen ESM-2 35M mean-pool embeddings + linear (or tiny MLP) head.

Does not fine-tune ESM. Does not touch models/baseline/ or reports/baseline/.
Homology embeddings are extracted with the frozen encoder; random-split
matrices are assembled from the same ID→vector store (same 21337 sequences).
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
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
from transformers import AutoModel, AutoTokenizer

SEED = 42
MODEL_ID = "facebook/esm2_t12_35M_UR50D"
MAX_LEN = 128  # peptides are 5–100 + specials
BATCH = 32
PH3_HIDDEN = 128  # MLP hidden size if used

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "splits"
EMB_DIR = ROOT / "data" / "processed" / "embeddings" / "esm2_35M"
MODEL_DIR = ROOT / "models" / "esm2_35M"
REPORT_DIR = ROOT / "reports" / "esm2_35M"
BASELINE_METRICS = ROOT / "reports" / "baseline" / "metrics.json"
HF_HOME = ROOT / ".cache" / "huggingface"


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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


def load_fold(prefix: str, fold: str):
    return parse_fasta(SPLITS / f"{prefix}{fold}.fasta")


@torch.no_grad()
def embed_sequences(seqs, tokenizer, model, device):
    """Mean-pool residue tokens (exclude CLS/EOS/PAD). ESM weights stay frozen."""
    model.eval()
    out = np.zeros((len(seqs), model.config.hidden_size), dtype=np.float32)
    cls_id = tokenizer.cls_token_id
    eos_id = tokenizer.eos_token_id
    pad_id = tokenizer.pad_token_id
    use_cuda = device.type == "cuda"
    for start in range(0, len(seqs), BATCH):
        chunk = seqs[start : start + BATCH]
        enc = tokenizer(
            chunk,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
            add_special_tokens=True,
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_cuda):
            hidden = model(**enc).last_hidden_state  # [B, L, H]
        ids = enc["input_ids"]
        mask = enc["attention_mask"].bool()
        special = torch.zeros_like(mask)
        if cls_id is not None:
            special |= ids == cls_id
        if eos_id is not None:
            special |= ids == eos_id
        if pad_id is not None:
            special |= ids == pad_id
        keep = mask & ~special
        keep_f = keep.unsqueeze(-1).to(hidden.dtype)
        denom = keep_f.sum(dim=1).clamp(min=1.0)
        pooled = (hidden * keep_f).sum(dim=1) / denom
        out[start : start + len(chunk)] = pooled.float().cpu().numpy()
        if start % (BATCH * 20) == 0:
            print(f"  embedded {min(start + BATCH, len(seqs))}/{len(seqs)}", flush=True)
    return out


def save_npz(path: Path, ids, y, X, extra=None):
    kw = dict(ids=np.asarray(ids), y=y, X=X)
    if extra:
        kw.update(extra)
    np.savez_compressed(path, **kw)


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


class TinyMLP(nn.Module):
    def __init__(self, d_in: int, hidden: int = PH3_HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_mlp(Xtr, ytr, Xva, yva, seed=SEED, max_epochs=80):
    set_seed(seed)
    device = torch.device("cpu")  # 21k x 480; CPU is enough and deterministic-ish
    pos = float((ytr == 1).sum())
    neg = float((ytr == 0).sum())
    pos_weight = torch.tensor([neg / max(pos, 1.0)], dtype=torch.float32)
    model = TinyMLP(Xtr.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    Xtr_t = torch.from_numpy(Xtr.astype(np.float32))
    ytr_t = torch.from_numpy(ytr.astype(np.float32))
    Xva_t = torch.from_numpy(Xva.astype(np.float32))
    best_auc, best_state, wait = -1.0, None, 0
    for epoch in range(1, max_epochs + 1):
        model.train()
        perm = torch.randperm(len(ytr_t))
        for i in range(0, len(ytr_t), 256):
            idx = perm[i : i + 256]
            opt.zero_grad()
            logits = model(Xtr_t[idx])
            loss = loss_fn(logits, ytr_t[idx])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            p = torch.sigmoid(model(Xva_t)).numpy()
        auc = roc_auc_score(yva, p)
        if auc > best_auc + 1e-4:
            best_auc = auc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= 12:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, float(best_auc)


@torch.no_grad()
def mlp_proba(model, X):
    model.eval()
    t = torch.from_numpy(X.astype(np.float32))
    return torch.sigmoid(model(t)).numpy()


def fit_linear(Xtr, ytr):
    clf = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=SEED,
    )
    clf.fit(Xtr, ytr)
    return clf


def eval_model(name, predict_proba, feat, split_name):
    rows = []
    test_prob = None
    test_y = None
    for fold in ("val", "test"):
        X, y = feat[fold]["X"], feat[fold]["y"]
        prob = predict_proba(X)
        pred = (prob >= 0.5).astype(np.int8)
        m = metrics_block(y, prob, pred)
        m.update({"split": split_name, "model": name, "fold": fold})
        rows.append(m)
        cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]], dtype=int)
        plot_confusion(
            cm,
            f"{split_name} {name} {fold}",
            REPORT_DIR / f"cm_{split_name}_{name}_{fold}.png",
        )
        if fold == "test":
            test_prob, test_y = prob, y
    plot_roc_pr(name, test_y, test_prob, f"{split_name}_{name}")
    return rows


def versions(device):
    import sklearn
    import transformers

    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "sklearn": sklearn.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "seed": SEED,
        "esm_model": MODEL_ID,
        "pooling": "mean of residue tokens (exclude CLS/EOS/PAD)",
        "esm_frozen": True,
        "batch_size": BATCH,
        "amp_fp16": device.type == "cuda",
    }


def write_summary(rows, selected, ver, rf_rows):
    def fmt(x):
        return f"{x:.4f}" if isinstance(x, float) else str(x)

    def pick(rows, split, model, fold):
        for r in rows:
            if r["split"] == split and r["model"] == model and r["fold"] == fold:
                return r
        return None

    esm_h = pick(rows, "homology", selected, "test")
    rf_h = pick(rf_rows, "homology", "rf", "test")
    esm_r = pick(rows, "random", selected, "test")
    rf_r = pick(rf_rows, "random", "rf", "test")

    lines = [
        "# ESM-2 35M frozen head vs classical RF",
        "",
        f"Built: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "Phase 3 only. ESM-2 encoder is **frozen**. No 150M, CNN, Streamlit, or IG.",
        "",
        "## Setup",
        "",
        f"- Encoder: `{MODEL_ID}` (hidden size 480, 12 layers)",
        "- Pooling: mean over residue tokens; CLS / EOS / PAD excluded",
        f"- Batch size `{BATCH}`, fp16 autocast on CUDA, no ESM gradient updates",
        f"- Seed `{SEED}`, class_weight=balanced (linear) / pos_weight (MLP)",
        f"- Selected head: **{selected}**",
        "- Linear: L2 logistic regression, C=1.0, StandardScaler fit on train embeddings",
        f"- Tiny MLP (fallback): 480→{PH3_HIDDEN} ReLU Dropout(0.2)→1, trained only if linear under-fits val",
        "- Homology split is the honest number. Random split is the leakage control.",
        "",
        "## Package / hardware versions",
        "",
    ]
    for k, v in ver.items():
        lines.append(f"- {k}: `{v}`")

    lines += [
        "",
        "## Homology test: classical RF vs ESM-2 35M head",
        "",
        "| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if rf_h:
        lines.append(
            f"| Phase 2 RF | {fmt(rf_h['accuracy'])} | {fmt(rf_h['macro_f1'])} | "
            f"{fmt(rf_h['roc_auc'])} | {fmt(rf_h['pr_auc'])} | "
            f"{rf_h['tn']} | {rf_h['fp']} | {rf_h['fn']} | {rf_h['tp']} |"
        )
    if esm_h:
        lines.append(
            f"| ESM-2 35M {selected} | {fmt(esm_h['accuracy'])} | {fmt(esm_h['macro_f1'])} | "
            f"{fmt(esm_h['roc_auc'])} | {fmt(esm_h['pr_auc'])} | "
            f"{esm_h['tn']} | {esm_h['fp']} | {esm_h['fn']} | {esm_h['tp']} |"
        )

    lines += [
        "",
        "## Random-split test (leakage control)",
        "",
        "| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    if rf_r:
        lines.append(
            f"| Phase 2 RF | {fmt(rf_r['accuracy'])} | {fmt(rf_r['macro_f1'])} | "
            f"{fmt(rf_r['roc_auc'])} | {fmt(rf_r['pr_auc'])} |"
        )
    if esm_r:
        lines.append(
            f"| ESM-2 35M {selected} | {fmt(esm_r['accuracy'])} | {fmt(esm_r['macro_f1'])} | "
            f"{fmt(esm_r['roc_auc'])} | {fmt(esm_r['pr_auc'])} |"
        )

    lines += [
        "",
        "## All ESM-2 head metrics",
        "",
        "| split | head | fold | accuracy | macro-F1 | ROC-AUC | PR-AUC |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {r['split']} | {r['model']} | {r['fold']} | {fmt(r['accuracy'])} | "
            f"{fmt(r['macro_f1'])} | {fmt(r['roc_auc'])} | {fmt(r['pr_auc'])} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Existing Phase-1 FASTAs and Phase-2 `models/baseline/`, `reports/baseline/` were not modified.",
        "- Random-split embedding matrices reuse the homology-extracted ID→vector store",
        "  (same 21,337 peptides; no second ESM pass).",
        "",
        "## Files",
        "",
        "- Embeddings: `data/processed/embeddings/esm2_35M/*.npz`",
        "- Model + scaler: `models/esm2_35M/`",
        "- This report: `reports/esm2_35M/`",
        "",
    ]
    (REPORT_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    set_seed(SEED)
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    HF_HOME.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}", flush=True)
    if device.type == "cuda":
        print(f"gpu={torch.cuda.get_device_name(0)} mem={torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB", flush=True)

    print(f"Loading {MODEL_ID} (frozen)", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)
    for p in model.parameters():
        p.requires_grad = False
    model.to(device)
    model.eval()
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert n_train == 0, n_train
    print(f"hidden={model.config.hidden_size} trainable={n_train}", flush=True)

    # Homology split: extract embeddings
    print("Extracting homology-split embeddings", flush=True)
    id_to_vec = {}
    homology = {}
    for fold in ("train", "val", "test"):
        ids, y, seqs = load_fold("", fold)
        X = embed_sequences(seqs, tokenizer, model, device)
        homology[fold] = {"ids": ids, "y": y, "X": X}
        save_npz(
            EMB_DIR / f"homology_{fold}.npz",
            ids,
            y,
            X,
            extra={"model_id": np.array(MODEL_ID), "pooling": np.array("mean_residue")},
        )
        for i, sid in enumerate(ids):
            id_to_vec[sid] = X[i]
        print(f"  homology {fold}: n={len(y)} pos={int(y.sum())} dim={X.shape[1]}", flush=True)

    # Free ESM GPU memory before head training
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()

    # Random-split matrices from the same vectors (no second ESM pass)
    print("Assembling random-split matrices from homology embeddings", flush=True)
    random_feat = {}
    for fold in ("train", "val", "test"):
        ids, y, _seqs = load_fold("random_", fold)
        missing = [s for s in ids if s not in id_to_vec]
        if missing:
            raise SystemExit(f"{len(missing)} random {fold} IDs lack embeddings (e.g. {missing[:3]})")
        X = np.stack([id_to_vec[s] for s in ids]).astype(np.float32)
        random_feat[fold] = {"ids": ids, "y": y, "X": X}
        save_npz(EMB_DIR / f"random_{fold}.npz", ids, y, X)
        print(f"  random {fold}: n={len(y)} pos={int(y.sum())}", flush=True)

    (EMB_DIR / "README.txt").write_text(
        f"Frozen {MODEL_ID} mean-pooled residue embeddings.\n"
        f"homology_*.npz extracted with the encoder; random_*.npz assembled by ID.\n"
        f"seed={SEED} batch={BATCH} max_len={MAX_LEN}\n",
        encoding="utf-8",
    )

    # Train heads independently on each split
    rf_rows = json.loads(BASELINE_METRICS.read_text(encoding="utf-8"))
    rf_h_val = next(r for r in rf_rows if r["split"] == "homology" and r["model"] == "rf" and r["fold"] == "val")

    all_rows = []
    selected_per_split = {}
    for split_name, feat in (("homology", homology), ("random", random_feat)):
        print(f"Training heads on {split_name}", flush=True)
        scaler = StandardScaler()
        Xtr_s = scaler.fit_transform(feat["train"]["X"])
        Xva_s = scaler.transform(feat["val"]["X"])
        Xte_s = scaler.transform(feat["test"]["X"])
        scaled = {
            "train": {"X": Xtr_s, "y": feat["train"]["y"]},
            "val": {"X": Xva_s, "y": feat["val"]["y"]},
            "test": {"X": Xte_s, "y": feat["test"]["y"]},
        }
        lin = fit_linear(Xtr_s, feat["train"]["y"])
        lin_val = roc_auc_score(feat["val"]["y"], lin.predict_proba(Xva_s)[:, 1])
        print(f"  linear val ROC-AUC={lin_val:.4f} (RF homology val={rf_h_val['roc_auc']:.4f})", flush=True)

        use_mlp = False
        mlp = None
        mlp_val = None
        # Under-fit rule: linear clearly below the Phase-2 RF val on homology,
        # or (for either split) try MLP if linear val < 0.90.
        if split_name == "homology" and lin_val < rf_h_val["roc_auc"] - 0.02:
            use_mlp = True
        if lin_val < 0.90:
            use_mlp = True
        if use_mlp:
            print("  linear under-fit on val — training tiny MLP", flush=True)
            mlp, mlp_val = train_mlp(Xtr_s, feat["train"]["y"], Xva_s, feat["val"]["y"])
            print(f"  mlp val ROC-AUC={mlp_val:.4f}", flush=True)
            # keep linear unless MLP wins by a clear margin
            if mlp_val > lin_val + 0.01:
                selected = "mlp"
            else:
                selected = "linear"
                use_mlp = False
        else:
            selected = "linear"

        selected_per_split[split_name] = selected
        joblib.dump(scaler, MODEL_DIR / f"{split_name}_scaler.joblib")
        joblib.dump(lin, MODEL_DIR / f"{split_name}_logreg.joblib")
        if mlp is not None:
            torch.save(
                {"state_dict": mlp.state_dict(), "d_in": feat["train"]["X"].shape[1], "hidden": PH3_HIDDEN},
                MODEL_DIR / f"{split_name}_mlp.pt",
            )

        all_rows.extend(
            eval_model("linear", lambda X, m=lin: m.predict_proba(X)[:, 1], scaled, split_name)
        )
        if mlp is not None:
            all_rows.extend(
                eval_model("mlp", lambda X, m=mlp: mlp_proba(m, X), scaled, split_name)
            )

        meta = {
            "selected_head": selected,
            "linear_val_roc_auc": float(lin_val),
            "mlp_val_roc_auc": float(mlp_val) if mlp_val is not None else None,
            "esm_frozen": True,
            "model_id": MODEL_ID,
        }
        (MODEL_DIR / f"{split_name}_head_meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    ver = versions(device)
    (REPORT_DIR / "versions.json").write_text(json.dumps(ver, indent=2) + "\n")
    (REPORT_DIR / "metrics.json").write_text(json.dumps(all_rows, indent=2) + "\n")
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
        for r in all_rows:
            f.write(
                ",".join(
                    str(r[k]) if not isinstance(r[k], float) else f"{r[k]:.6f}" for k in keys
                )
                + "\n"
            )

    selected = selected_per_split["homology"]
    write_summary(all_rows, selected, ver, rf_rows)

    def row(split, model, fold):
        for r in all_rows:
            if r["split"] == split and r["model"] == model and r["fold"] == fold:
                return r
        return None

    esm_h = row("homology", selected, "test")
    rf_h = next(r for r in rf_rows if r["split"] == "homology" and r["model"] == "rf" and r["fold"] == "test")
    esm_r = row("random", selected_per_split["random"], "test")
    rf_r = next(r for r in rf_rows if r["split"] == "random" and r["model"] == "rf" and r["fold"] == "test")

    print()
    print("=" * 92)
    print("HOMOLOGY TEST  classical RF vs ESM-2 35M frozen head")
    print("=" * 92)
    print(f"{'model':<24} {'acc':>8} {'macroF1':>8} {'ROC-AUC':>8} {'PR-AUC':>8}  {'TN':>5} {'FP':>5} {'FN':>5} {'TP':>5}")
    print("-" * 92)
    print(
        f"{'Phase2 RF':<24} {rf_h['accuracy']:8.4f} {rf_h['macro_f1']:8.4f} "
        f"{rf_h['roc_auc']:8.4f} {rf_h['pr_auc']:8.4f}  "
        f"{rf_h['tn']:5d} {rf_h['fp']:5d} {rf_h['fn']:5d} {rf_h['tp']:5d}"
    )
    print(
        f"{'ESM-2 35M '+selected:<24} {esm_h['accuracy']:8.4f} {esm_h['macro_f1']:8.4f} "
        f"{esm_h['roc_auc']:8.4f} {esm_h['pr_auc']:8.4f}  "
        f"{esm_h['tn']:5d} {esm_h['fp']:5d} {esm_h['fn']:5d} {esm_h['tp']:5d}"
    )
    print("=" * 92)
    print(
        f"random-split test  RF ROC={rf_r['roc_auc']:.4f}  "
        f"ESM-2 {selected_per_split['random']} ROC={esm_r['roc_auc']:.4f}"
    )
    print(f"selected heads: {selected_per_split}")
    print(f"wrote {EMB_DIR}")
    print(f"wrote {MODEL_DIR}")
    print(f"wrote {REPORT_DIR}")


if __name__ == "__main__":
    main()
