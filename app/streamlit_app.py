#!/usr/bin/env python3
"""Offline AMP vs non-AMP demo. Loads locked Phase 2–6 artifacts only."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_baseline import (  # noqa: E402
    AA20,
    AA_INDEX,
    featurize_one,
    gravy,
    net_charge_pH7,
)
from run_cnn1d import CNN1D  # noqa: E402

AA21 = "ACDEFGHIKLMNPQRSTVWYX"
AA21_INDEX = {a: i for i, a in enumerate(AA21)}
AA20X = set("ACDEFGHIKLMNPQRSTVWXY")
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})
MAX_LEN = 100
BATCH_CAP = 50
T_CNN = 1.283257835158267
PLATT_A = 10.084665761569521
PLATT_B = -5.083872738776154

CANONICAL = {
    "GIGKFLHSAKKFGKAFVGEIMNS": (
        "magainin-2",
        "POS_DRAMP_DRAMP02271",
        ROOT / "reports" / "explain" / "heatmap_magainin_2.png",
    ),
    "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES": (
        "LL-37",
        "POS_DRAMP_DRAMP03571",
        ROOT / "reports" / "explain" / "heatmap_LL_37.png",
    ),
    "GIGAVLKVLTTGLPALISWIKRKRQQ": (
        "melittin",
        "POS_DRAMP_DRAMP03002",
        ROOT / "reports" / "explain" / "heatmap_melittin.png",
    ),
}


def sigmoid(z):
    z = np.clip(z, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-z))


def preprocess(raw: str):
    s = raw.replace(" ", "").replace("\t", "").replace("*", "").upper().translate(MAP)
    if not (5 <= len(s) <= 100):
        return None, f"length {len(s)} is outside 5–100"
    bad = sorted({c for c in s if c not in AA20X})
    if bad:
        return None, f"non-AA characters after B/Z/U/O/J→X mapping: {''.join(bad)}"
    return s, None


def parse_fasta_text(text: str):
    recs = []
    hdr, buf = None, []
    for line in text.splitlines():
        line = line.rstrip("\n")
        if line.startswith(">"):
            if hdr is not None:
                recs.append((hdr.split()[0], "".join(buf)))
            hdr, buf = line[1:].strip() or f"seq{len(recs)+1}", []
        else:
            buf.append(line.strip())
    if hdr is not None:
        recs.append((hdr.split()[0], "".join(buf)))
    elif text.strip() and not text.lstrip().startswith(">"):
        recs.append(("pasted", text.strip()))
    return recs


class CNNOneHot(nn.Module):
    def __init__(self, inner: CNN1D):
        super().__init__()
        self.conv = inner.conv
        self.head = inner.head

    def forward(self, x):
        h = self.conv(x)
        h = h.amax(dim=-1)
        return self.head(h).squeeze(-1)


def one_hot(seq: str) -> np.ndarray:
    x = np.zeros((21, MAX_LEN), dtype=np.float32)
    for j, a in enumerate(seq[:MAX_LEN]):
        i = AA21_INDEX.get(a)
        if i is not None:
            x[i, j] = 1.0
    return x


@st.cache_resource
def load_artifacts():
    rf = joblib.load(ROOT / "models" / "baseline" / "homology_rf.joblib")
    ckpt = torch.load(
        ROOT / "models" / "cnn1d" / "homology_cnn1d.pt",
        map_location="cpu",
        weights_only=False,
    )
    inner = CNN1D(dropout=float(ckpt.get("dropout", 0.2)))
    inner.load_state_dict(ckpt["state_dict"])
    inner.eval()
    for p in inner.parameters():
        p.requires_grad = False
    cnn = CNNOneHot(inner)
    cnn.eval()
    return rf, cnn


def rf_calibrated(rf, seq: str) -> float:
    x = featurize_one(seq).reshape(1, -1)
    p_raw = float(rf.predict_proba(x)[0, 1])
    return float(sigmoid(PLATT_A * p_raw + PLATT_B))


@torch.no_grad()
def cnn_calibrated(cnn, seq: str) -> tuple[float, float]:
    x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
    logit = float(cnn(x).cpu())
    return logit, float(sigmoid(logit / T_CNN))


def ig_vector(cnn, seq: str) -> np.ndarray:
    from captum.attr import IntegratedGradients

    x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
    x.requires_grad_(True)
    ig = IntegratedGradients(cnn)
    attr = ig.attribute(x, baselines=torch.zeros_like(x), n_steps=32)
    return attr.squeeze(0).sum(dim=0).detach().cpu().numpy()[: len(seq)]


def ig_figure(seq: str, ig: np.ndarray, title: str):
    fig, ax = plt.subplots(figsize=(max(7.0, 0.28 * len(seq)), 2.4))
    vmax = max(float(np.max(np.abs(ig))), 1e-8)
    im = ax.imshow(ig[np.newaxis, :], cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_yticks([])
    ax.set_xticks(range(len(seq)))
    ax.set_xticklabels(list(seq), fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    return fig


def page_predict():
    st.title("AMP vs non-AMP")
    st.caption(
        "Offline demo. Primary score = Platt-calibrated Random Forest. "
        "Secondary = 1D-CNN with temperature T = 1.283. Homology-split models only."
    )
    rf, cnn = load_artifacts()

    left, right = st.columns(2)
    with left:
        pasted = st.text_area(
            "Paste one sequence (or a small FASTA)",
            height=140,
            placeholder="GIGKFLHSAKKFGKAFVGEIMNS",
        )
    with right:
        up = st.file_uploader("Or upload FASTA (max 50 sequences)", type=["fa", "fasta", "txt"])

    raw_text = ""
    if up is not None:
        raw_text = up.getvalue().decode("utf-8", errors="replace")
    elif pasted.strip():
        raw_text = pasted

    if st.button("Predict", type="primary") or (raw_text.strip() and up is not None):
        recs = parse_fasta_text(raw_text)
        if not recs:
            st.error("No sequence found. Paste residues or a FASTA header + sequence.")
            return
        if len(recs) > BATCH_CAP:
            st.warning(f"Capped at {BATCH_CAP} sequences (got {len(recs)}).")
            recs = recs[:BATCH_CAP]

        rows = []
        for sid, raw in recs:
            seq, err = preprocess(raw)
            if err:
                rows.append({"id": sid, "ok": False, "error": err, "raw": raw})
            else:
                p_rf = rf_calibrated(rf, seq)
                logit, p_cnn = cnn_calibrated(cnn, seq)
                rows.append(
                    {
                        "id": sid,
                        "ok": True,
                        "seq": seq,
                        "p_rf": p_rf,
                        "p_cnn": p_cnn,
                        "logit_cnn": logit,
                        "label": "AMP" if p_rf >= 0.5 else "non-AMP",
                        "length": len(seq),
                        "net_charge": net_charge_pH7(seq),
                        "gravy": gravy(seq),
                    }
                )

        ok_rows = [r for r in rows if r["ok"]]
        bad_rows = [r for r in rows if not r["ok"]]
        if bad_rows:
            for r in bad_rows:
                st.error(f"{r['id']}: {r['error']}")
        if not ok_rows:
            return

        table = [
            {
                "id": r["id"],
                "label (RF, 0.5)": r["label"],
                "RF P(AMP) calibrated": round(r["p_rf"], 4),
                "CNN P(AMP) T=1.283": round(r["p_cnn"], 4),
                "length": r["length"],
                "net charge pH7": round(r["net_charge"], 3),
                "GRAVY": round(r["gravy"], 3),
            }
            for r in ok_rows
        ]
        st.subheader("Predictions")
        st.dataframe(table, use_container_width=True)

        st.subheader("Explainability (CNN Integrated Gradients)")
        for r in ok_rows:
            st.markdown(f"**{r['id']}**  `{r['seq']}`")
            canon = CANONICAL.get(r["seq"])
            if canon:
                name, did, png = canon
                st.warning(
                    f"These three examples are in the TRAINING set. "
                    f"{name} = {did} (homology train)."
                )
                if png.is_file():
                    st.image(str(png), caption=f"Precomputed Phase-6 heatmap: {name}")
            ig = ig_vector(cnn, r["seq"])
            fig = ig_figure(
                r["seq"],
                ig,
                f"CNN IG  {r['id']}  P_rf={r['p_rf']:.3f}  P_cnn={r['p_cnn']:.3f}",
            )
            st.pyplot(fig)
            plt.close(fig)


def page_metrics():
    st.title("Locked evaluation (homology is the honest number)")
    st.markdown(
        """
Homology split = MMseqs2 30% identity, whole clusters, 70/15/15, seed 42.
Random split = same peptides, clusters ignored — **leaky**, shown only as a control.
        """
    )
    st.subheader("Homology test")
    st.table(
        [
            {"model": "RF (Phase 2)", "acc": 0.8734, "macro-F1": 0.8734, "ROC-AUC": 0.9515, "PR-AUC": 0.9542},
            {"model": "ESM-2 35M linear (Phase 3)", "acc": 0.8622, "macro-F1": 0.8622, "ROC-AUC": 0.9450, "PR-AUC": 0.9424},
            {"model": "1D-CNN (Phase 4)", "acc": 0.8650, "macro-F1": 0.8648, "ROC-AUC": 0.9424, "PR-AUC": 0.9465},
            {"model": "ESM-2 150M linear (Phase 9)", "acc": 0.8762, "macro-F1": 0.8761, "ROC-AUC": 0.9521, "PR-AUC": 0.9516},
        ]
    )
    st.caption(
        "Phase 9 ESM-2 150M linear homology-test ROC-AUC 0.9521 is a tie with RF 0.9515 "
        "(val 0.9372 so LoRA was not run). Source: reports/phase_9_report.md."
    )
    st.subheader("Random-split test (leakage control)")
    st.table(
        [
            {"model": "RF", "acc": 0.9231, "ROC-AUC": 0.9791},
            {"model": "ESM-2 35M linear", "acc": 0.9009, "ROC-AUC": 0.9657},
            {"model": "1D-CNN", "acc": 0.9203, "ROC-AUC": 0.9749},
        ]
    )
    st.caption("Numbers copied from locked reports/baseline, reports/esm2_35M, reports/cnn1d, reports/calibration, reports/phase_9_report.md.")
    st.subheader("Calibration ECE (15 bins) on homology test")
    st.table(
        [
            {"model": "RF (Platt)", "uncal ECE": 0.0776, "cal ECE": 0.0235, "ROC-AUC": 0.9515},
            {"model": "ESM-2 linear (T)", "uncal ECE": 0.0376, "cal ECE": 0.0185, "ROC-AUC": 0.9450},
            {"model": "1D-CNN (T=1.283)", "uncal ECE": 0.0624, "cal ECE": 0.0403, "ROC-AUC": 0.9424},
        ]
    )
    st.subheader("Limitations")
    st.markdown(
        """
This app is a **sequence-pattern classifier** trained on DRAMP General AMPs vs AMPlify
non-AMPs, length 5–100. The honest number is the **homology-split** test (RF ROC-AUC 0.95).
The random split looks better because close homologs leak across folds. Calibration
changes confidence, not ranking. IG highlights residues the **CNN** uses; it is not a
wet-lab active site and magainin-2 / LL-37 / melittin are **in the training set**.
The model does not claim de novo AMP discovery, mechanism, or MIC.
        """
    )


def main():
    st.set_page_config(page_title="AMP vs non-AMP", layout="wide")
    page = st.sidebar.radio("Page", ["Predict", "Metrics"])
    st.sidebar.markdown(
        "Offline. No APIs. No training. "
        "Models: `models/baseline/homology_rf.joblib`, "
        "`models/cnn1d/homology_cnn1d.pt`, "
        "Platt (a=10.085, b=−5.084), CNN T=1.283."
    )
    if page == "Predict":
        page_predict()
    else:
        page_metrics()


if __name__ == "__main__":
    main()
