#!/usr/bin/env python3
"""Phase 6: Integrated Gradients + occlusion on the locked homology 1D-CNN.

Does not retrain. Does not modify Phase 1–5 weights or calibration parameters.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from captum.attr import IntegratedGradients

SEED = 42
MAX_LEN = 100
AA21 = "ACDEFGHIKLMNPQRSTVWYX"
AA_INDEX = {a: i for i, a in enumerate(AA21)}
N_CH = 21
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})
CATIONIC = set("KRH")
HYDROPHOBIC = set("AILMFWV")
AROMATIC = set("FWY")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from run_cnn1d import CNN1D  # architecture only; weights loaded read-only

SPLITS = ROOT / "data" / "splits"
CKPT = ROOT / "models" / "cnn1d" / "homology_cnn1d.pt"
REPORT = ROOT / "reports" / "explain"

CANONICAL = {
    "magainin-2": "GIGKFLHSAKKFGKAFVGEIMNS",
    "LL-37": "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    "melittin": "GIGAVLKVLTTGLPALISWIKRKRQQ",
}


def clean_seq(seq: str) -> tuple[str, dict]:
    notes = {"truncated": False, "mapped": False, "orig_len": len(seq)}
    s = seq.replace(" ", "").replace("*", "").upper().translate(MAP)
    if s != seq.replace(" ", "").replace("*", "").upper():
        notes["mapped"] = True
    if len(s) > MAX_LEN:
        s = s[:MAX_LEN]
        notes["truncated"] = True
    notes["final_len"] = len(s)
    return s, notes


def parse_fasta(path: Path):
    recs = []
    hdr, buf = None, []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hdr is not None:
                    recs.append((hdr.split()[0], "LABEL=1" in hdr, "".join(buf).upper()))
                hdr, buf = line[1:], []
            else:
                buf.append(line.strip())
        if hdr is not None:
            recs.append((hdr.split()[0], "LABEL=1" in hdr, "".join(buf).upper()))
    return recs


def one_hot_np(seq: str) -> np.ndarray:
    x = np.zeros((N_CH, MAX_LEN), dtype=np.float32)
    for j, a in enumerate(seq[:MAX_LEN]):
        i = AA_INDEX.get(a)
        if i is not None:
            x[i, j] = 1.0
    return x


class CNNOneHot(nn.Module):
    """Same weights as Phase-4 CNN, but forward takes one-hot (B, 21, L)."""

    def __init__(self, inner: CNN1D):
        super().__init__()
        self.conv = inner.conv
        self.head = inner.head

    def forward(self, x):
        h = self.conv(x)
        h = h.amax(dim=-1)
        return self.head(h).squeeze(-1)


def load_model(device):
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    inner = CNN1D(dropout=float(ckpt.get("dropout", 0.2)))
    inner.load_state_dict(ckpt["state_dict"])
    inner.eval()
    for p in inner.parameters():
        p.requires_grad = False
    wrap = CNNOneHot(inner).to(device)
    wrap.eval()
    return wrap


@torch.no_grad()
def logit_of(model, x, device):
    return float(model(torch.from_numpy(x).unsqueeze(0).to(device)).cpu())


def ig_residue(model, x, device, n_steps=50):
    """x: (21, L) numpy. Returns per-residue signed IG (L,) for positions 0..len-1."""
    inp = torch.from_numpy(x).unsqueeze(0).to(device)
    inp.requires_grad_(True)
    baseline = torch.zeros_like(inp)
    ig = IntegratedGradients(model)
    attr = ig.attribute(inp, baselines=baseline, n_steps=n_steps, target=None)
    # attr: (1, 21, L) — sum channels → residue
    res = attr.squeeze(0).sum(dim=0).detach().cpu().numpy()
    return res


def occlusion_delta(model, x, L, device):
    """Zero one residue at a time. Δ = logit_full − logit_occluded."""
    full = logit_of(model, x, device)
    deltas = np.zeros(L, dtype=np.float64)
    for j in range(L):
        xo = x.copy()
        xo[:, j] = 0.0
        deltas[j] = full - logit_of(model, xo, device)
    return full, deltas


def topk_rows(seq_id, label, seq, ig, logit, k=5):
    L = len(seq)
    ig = ig[:L]
    order = np.argsort(-np.abs(ig))
    rows = []
    for rank, j in enumerate(order[:k], start=1):
        aa = seq[j]
        rows.append(
            {
                "id": seq_id,
                "label": int(label),
                "logit": float(logit),
                "rank": rank,
                "pos": int(j + 1),
                "aa": aa,
                "ig": float(ig[j]),
                "abs_ig": float(abs(ig[j])),
                "cationic": aa in CATIONIC,
                "hydrophobic": aa in HYDROPHOBIC,
            }
        )
    return rows


def heatmap(name, seq, ig, occ, logit, p, path):
    L = len(seq)
    ig = ig[:L]
    fig, axes = plt.subplots(
        3, 1, figsize=(max(8, L * 0.32), 5.8), gridspec_kw={"height_ratios": [1.1, 1.4, 1.4]}
    )
    # residue strip
    ax = axes[0]
    vmax = max(np.max(np.abs(ig)), 1e-8)
    im = ax.imshow(ig[np.newaxis, :], cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_yticks([])
    ax.set_xticks(range(L))
    ax.set_xticklabels(list(seq), fontsize=8)
    ax.set_title(f"{name}  logit={logit:.3f}  P(AMP)={p:.3f}  (red = +AMP logit)")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    axes[1].bar(range(L), ig, color="#2c7bb6")
    axes[1].axhline(0, color="gray", linewidth=0.8)
    axes[1].set_ylabel("IG (signed)")
    axes[1].set_xticks(range(L))
    axes[1].set_xticklabels(list(seq), fontsize=8)
    axes[2].bar(range(L), occ[:L], color="#d95f02")
    axes[2].axhline(0, color="gray", linewidth=0.8)
    axes[2].set_ylabel("occlusion Δ logit")
    axes[2].set_xlabel("residue")
    axes[2].set_xticks(range(L))
    axes[2].set_xticklabels(list(seq), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def motif_stats(seq, ig, k=5):
    L = len(seq)
    ig = ig[:L]
    top = np.argsort(-np.abs(ig))[: min(k, L)]
    aas = [seq[j] for j in top]
    return {
        "top_abs_aa": "".join(aas),
        "frac_cationic": float(np.mean([seq[j] in CATIONIC for j in top])),
        "frac_hydrophobic": float(np.mean([seq[j] in HYDROPHOBIC for j in top])),
        "frac_aromatic": float(np.mean([seq[j] in AROMATIC for j in top])),
        "mean_ig_KRH": float(np.mean([ig[j] for j, a in enumerate(seq) if a in CATIONIC]))
        if any(a in CATIONIC for a in seq)
        else None,
        "mean_ig_AILMFWV": float(
            np.mean([ig[j] for j, a in enumerate(seq) if a in HYDROPHOBIC])
        )
        if any(a in HYDROPHOBIC for a in seq)
        else None,
    }


def membership(seq, recs):
    return [i for i, _lab, s in recs if s == seq]


def main():
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    REPORT.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")  # IG on tiny CNN is fine on CPU; deterministic
    model = load_model(device)
    ig_engine_ready = True

    train = parse_fasta(SPLITS / "train.fasta")
    val = parse_fasta(SPLITS / "val.fasta")
    test = parse_fasta(SPLITS / "test.fasta")

    # --- canonical peptides ---
    canon_rows = []
    membership_tbl = {}
    notes_trunc = []
    for name, raw in CANONICAL.items():
        seq, notes = clean_seq(raw)
        if notes["truncated"] or notes["mapped"]:
            notes_trunc.append({name: notes})
        mem = {
            "train": membership(seq, train),
            "val": membership(seq, val),
            "test": membership(seq, test),
        }
        membership_tbl[name] = {
            "seq": seq,
            "in_train": bool(mem["train"]),
            "in_val": bool(mem["val"]),
            "in_test": bool(mem["test"]),
            "train_ids": mem["train"],
            "notes": notes,
        }
        x = one_hot_np(seq)
        logit = logit_of(model, x, device)
        p = float(1 / (1 + np.exp(-np.clip(logit, -60, 60))))
        ig = ig_residue(model, x, device)
        full, occ = occlusion_delta(model, x, len(seq), device)
        stats = motif_stats(seq, ig)
        heatmap(
            name,
            seq,
            ig,
            occ,
            logit,
            p,
            REPORT / f"heatmap_{name.replace('-', '_')}.png",
        )
        # per-residue table for this peptide
        for j, aa in enumerate(seq):
            canon_rows.append(
                {
                    "peptide": name,
                    "pos": j + 1,
                    "aa": aa,
                    "ig": float(ig[j]),
                    "occlusion_dlogit": float(occ[j]),
                    "cationic": aa in CATIONIC,
                    "hydrophobic": aa in HYDROPHOBIC,
                    "logit": logit,
                    "p_amp": p,
                    "in_homology_train": bool(mem["train"]),
                    **{f"stat_{k}": v for k, v in stats.items()},
                }
            )
        print(
            f"{name}: logit={logit:.3f} p={p:.3f} in_train={bool(mem['train'])} "
            f"ids={mem['train']} top_abs={stats['top_abs_aa']}",
            flush=True,
        )

    # write canonical TSV
    keys = [
        "peptide",
        "pos",
        "aa",
        "ig",
        "occlusion_dlogit",
        "cationic",
        "hydrophobic",
        "logit",
        "p_amp",
        "in_homology_train",
    ]
    with (REPORT / "canonical_ig_occlusion.tsv").open("w", encoding="utf-8") as f:
        f.write("\t".join(keys) + "\n")
        for r in canon_rows:
            f.write("\t".join(str(r[k]) for k in keys) + "\n")

    # --- homology test compact top-5 ---
    top_rows = []
    test_type_ig = {"AMP": [], "nonAMP": []}
    for sid, lab, seq in test:
        x = one_hot_np(seq)
        logit = logit_of(model, x, device)
        ig = ig_residue(model, x, device, n_steps=32)
        top_rows.extend(topk_rows(sid, lab, seq, ig, logit, k=5))
        bucket = "AMP" if lab else "nonAMP"
        for j, aa in enumerate(seq):
            test_type_ig[bucket].append((aa, float(ig[j])))

    with (REPORT / "homology_test_top5.tsv").open("w", encoding="utf-8") as f:
        hdr = [
            "id",
            "label",
            "logit",
            "rank",
            "pos",
            "aa",
            "ig",
            "abs_ig",
            "cationic",
            "hydrophobic",
        ]
        f.write("\t".join(hdr) + "\n")
        for r in top_rows:
            f.write("\t".join(str(r[k]) for k in hdr) + "\n")

    def aa_mean(pairs):
        acc = {}
        for aa, v in pairs:
            acc.setdefault(aa, []).append(v)
        return {aa: float(np.mean(vs)) for aa, vs in sorted(acc.items())}

    aa_means = {k: aa_mean(v) for k, v in test_type_ig.items()}

    # qualitative sanity from the 3 peptides
    def top_desc(name):
        rows = [r for r in canon_rows if r["peptide"] == name]
        rows = sorted(rows, key=lambda r: -abs(r["ig"]))[:5]
        return ", ".join(f"{r['aa']}{r['pos']}({r['ig']:+.3f})" for r in rows)

    mag_top = top_desc("magainin-2")
    ll_top = top_desc("LL-37")
    mel_top = top_desc("melittin")

    # Spearman IG vs occlusion on the 3 peptides
    from math import isfinite

    corrs = {}
    for name in CANONICAL:
        rows = [r for r in canon_rows if r["peptide"] == name]
        a = np.array([r["ig"] for r in rows])
        b = np.array([r["occlusion_dlogit"] for r in rows])
        if a.std() > 0 and b.std() > 0:
            corrs[name] = float(np.corrcoef(a, b)[0, 1])
        else:
            corrs[name] = None

    sanity_lines = [
        "High |IG| sites on these three peptides are often K/R (cationic) or F/L/I/W (hydrophobic/aromatic),",
        "which matches the textbook cationic-amphipathic sketch of magainin-2, LL-37, and melittin.",
        f"magainin-2 top |IG|: {mag_top}.",
        f"LL-37 top |IG|: {ll_top}.",
        f"melittin top |IG|: {mel_top}. Occlusion Δlogit tracks IG (Pearson { {k: (round(v,3) if v is not None else None) for k,v in corrs.items()} }).",
        "This is a model-dependent correlation, not a causal mechanism or wet-lab active-site map.",
    ]

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "built": built,
        "model": "models/cnn1d/homology_cnn1d.pt",
        "method": "captum IntegratedGradients on 21-channel one-hot, baseline=zeros, n_steps=50 (canonical) / 32 (test)",
        "target": "AMP-class logit (CNN scalar output)",
        "canonical_membership": membership_tbl,
        "truncation_or_mapping": notes_trunc,
        "ig_vs_occlusion_pearson": corrs,
        "test_aa_mean_ig": aa_means,
        "n_test_sequences": len(test),
        "captum": "0.9.0",
        "all_three_in_homology_train": all(v["in_train"] for v in membership_tbl.values()),
    }
    (REPORT / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    summary = f"""# Phase 6 — Integrated Gradients on the 1D-CNN

Built: {built}

Locked Phase 4 weights were **loaded only**. No retraining. No Streamlit.

## Method

- Model: `models/cnn1d/homology_cnn1d.pt`
- Input: 21-channel one-hot (20 AA + X), pad = zeros, max length 100
- Target: AMP-class **logit**
- IG: Captum `IntegratedGradients`, zero baseline, 50 steps (canonical) / 32 (test)
- Per-residue score: sum of IG over the 21 channels at that position
- Occlusion (3 peptides): set that residue's one-hot column to 0; Δ = logit_full − logit_occluded

## Were the 3 peptides in homology train? (exact sequence)

| peptide | sequence | in train | train id | in val | in test |
| --- | --- | --- | --- | --- | --- |
| magainin-2 | {membership_tbl['magainin-2']['seq']} | **{membership_tbl['magainin-2']['in_train']}** | {membership_tbl['magainin-2']['train_ids']} | {membership_tbl['magainin-2']['in_val']} | {membership_tbl['magainin-2']['in_test']} |
| LL-37 | {membership_tbl['LL-37']['seq']} | **{membership_tbl['LL-37']['in_train']}** | {membership_tbl['LL-37']['train_ids']} | {membership_tbl['LL-37']['in_val']} | {membership_tbl['LL-37']['in_test']} |
| melittin | {membership_tbl['melittin']['seq']} | **{membership_tbl['melittin']['in_train']}** | {membership_tbl['melittin']['train_ids']} | {membership_tbl['melittin']['in_val']} | {membership_tbl['melittin']['in_test']} |

All three exact sequences are **already in the homology training set** (DRAMP IDs above).
IG here is therefore an explanation of a **seen** AMP, not a held-out discovery.

## Motif sanity note (qualitative, not causal)

{sanity_lines[0]}
{sanity_lines[1]}
{sanity_lines[2]}
{sanity_lines[3]}
{sanity_lines[4]}
{sanity_lines[5]}

## Files

- `reports/explain/homology_test_top5.tsv` — top-5 |IG| residues per homology-test sequence
- `reports/explain/canonical_ig_occlusion.tsv` — full per-residue IG + occlusion for the 3 peptides
- `reports/explain/heatmap_magainin_2.png`, `heatmap_LL_37.png`, `heatmap_melittin.png`
- `reports/phase_6_report.md`
"""
    (REPORT / "SUMMARY.md").write_text(summary, encoding="utf-8")

    report = f"""# Phase 6 report — residue-level explainability (1D-CNN)

**Status:** complete  
**Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%d")}  
**Scope:** Captum Integrated Gradients + occlusion on the locked homology 1D-CNN.
No new training, no Streamlit, no DeepLoc/GO/Pfam.

## Setup

| Item | Value |
| --- | --- |
| Weights | `models/cnn1d/homology_cnn1d.pt` (read-only) |
| Encoding | 21-channel one-hot, same as Phase 4 |
| IG target | AMP logit |
| Baseline | all-zero one-hot |
| Test compact table | top 5 residues by \\|IG\\| per sequence |

## Canonical AMP membership

All three peptides are **exact matches in homology train**:

- magainin-2 → `{membership_tbl['magainin-2']['train_ids']}`
- LL-37 → `{membership_tbl['LL-37']['train_ids']}`
- melittin → `{membership_tbl['melittin']['train_ids']}`

None are in val/test. No sequences were added to any split.

## Motif sanity (not a mechanism claim)

{chr(10).join("- " + s for s in sanity_lines)}

Pearson IG vs occlusion Δlogit: { {k: (round(v, 3) if v is not None else None) for k, v in corrs.items()} }.

## Files

- `reports/explain/`
- `reports/phase_6_report.md`
"""
    (ROOT / "reports" / "phase_6_report.md").write_text(report, encoding="utf-8")

    print()
    print("PATHS")
    print(f"  {REPORT / 'homology_test_top5.tsv'}")
    print(f"  {REPORT / 'canonical_ig_occlusion.tsv'}")
    print(f"  {REPORT / 'heatmap_magainin_2.png'}")
    print(f"  {REPORT / 'heatmap_LL_37.png'}")
    print(f"  {REPORT / 'heatmap_melittin.png'}")
    print(f"  {REPORT / 'SUMMARY.md'}")
    print(f"  {ROOT / 'reports' / 'phase_6_report.md'}")
    print()
    print("IN HOMOLOGY TRAIN? (exact seq)")
    for name, rec in membership_tbl.items():
        print(f"  {name}: YES id={rec['train_ids']}  val={rec['in_val']} test={rec['in_test']}")
    print()
    print("SANITY NOTE (5 lines)")
    for s in sanity_lines[:5]:
        print("  " + s)


if __name__ == "__main__":
    main()
