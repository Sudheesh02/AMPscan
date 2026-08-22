"""Locked AMPscan scoring — same paths and formulas as app/streamlit_app.py."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_baseline import (  # noqa: E402
    AA20,
    aromatic_fraction,
    featurize_one,
    gravy,
    hydrophobic_moment,
    net_charge_pH7,
)
from run_cnn1d import CNN1D  # noqa: E402

AA21 = "ACDEFGHIKLMNPQRSTVWYX"
AA21_INDEX = {a: i for i, a in enumerate(AA21)}
AA20X = set("ACDEFGHIKLMNPQRSTVWXY")
MAP = str.maketrans({"B": "X", "Z": "X", "U": "X", "O": "X", "J": "X"})
MAX_LEN = 100
VERSION = "ampscan-api-1.0"

CANONICAL = {
    "GIGKFLHSAKKFGKAFVGEIMNS": ("magainin-2", "POS_DRAMP_DRAMP02271"),
    "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES": ("LL-37", "POS_DRAMP_DRAMP03571"),
    "GIGAVLKVLTTGLPALISWIKRKRQQ": ("melittin", "POS_DRAMP_DRAMP03002"),
}


class CNNOneHot(nn.Module):
    def __init__(self, inner: CNN1D):
        super().__init__()
        self.conv = inner.conv
        self.head = inner.head

    def forward(self, x):
        h = self.conv(x)
        h = h.amax(dim=-1)
        return self.head(h).squeeze(-1)


def sigmoid(z: float) -> float:
    z = float(np.clip(z, -60.0, 60.0))
    return 1.0 / (1.0 + math.exp(-z))


def strip_fasta(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text.lstrip().startswith(">"):
        lines = []
        for line in text.splitlines():
            if line.startswith(">"):
                continue
            lines.append(line.strip())
        text = "".join(lines)
    return text.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "").replace("*", "")


def preprocess(raw: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    s = strip_fasta(raw).upper().translate(MAP)
    if not s:
        return None, ["no sequence found (paste residues or FASTA)"]
    if not (5 <= len(s) <= 100):
        errors.append(f"length {len(s)} is outside 5–100")
    bad = sorted({c for c in s if c not in AA20X})
    if bad:
        errors.append(f"non-AA characters after B/Z/U/O/J→X mapping: {''.join(bad)}")
    if errors:
        return None, errors
    return s, []


def one_hot(seq: str) -> np.ndarray:
    x = np.zeros((21, MAX_LEN), dtype=np.float32)
    for j, a in enumerate(seq[:MAX_LEN]):
        i = AA21_INDEX.get(a)
        if i is not None:
            x[i, j] = 1.0
    return x


def aac_preview(seq: str) -> dict:
    counts = {a: 0 for a in AA20}
    for a in seq:
        if a in counts:
            counts[a] += 1
    L = max(len(seq), 1)
    freqs = {a: round(counts[a] / L, 4) for a in AA20 if counts[a]}
    top = sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    return {
        "length": len(seq),
        "net_charge_pH7": round(float(net_charge_pH7(seq)), 4),
        "GRAVY": round(float(gravy(seq)), 4),
        "hydrophobic_moment": round(float(hydrophobic_moment(seq)), 4),
        "aromatic_fraction": round(float(aromatic_fraction(seq)), 4),
        "aac_nonzero": dict(top),
    }


class Artifacts:
    def __init__(self) -> None:
        platt_path = ROOT / "models" / "calibration" / "homology_rf_platt.json"
        t_path = ROOT / "models" / "calibration" / "homology_cnn_temperature.json"
        platt = json.loads(platt_path.read_text(encoding="utf-8"))
        tjson = json.loads(t_path.read_text(encoding="utf-8"))
        self.platt_a = float(platt["a"])
        self.platt_b = float(platt["b"])
        self.t_cnn = float(tjson["T"])
        self.rf = joblib.load(ROOT / "models" / "baseline" / "homology_rf.joblib")
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
        self.cnn = CNNOneHot(inner)
        self.cnn.eval()
        self.device = "cpu"
        self.rf_path = "models/baseline/homology_rf.joblib"
        self.cnn_path = "models/cnn1d/homology_cnn1d.pt"

    def rf_calibrated(self, seq: str) -> tuple[float, float]:
        x = featurize_one(seq).reshape(1, -1)
        p_raw = float(self.rf.predict_proba(x)[0, 1])
        p_cal = float(sigmoid(self.platt_a * p_raw + self.platt_b))
        return p_raw, p_cal

    @torch.no_grad()
    def cnn_calibrated(self, seq: str) -> tuple[float, float]:
        x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
        logit = float(self.cnn(x).cpu())
        return logit, float(sigmoid(logit / self.t_cnn))

    def ig_vector(self, seq: str) -> np.ndarray:
        from captum.attr import IntegratedGradients

        x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
        x.requires_grad_(True)
        ig = IntegratedGradients(self.cnn)
        attr = ig.attribute(x, baselines=torch.zeros_like(x), n_steps=32)
        return attr.squeeze(0).sum(dim=0).detach().cpu().numpy()[: len(seq)]


_ART: Artifacts | None = None


def get_artifacts() -> Artifacts:
    global _ART
    if _ART is None:
        _ART = Artifacts()
    return _ART
