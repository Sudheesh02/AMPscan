#!/usr/bin/env python3
"""Phase 9: frozen ESM-2 150M mean-pool + linear (MLP only if val clearly worse).

Homology train/val for selection. Homology test touched once at the end.
Does not modify Phases 1–8 artifacts.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from transformers import AutoModel, AutoTokenizer

SEED = 42
MODEL_ID = "facebook/esm2_t30_150M_UR50D"
MAX_LEN = 128
BATCH = 8
RF_VAL_AUC = 0.9513491183415527  # locked Phase-2 RF homology val
RF_TEST_AUC = 0.9514824813345495  # locked Phase-2 RF homology test
MLP_IF_LINEAR_BELOW = RF_VAL_AUC - 0.02

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "splits"
EMB_DIR = ROOT / "data" / "processed" / "embeddings" / "esm2_150M"
MODEL_DIR = ROOT / "models" / "esm2_150M"
REPORT_DIR = ROOT / "reports" / "esm2_150M"
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
def embed_sequences(seqs, tokenizer, model, device, batch=BATCH):
    model.eval()
    out = np.zeros((len(seqs), model.config.hidden_size), dtype=np.float32)
    cls_id, eos_id, pad_id = tokenizer.cls_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id
    use_cuda = device.type == "cuda"
    for start in range(0, len(seqs), batch):
        chunk = seqs[start : start + batch]
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
            hidden = model(**enc).last_hidden_state
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
        if start % (batch * 40) == 0:
            print(f"  embedded {min(start + batch, len(seqs))}/{len(seqs)}", flush=True)
    return out


def metrics_block(y_true, y_prob):
    pred = (y_prob >= 0.5).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro")),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "n": int(len(y_true)),
    }


class TinyMLP(nn.Module):
    def __init__(self, d_in: int, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_mlp(Xtr, ytr, Xva, yva):
    set_seed(SEED)
    pos = float((ytr == 1).sum())
    neg = float((ytr == 0).sum())
    pos_weight = torch.tensor([neg / max(pos, 1.0)])
    model = TinyMLP(Xtr.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    Xtr_t = torch.from_numpy(Xtr.astype(np.float32))
    ytr_t = torch.from_numpy(ytr.astype(np.float32))
    Xva_t = torch.from_numpy(Xva.astype(np.float32))
    best_auc, best_state, wait = -1.0, None, 0
    for _epoch in range(80):
        model.train()
        perm = torch.randperm(len(ytr_t))
        for i in range(0, len(ytr_t), 256):
            idx = perm[i : i + 256]
            opt.zero_grad()
            loss = loss_fn(model(Xtr_t[idx]), ytr_t[idx])
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


def main():
    set_seed(SEED)
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    HF_HOME.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} model={MODEL_ID} batch={BATCH}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)
    for p in model.parameters():
        p.requires_grad = False
    model.to(device)
    model.eval()
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert n_train == 0
    print(f"hidden={model.config.hidden_size} trainable={n_train}", flush=True)

    print("Extracting homology embeddings (frozen)", flush=True)
    id_to_vec = {}
    homology = {}
    for fold in ("train", "val", "test"):
        ids, y, seqs = load_fold("", fold)
        X = embed_sequences(seqs, tokenizer, model, device)
        homology[fold] = {"ids": ids, "y": y, "X": X}
        np.savez_compressed(
            EMB_DIR / f"homology_{fold}.npz",
            ids=np.asarray(ids),
            y=y,
            X=X,
            model_id=np.array(MODEL_ID),
        )
        for i, sid in enumerate(ids):
            id_to_vec[sid] = X[i]
        print(f"  homology {fold}: n={len(y)} dim={X.shape[1]}", flush=True)

    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()

    print("Assembling random-split matrices from ID map (no second ESM pass)", flush=True)
    for fold in ("train", "val", "test"):
        ids, y, _ = load_fold("random_", fold)
        missing = [s for s in ids if s not in id_to_vec]
        if missing:
            raise SystemExit(f"random {fold} missing embeddings: {missing[:3]}")
        X = np.stack([id_to_vec[s] for s in ids]).astype(np.float32)
        np.savez_compressed(EMB_DIR / f"random_{fold}.npz", ids=np.asarray(ids), y=y, X=X)
        print(f"  random {fold}: n={len(y)}", flush=True)

    scaler = StandardScaler()
    Xtr = scaler.fit_transform(homology["train"]["X"])
    Xva = scaler.transform(homology["val"]["X"])
    ytr, yva = homology["train"]["y"], homology["val"]["y"]

    lin = LogisticRegression(
        C=1.0, solver="lbfgs", max_iter=2000, class_weight="balanced", random_state=SEED
    )
    lin.fit(Xtr, ytr)
    p_va_lin = lin.predict_proba(Xva)[:, 1]
    lin_val = float(roc_auc_score(yva, p_va_lin))
    print(f"LINEAR val ROC-AUC={lin_val:.4f}  (locked RF val={RF_VAL_AUC:.4f})", flush=True)

    selected = "linear"
    mlp = None
    mlp_val = None
    predict_va = p_va_lin
    if lin_val < MLP_IF_LINEAR_BELOW:
        print("linear clearly below RF-val-0.02 — training tiny MLP on val only", flush=True)
        mlp, mlp_val = train_mlp(Xtr, ytr, Xva, yva)
        print(f"MLP val ROC-AUC={mlp_val:.4f}", flush=True)
        if mlp_val > lin_val + 0.01:
            selected = "mlp"
            with torch.no_grad():
                predict_va = torch.sigmoid(
                    mlp(torch.from_numpy(Xva.astype(np.float32)))
                ).numpy()

    val_auc = float(roc_auc_score(yva, predict_va))
    gap_to_rf_val = RF_VAL_AUC - val_auc
    print(f"SELECTED {selected} val ROC-AUC={val_auc:.4f}  gap_to_RF_val={gap_to_rf_val:+.4f}", flush=True)

    lora_eligible = gap_to_rf_val <= 0.01
    if lora_eligible:
        print(
            "NOTE: frozen val is within 0.01 of RF val. LoRA is allowed only if you ask. Not training LoRA.",
            flush=True,
        )
    else:
        print("LoRA not considered (frozen val not within 0.01 of RF val).", flush=True)

    joblib.dump(scaler, MODEL_DIR / "homology_scaler.joblib")
    joblib.dump(lin, MODEL_DIR / "homology_logreg.joblib")
    if mlp is not None:
        torch.save({"state_dict": mlp.state_dict(), "d_in": Xtr.shape[1]}, MODEL_DIR / "homology_mlp.pt")

    # --- TEST ONCE ---
    print("SCORING HOMOLOGY TEST ONCE", flush=True)
    Xte = scaler.transform(homology["test"]["X"])
    yte = homology["test"]["y"]
    if selected == "linear":
        p_te = lin.predict_proba(Xte)[:, 1]
    else:
        with torch.no_grad():
            p_te = torch.sigmoid(mlp(torch.from_numpy(Xte.astype(np.float32)))).numpy()
    test_m = metrics_block(yte, p_te)
    val_m = metrics_block(yva, predict_va)
    print(
        f"TEST  acc={test_m['accuracy']:.4f}  macroF1={test_m['macro_f1']:.4f}  "
        f"ROC-AUC={test_m['roc_auc']:.4f}  PR-AUC={test_m['pr_auc']:.4f}",
        flush=True,
    )
    beat = test_m["roc_auc"] > RF_TEST_AUC + 1e-6
    print(
        f"vs locked RF test ROC-AUC {RF_TEST_AUC:.4f}: "
        f"{'BEATS RF' if beat else 'DOES NOT BEAT RF'}  Δ={test_m['roc_auc']-RF_TEST_AUC:+.4f}",
        flush=True,
    )

    payload = {
        "model_id": MODEL_ID,
        "frozen": True,
        "selected_head": selected,
        "linear_val_roc_auc": lin_val,
        "mlp_val_roc_auc": mlp_val,
        "val": val_m,
        "test": test_m,
        "rf_val_roc_auc": RF_VAL_AUC,
        "rf_test_roc_auc": RF_TEST_AUC,
        "beats_rf_test": beat,
        "lora_eligible_on_val": lora_eligible,
        "lora_trained": False,
        "seed": SEED,
        "batch": BATCH,
    }
    (MODEL_DIR / "homology_head_meta.json").write_text(json.dumps(payload, indent=2) + "\n")
    (REPORT_DIR / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")

    built = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    verdict = (
        f"Frozen ESM-2 150M **does not beat** locked RF homology-test ROC-AUC "
        f"({test_m['roc_auc']:.4f} vs {RF_TEST_AUC:.4f}). Stop. No LoRA."
        if not beat
        else f"Frozen ESM-2 150M **beats** locked RF ({test_m['roc_auc']:.4f} vs {RF_TEST_AUC:.4f})."
    )
    report = f"""# Phase 9 report — frozen ESM-2 150M

**Status:** complete (one homology-test evaluation)  
**Date:** {built}  
**Encoder:** `{MODEL_ID}` frozen, mean-pool residue tokens (CLS/EOS/PAD excluded).  
**Head:** {selected} (linear val ROC-AUC={lin_val:.4f}{'' if mlp_val is None else f'; MLP val={mlp_val:.4f}'}).  
Test was scored **once** after val selection.

## Homology

| set | model | ROC-AUC | PR-AUC | accuracy | macro-F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| val | ESM-2 150M {selected} | {val_m['roc_auc']:.4f} | {val_m['pr_auc']:.4f} | {val_m['accuracy']:.4f} | {val_m['macro_f1']:.4f} |
| val | Phase 2 RF (locked) | {RF_VAL_AUC:.4f} | — | — | — |
| **test** | ESM-2 150M {selected} | **{test_m['roc_auc']:.4f}** | {test_m['pr_auc']:.4f} | {test_m['accuracy']:.4f} | {test_m['macro_f1']:.4f} |
| **test** | Phase 2 RF (locked) | **{RF_TEST_AUC:.4f}** | 0.9542 | 0.8734 | 0.8734 |

Δ test ROC-AUC vs RF: **{test_m['roc_auc']-RF_TEST_AUC:+.4f}**.

## Verdict

{verdict}

LoRA: {'val was within 0.01 of RF — not trained because the protocol says ask first.' if lora_eligible else 'not eligible (val not within 0.01 of RF).'}

Embeddings: `data/processed/embeddings/esm2_150M/` (new folder). Head: `models/esm2_150M/`.
Random-split `.npz` files were assembled from the homology ID map; they were not used for the test comparison.
"""
    (ROOT / "reports" / "phase_9_report.md").write_text(report)
    (REPORT_DIR / "SUMMARY.md").write_text(report)
    print(f"wrote {ROOT / 'reports' / 'phase_9_report.md'}")


if __name__ == "__main__":
    main()
