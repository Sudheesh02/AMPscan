#!/usr/bin/env python3
"""FastAPI inference for locked AMPscan models. No training. No internet."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from locked_metrics import (
    CALIBRATION_ECE,
    COHORT_2B,
    HOMOLOGY_TEST,
    PLAIN_ENGLISH,
    RANDOM_TEST,
    SOURCES,
)
from scoring import (
    BATCH_CAP,
    CANONICAL,
    MAP,
    NEAREST_LEN_DELTA,
    SCAN_MAX_LEN,
    SCAN_MAX_WINDOWS,
    SCAN_NOTE,
    VERSION,
    get_artifacts,
    get_train_index,
    invalid_result,
    normalize_aa,
    predict_result,
    preprocess,
    scan_protein,
    sliding_windows,
    strip_fasta,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_artifacts()
    get_train_index()
    yield


app = FastAPI(
    title="AMPscan API",
    version=VERSION,
    description=(
        "AMP vs non-AMP scores from locked homology-split models. "
        "Primary: Random Forest + Platt. Secondary: 1D-CNN + temperature. "
        "Windowed /scan is not a protein-level AMP call. "
        "v1 headline remains homology-test RF ROC-AUC 0.9515."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://ampscan.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SequenceIn(BaseModel):
    sequence: str = Field(..., description="Raw letters or a small FASTA record")

    model_config = {
        "json_schema_extra": {"examples": [{"sequence": "GIGKFLHSAKKFGKAFVGEIMNS"}]}
    }


class BatchItemIn(BaseModel):
    id: str | None = Field(None, description="Caller id; auto-assigned if omitted")
    sequence: str


class BatchIn(BaseModel):
    sequences: list[BatchItemIn] = Field(
        ...,
        min_length=1,
        max_length=BATCH_CAP,
        description=f"Peptides to score, cap {BATCH_CAP}",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sequences": [
                        {"id": "magainin-2", "sequence": "GIGKFLHSAKKFGKAFVGEIMNS"},
                        {"id": "ll37", "sequence": "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES"},
                    ]
                }
            ]
        }
    }


class ScanIn(BaseModel):
    sequence: str = Field(..., description="Protein or long peptide; first FASTA record only")
    window: int = Field(25, ge=5, le=100, description="Window length (RF input range 5–100)")
    step: int = Field(1, ge=1, le=100, description="Slide step in residues")

    model_config = {
        "json_schema_extra": {
            "examples": [{"sequence": "MKTQRDGHSLGRWSLVLLLLGLVMPLAIIA", "window": 25, "step": 1}]
        }
    }


def strip_display(raw: str) -> str:
    return strip_fasta(raw).upper().translate(MAP)


def _score_valid_many(seqs: list[str]) -> list[dict]:
    art = get_artifacts()
    index = get_train_index()
    p_rf = art.rf_calibrated_many(seqs)
    p_cnn = art.cnn_calibrated_many(seqs)
    out = []
    for s, a, b in zip(seqs, p_rf, p_cnn):
        out.append(predict_result(s, float(a), float(b), art.t_cnn, index.nearest(s)))
    return out


@app.get("/health")
def health():
    art = get_artifacts()
    index = get_train_index()
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
        "train_index": {"n": index.n, "path": index.path, "length_delta": NEAREST_LEN_DELTA},
        "limits": {
            "batch_cap": BATCH_CAP,
            "scan_max_len": SCAN_MAX_LEN,
            "scan_max_windows": SCAN_MAX_WINDOWS,
            "peptide_len": [5, 100],
        },
        "endpoints": ["/health", "/metrics", "/predict", "/predict-batch", "/scan", "/explain"],
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
        "cohort_2b": COHORT_2B,
        "plain_english": PLAIN_ENGLISH,
        "sources": SOURCES,
        "recomputed": False,
    }


@app.post("/predict")
def predict(body: SequenceIn):
    seq, errors = preprocess(body.sequence)
    if seq is None:
        return invalid_result(strip_display(body.sequence), errors)
    scored = _score_valid_many([seq])[0]
    return scored


@app.post("/predict-batch")
def predict_batch(body: BatchIn):
    """Batched locked RF+CNN. Same Platt / T as POST /predict. Cap 500."""
    prepared: list[tuple[int, str, str | None, list[str]]] = []
    valid_seqs: list[str] = []
    valid_idx: list[int] = []
    for i, item in enumerate(body.sequences):
        item_id = item.id if item.id else f"item_{i + 1}"
        seq, errors = preprocess(item.sequence)
        if seq is None:
            prepared.append((i, item_id, None, errors))
        else:
            prepared.append((i, item_id, seq, []))
            valid_seqs.append(seq)
            valid_idx.append(i)

    scored_by_i: dict[int, dict] = {}
    if valid_seqs:
        for i, payload in zip(valid_idx, _score_valid_many(valid_seqs)):
            scored_by_i[i] = payload

    results = []
    n_valid = 0
    for i, item_id, seq, errors in prepared:
        if seq is None:
            row = invalid_result(strip_display(body.sequences[i].sequence), errors)
        else:
            row = dict(scored_by_i[i])
            n_valid += 1
        row["id"] = item_id
        results.append(row)

    return {
        "version": VERSION,
        "n": len(results),
        "n_valid": n_valid,
        "n_invalid": len(results) - n_valid,
        "results": results,
    }


@app.post("/scan")
def scan(body: ScanIn):
    """Sliding locked-RF windows. Not a protein-level AMP call."""
    s, errors = normalize_aa(body.sequence, first_record=True)
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "sequence_length": len(s),
            "window": body.window,
            "step": body.step,
            "n_windows": 0,
            "protein_level_call": False,
            "note": SCAN_NOTE,
            "windows": [],
            "summary": None,
        }
    extra: list[str] = []
    if len(s) > SCAN_MAX_LEN:
        extra.append(f"length {len(s)} exceeds scan cap {SCAN_MAX_LEN} residues")
    if len(s) < body.window:
        extra.append(f"length {len(s)} is shorter than window {body.window}")
    n_win = 0 if len(s) < body.window else len(sliding_windows(s, body.window, body.step))
    if n_win > SCAN_MAX_WINDOWS:
        extra.append(
            f"this protein/window/step would produce {n_win} windows "
            f"(cap {SCAN_MAX_WINDOWS}); increase step"
        )
    if extra:
        return {
            "valid": False,
            "errors": extra,
            "sequence_length": len(s),
            "window": body.window,
            "step": body.step,
            "n_windows": n_win,
            "protein_level_call": False,
            "note": SCAN_NOTE,
            "windows": [],
            "summary": None,
        }
    art = get_artifacts()
    return scan_protein(s, body.window, body.step, art)


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
