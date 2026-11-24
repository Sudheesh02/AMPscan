"""Shared AMPscan biophysical features and 1D-CNN model definition.

Single source of truth for both ``services/predict_api/scoring.py`` and training
scripts under ``scripts/``, eliminating ``sys.path`` coupling to ``scripts/``.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

AA20 = "ACDEFGHIKLMNPQRSTVWY"
AA_INDEX = {a: i for i, a in enumerate(AA20)}
DIPEPTIDES = [a + b for a in AA20 for b in AA20]

N_CHANNELS = 21  # 20 canonical AAs + X
MAX_LEN = 100

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
PKA_POS = {"K": 10.54, "R": 12.48, "H": 6.04}
PKA_NEG = {"D": 3.90, "E": 4.07, "C": 8.18, "Y": 10.46}
PKA_NTERM = 9.69
PKA_CTERM = 2.34
PH = 7.0
HELIX_DELTA = math.radians(100.0)

PHYSCHEM_NAMES = [
    "length",
    "net_charge_pH7",
    "GRAVY",
    "hydrophobic_moment",
    "aromatic_fraction",
]
PHYSCHEM_NAMES_NO_LEN = [n for n in PHYSCHEM_NAMES if n != "length"]

FEATURE_NAMES = (
    [f"AAC_{a}" for a in AA20]
    + [f"DPC_{ab}" for ab in DIPEPTIDES]
    + PHYSCHEM_NAMES
)
FEATURE_NAMES_NO_LEN = (
    [f"AAC_{a}" for a in AA20]
    + [f"DPC_{ab}" for ab in DIPEPTIDES]
    + PHYSCHEM_NAMES_NO_LEN
)


def net_charge_pH7(seq: str) -> float:
    """Henderson–Hasselbalch net charge at pH 7, including N/C termini."""
    charge = 1.0 / (1.0 + 10.0 ** (PH - PKA_NTERM))
    charge += -1.0 / (1.0 + 10.0 ** (PKA_CTERM - PH))
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
    """Eisenberg hydrophobic moment (v1.1 locked behavior)."""
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


def hydrophobic_moment_v2(seq: str) -> float:
    """Eisenberg hydrophobic moment preserving alpha-helix phase across 'X' residues."""
    sc = ss = 0.0
    n = 0
    for i, a in enumerate(seq):
        h = EISENBERG.get(a)
        if h is None:
            continue
        ang = i * HELIX_DELTA
        sc += h * math.cos(ang)
        ss += h * math.sin(ang)
        n += 1
    return math.sqrt(sc * sc + ss * ss) / n if n else 0.0


def aromatic_fraction(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(1 for a in seq if a in "FWY") / len(seq)


def featurize_one(
    seq: str,
    *,
    include_length: bool = True,
    v2_hmoment: bool = False,
) -> np.ndarray:
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
    hm = hydrophobic_moment_v2(seq) if v2_hmoment else hydrophobic_moment(seq)
    phys_list = [net_charge_pH7(seq), gravy(seq), hm, aromatic_fraction(seq)]
    if include_length:
        phys_list.insert(0, float(L))
    phys = np.array(phys_list, dtype=np.float64)
    return np.concatenate([aac, dpc, phys])


def featurize_many(
    seqs,
    *,
    include_length: bool = True,
    v2_hmoment: bool = False,
) -> np.ndarray:
    dim = len(FEATURE_NAMES) if include_length else len(FEATURE_NAMES_NO_LEN)
    X = np.zeros((len(seqs), dim), dtype=np.float32)
    for i, s in enumerate(seqs):
        X[i] = featurize_one(s, include_length=include_length, v2_hmoment=v2_hmoment)
    return X


def one_hot_idx_batch(idx_batch: torch.Tensor) -> torch.Tensor:
    """(B, L) int64 with -1 pad -> (B, 21, L) float32."""
    mask = (idx_batch >= 0).unsqueeze(1).float()
    safe = idx_batch.clamp(min=0)
    oh = F.one_hot(safe, num_classes=N_CHANNELS).permute(0, 2, 1).float()
    return oh * mask


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
        x = one_hot_idx_batch(idx)
        h = self.conv(x)
        h = h.amax(dim=-1)
        return self.head(h).squeeze(-1)
