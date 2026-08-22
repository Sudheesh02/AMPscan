#!/usr/bin/env python3
"""FastAPI inference for locked AMPscan models. No training. No internet."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from locked_metrics import (
    CALIBRATION_ECE,
    HOMOLOGY_TEST,
    PLAIN_ENGLISH,
    RANDOM_TEST,
    SOURCES,
)
from scoring import (
    CANONICAL,
    VERSION,
    aac_preview,
    get_artifacts,
    preprocess,
)

app = FastAPI(
    title="AMPscan API",
    version=VERSION,
    description="Offline AMP vs non-AMP scores from locked homology-split models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SequenceIn(BaseModel):
    sequence: str = Field(..., description="Raw letters or a small FASTA record")


@app.on_event("startup")
def _load() -> None:
    get_artifacts()


@app.get("/health")
def health():
    art = get_artifacts()
    return {
        "ok": True,
        "version": VERSION,
        "device": art.device,
        "models_loaded": {
            "rf": art.rf_path,
            "cnn": art.cnn_path,
            "platt_a": art.platt_a,
            "platt_b": art.platt_b,
            "cnn_T": art.t_cnn,
        },
        "offline": True,
    }


@app.get("/metrics")
def metrics():
    return {
        "homology_test": HOMOLOGY_TEST,
        "random_test": RANDOM_TEST,
        "calibration_ece_homology_test": CALIBRATION_ECE,
        "headline": {
            "quote": 0.9515,
            "model": "Random Forest, homology test ROC-AUC",
            "do_not_quote": 0.9791,
            "do_not_quote_note": "random-split RF ROC-AUC (leakage control)",
        },
        "plain_english": PLAIN_ENGLISH,
        "sources": SOURCES,
        "recomputed": False,
    }


@app.post("/predict")
def predict(body: SequenceIn):
    seq, errors = preprocess(body.sequence)
    if seq is None:
        return {
            "sequence": strip_display(body.sequence),
            "length": len(strip_display(body.sequence)),
            "valid": False,
            "errors": errors,
            "primary": None,
            "secondary": None,
            "features_preview": None,
        }
    art = get_artifacts()
    _p_raw, p_rf = art.rf_calibrated(seq)
    _logit, p_cnn = art.cnn_calibrated(seq)
    return {
        "sequence": seq,
        "length": len(seq),
        "valid": True,
        "errors": [],
        "primary": {
            "model": "rf_homology_platt",
            "p_amp": round(p_rf, 6),
            "label": "AMP" if p_rf >= 0.5 else "non-AMP",
            "calibrated": True,
            "threshold": 0.5,
        },
        "secondary": {
            "model": "cnn1d_T",
            "p_amp": round(p_cnn, 6),
            "temperature": art.t_cnn,
            "calibrated": True,
        },
        "features_preview": aac_preview(seq),
    }


@app.post("/explain")
def explain(body: SequenceIn):
    seq, errors = preprocess(body.sequence)
    if seq is None:
        return {
            "method": "integrated_gradients_cnn",
            "valid": False,
            "errors": errors,
            "residues": [],
            "train_set_warning": False,
            "matched_train_id": None,
            "canonical_name": None,
            "note": "Sequence failed validation; no attribution.",
        }
    art = get_artifacts()
    ig = art.ig_vector(seq)
    canon = CANONICAL.get(seq)
    return {
        "method": "integrated_gradients_cnn",
        "valid": True,
        "errors": [],
        "residues": [
            {"pos": i + 1, "aa": aa, "ig": round(float(ig[i]), 6)}
            for i, aa in enumerate(seq)
        ],
        "train_set_warning": bool(canon),
        "matched_train_id": canon[1] if canon else None,
        "canonical_name": canon[0] if canon else None,
        "note": (
            "Explanations are model-dependent; canonical demos may be training sequences. "
            "IG is the CNN AMP-logit attribution, not a wet-lab mechanism."
        ),
    }


def strip_display(raw: str) -> str:
    from scoring import strip_fasta, MAP

    return strip_fasta(raw).upper().translate(MAP)
