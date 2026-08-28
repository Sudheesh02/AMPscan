"""Locked AMPscan scoring — same paths and formulas as app/streamlit_app.py."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
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
    featurize_many,
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
VERSION = "ampscan-api-1.1"

BATCH_CAP = 500
SCAN_MAX_LEN = 5000
SCAN_MAX_WINDOWS = 2000
NEAREST_LEN_DELTA = 2
CNN_BATCH = 256
TRAIN_FASTA = ROOT / "data" / "splits" / "train.fasta"

CANONICAL = {
    "GIGKFLHSAKKFGKAFVGEIMNS": ("magainin-2", "POS_DRAMP_DRAMP02271"),
    "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES": ("LL-37", "POS_DRAMP_DRAMP03571"),
    "GIGAVLKVLTTGLPALISWIKRKRQQ": ("melittin", "POS_DRAMP_DRAMP03002"),
}

NEAREST_NOTE = (
    f"Ungapped identity to the closest homology-train peptide with |Δlength| ≤ {NEAREST_LEN_DELTA}. "
    "This is not an MMseqs 30% cluster wall."
)
EXACT_TRAIN_NOTE = (
    "Exact match to a homology-train peptide. Score is train-set recall, not a held-out test case."
)
SCAN_NOTE = "Window scores from the locked RF. This is not a protein-level AMP call."


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


def sigmoid_np(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-z))


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


def strip_fasta_one(raw: str) -> str:
    """First FASTA record only (scan must not concatenate multi-FASTA)."""
    text = (raw or "").strip()
    if not text:
        return ""
    if text.lstrip().startswith(">"):
        buf: list[str] = []
        seen_header = False
        for line in text.splitlines():
            if line.startswith(">"):
                if seen_header:
                    break
                seen_header = True
                continue
            buf.append(line.strip())
        text = "".join(buf)
    return text.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "").replace("*", "")


def normalize_aa(raw: str, *, first_record: bool = False) -> tuple[str, list[str]]:
    """Uppercase + B/Z/U/O/J→X. Does not enforce length 5–100."""
    s = (strip_fasta_one(raw) if first_record else strip_fasta(raw)).upper().translate(MAP)
    errors: list[str] = []
    if not s:
        return "", ["no sequence found (paste residues or FASTA)"]
    bad = sorted({c for c in s if c not in AA20X})
    if bad:
        errors.append(f"non-AA characters after B/Z/U/O/J→X mapping: {''.join(bad)}")
    return s, errors


def preprocess(raw: str) -> tuple[str | None, list[str]]:
    s, errors = normalize_aa(raw, first_record=False)
    if not s:
        return None, errors
    if not (5 <= len(s) <= 100):
        if len(s) > 100:
            errors.append(
                f"length {len(s)} is outside 5–100; use POST /scan for windowed locked-RF "
                "scores (not a protein-level AMP call)"
            )
        else:
            errors.append(f"length {len(s)} is outside 5–100")
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


def sliding_windows(seq: str, window: int, step: int) -> list[tuple[int, int, str]]:
    """1-based inclusive coordinates, same as scripts/scan_protein.py."""
    if len(seq) < window:
        return []
    out: list[tuple[int, int, str]] = []
    for start in range(0, len(seq) - window + 1, step):
        out.append((start + 1, start + window, seq[start : start + window]))
    return out


def nearest_payload(
    *,
    train_id: str | None,
    identity: float | None,
    train_length: int | None,
    train_label: str | None,
    exact_match: bool,
    note: str,
) -> dict:
    return {
        "train_id": train_id,
        "identity": None if identity is None else round(float(identity), 4),
        "train_length": train_length,
        "train_label": train_label,
        "exact_match": exact_match,
        "note": note,
    }


@dataclass
class _LenBucket:
    ids: list[str]
    labels: list[str]
    arr: np.ndarray  # (n, L) uint8 ascii


class TrainIndex:
    """Ungapped identity vs homology train. Not an MMseqs cluster wall."""

    def __init__(self, fasta: Path = TRAIN_FASTA) -> None:
        self.n = 0
        self.path = str(fasta.relative_to(ROOT)) if fasta.exists() else str(fasta)
        self.exact: dict[str, tuple[str, str, int]] = {}
        self.buckets: dict[int, _LenBucket] = {}
        if fasta.is_file():
            self._load(fasta)

    def _load(self, fasta: Path) -> None:
        by_len: dict[int, list[tuple[str, str, str]]] = {}
        hdr, buf = None, []

        def flush() -> None:
            if hdr is None:
                return
            tid = hdr.split()[0]
            raw = "".join(buf).upper().translate(MAP)
            if not raw or any(c not in AA20X for c in raw):
                return
            lab = "AMP" if "LABEL=1" in hdr else "non-AMP"
            if raw not in self.exact:
                self.exact[raw] = (tid, lab, len(raw))
            by_len.setdefault(len(raw), []).append((tid, lab, raw))

        with fasta.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith(">"):
                    flush()
                    hdr, buf = line[1:], []
                else:
                    buf.append(line.strip())
            flush()

        for ell, rows in by_len.items():
            ids = [r[0] for r in rows]
            labels = [r[1] for r in rows]
            arr = np.frombuffer("".join(r[2] for r in rows).encode("ascii"), dtype=np.uint8)
            arr = arr.reshape(len(rows), ell)
            self.buckets[ell] = _LenBucket(ids=ids, labels=labels, arr=arr)
        self.n = sum(b.arr.shape[0] for b in self.buckets.values())

    def nearest(self, seq: str, delta: int = NEAREST_LEN_DELTA) -> dict:
        if not self.n:
            return nearest_payload(
                train_id=None,
                identity=None,
                train_length=None,
                train_label=None,
                exact_match=False,
                note="Train index unavailable.",
            )
        hit = self.exact.get(seq)
        if hit is not None:
            tid, lab, tlen = hit
            return nearest_payload(
                train_id=tid,
                identity=1.0,
                train_length=tlen,
                train_label=lab,
                exact_match=True,
                note=EXACT_TRAIN_NOTE,
            )

        q = np.frombuffer(seq.encode("ascii"), dtype=np.uint8)
        L = len(seq)
        best_id = -1.0
        best_tid: str | None = None
        best_lab: str | None = None
        best_tlen: int | None = None

        def consider(ell: int) -> None:
            nonlocal best_id, best_tid, best_lab, best_tlen
            bucket = self.buckets.get(ell)
            if bucket is None or bucket.arr.size == 0:
                return
            arr = bucket.arr
            if ell == L:
                matches = (arr == q).sum(axis=1)
                ident = matches / float(max(L, 1))
            elif ell > L:
                matches = np.zeros(arr.shape[0], dtype=np.int32)
                for off in range(ell - L + 1):
                    np.maximum(matches, (arr[:, off : off + L] == q).sum(axis=1), out=matches)
                ident = matches / float(ell)
            else:
                matches = np.zeros(arr.shape[0], dtype=np.int32)
                for off in range(L - ell + 1):
                    np.maximum(matches, (arr == q[off : off + ell]).sum(axis=1), out=matches)
                ident = matches / float(L)
            j = int(np.argmax(ident))
            v = float(ident[j])
            if v > best_id:
                best_id = v
                best_tid = bucket.ids[j]
                best_lab = bucket.labels[j]
                best_tlen = ell

        consider(L)
        for d in range(1, delta + 1):
            consider(L - d)
            consider(L + d)

        if best_tid is None:
            return nearest_payload(
                train_id=None,
                identity=None,
                train_length=None,
                train_label=None,
                exact_match=False,
                note="No train peptide in the length window.",
            )
        return nearest_payload(
            train_id=best_tid,
            identity=best_id,
            train_length=best_tlen,
            train_label=best_lab,
            exact_match=False,
            note=NEAREST_NOTE,
        )


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

    def rf_calibrated_many(self, seqs: list[str]) -> np.ndarray:
        if not seqs:
            return np.zeros((0,), dtype=np.float64)
        X = featurize_many(seqs)
        p_raw = self.rf.predict_proba(X)[:, 1]
        return sigmoid_np(self.platt_a * p_raw + self.platt_b)

    @torch.no_grad()
    def cnn_calibrated(self, seq: str) -> tuple[float, float]:
        x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
        logit = float(self.cnn(x).cpu())
        return logit, float(sigmoid(logit / self.t_cnn))

    @torch.no_grad()
    def cnn_calibrated_many(self, seqs: list[str], batch: int = CNN_BATCH) -> np.ndarray:
        if not seqs:
            return np.zeros((0,), dtype=np.float64)
        out = np.empty(len(seqs), dtype=np.float64)
        self.cnn.eval()
        for i in range(0, len(seqs), batch):
            chunk = seqs[i : i + batch]
            x = torch.from_numpy(np.stack([one_hot(s) for s in chunk]))
            logit = self.cnn(x).cpu().numpy().reshape(-1)
            out[i : i + len(chunk)] = sigmoid_np(logit / self.t_cnn)
        return out

    def ig_vector(self, seq: str) -> np.ndarray:
        from captum.attr import IntegratedGradients

        x = torch.from_numpy(one_hot(seq)).unsqueeze(0)
        x.requires_grad_(True)
        ig = IntegratedGradients(self.cnn)
        attr = ig.attribute(x, baselines=torch.zeros_like(x), n_steps=32)
        return attr.squeeze(0).sum(dim=0).detach().cpu().numpy()[: len(seq)]


def predict_result(seq: str, p_rf: float, p_cnn: float, t_cnn: float, nearest: dict) -> dict:
    return {
        "sequence": seq,
        "length": len(seq),
        "valid": True,
        "errors": [],
        "primary": {
            "model": "rf_homology_platt",
            "p_amp": round(float(p_rf), 6),
            "label": "AMP" if p_rf >= 0.5 else "non-AMP",
            "calibrated": True,
            "threshold": 0.5,
        },
        "secondary": {
            "model": "cnn1d_T",
            "p_amp": round(float(p_cnn), 6),
            "temperature": t_cnn,
            "calibrated": True,
        },
        "features_preview": aac_preview(seq),
        "nearest_train": nearest,
    }


def invalid_result(display_seq: str, errors: list[str]) -> dict:
    return {
        "sequence": display_seq,
        "length": len(display_seq),
        "valid": False,
        "errors": errors,
        "primary": None,
        "secondary": None,
        "features_preview": None,
        "nearest_train": None,
    }


def scan_protein(seq: str, window: int, step: int, art: Artifacts) -> dict:
    wins = sliding_windows(seq, window, step)
    p = art.rf_calibrated_many([w[2] for w in wins]) if wins else np.zeros((0,), dtype=np.float64)
    windows = [
        {
            "start": start,
            "end": end,
            "seq": sub,
            "p_amp": round(float(pi), 6),
            "label": "AMP" if float(pi) >= 0.5 else "non-AMP",
        }
        for (start, end, sub), pi in zip(wins, p)
    ]
    if windows:
        i_max = int(np.argmax(p))
        summary = {
            "max_p_amp": windows[i_max]["p_amp"],
            "max_start": windows[i_max]["start"],
            "max_end": windows[i_max]["end"],
            "n_windows_ge_0.5": int(np.sum(p >= 0.5)),
            "n_windows_ge_0.9": int(np.sum(p >= 0.9)),
        }
    else:
        summary = {
            "max_p_amp": None,
            "max_start": None,
            "max_end": None,
            "n_windows_ge_0.5": 0,
            "n_windows_ge_0.9": 0,
        }
    return {
        "valid": True,
        "errors": [],
        "sequence_length": len(seq),
        "window": window,
        "step": step,
        "n_windows": len(windows),
        "protein_level_call": False,
        "note": SCAN_NOTE,
        "windows": windows,
        "summary": summary,
    }


_ART: Artifacts | None = None
_TRAIN: TrainIndex | None = None


def get_artifacts() -> Artifacts:
    global _ART
    if _ART is None:
        _ART = Artifacts()
    return _ART


def get_train_index() -> TrainIndex:
    global _TRAIN
    if _TRAIN is None:
        _TRAIN = TrainIndex()
    return _TRAIN
