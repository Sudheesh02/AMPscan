# AMPscan API v1.1 — Vercel contract

Base URL locally: `http://127.0.0.1:8000`  
Production frontend origin: `https://ampscan.vercel.app` (CORS allow-listed).

Frozen weights. Same Platt JSON (`a=10.0847`, `b=-5.0839`). Same 425-D features.
Do not treat extra JSON keys as breaking; ignore unknown fields.

Live schema: `GET /openapi.json`.

## Limits

| Limit | Value |
| --- | --- |
| Peptide length for `/predict` and `/predict-batch` | 5–100 |
| Batch size | 500 |
| Scan protein length | 5000 |
| Scan windows | 2000 (increase `step` if over) |
| Scan window | 5–100 (default 25) |
| Alphabet | ACDEFGHIKLMNPQRSTVWXY after B/Z/U/O/J→X |

## GET `/health`

```json
{
  "ok": true,
  "version": "ampscan-api-1.1",
  "device": "cpu",
  "models_loaded": {"rf": "...", "cnn": "...", "platt_a": 10.08, "platt_b": -5.08, "cnn_T": 1.28},
  "train_index": {"n": 14904, "path": "data/splits/train.fasta", "length_delta": 2},
  "limits": {"batch_cap": 500, "scan_max_len": 5000, "scan_max_windows": 2000, "peptide_len": [5, 100]},
  "endpoints": ["/health", "/metrics", "/predict", "/predict-batch", "/scan", "/explain"],
  "offline": true
}
```

## GET `/metrics`

Existing keys unchanged (`homology_test`, `headline.quote = 0.9515`, `recomputed: false`).

**New key** `cohort_2b`:

```json
{
  "name": "Cohort 2b — length-matched DBAASP OOD",
  "locked_headline_remains": 0.9515,
  "ampscan_rf": {"roc_auc": 0.9030, "pr_auc": 0.9205, "accuracy_at_0.5": 0.6449, "ece_15": 0.2767},
  "ranking": "…tie at ~0.90 ROC… Do not rank tools by accuracy at 0.5…",
  "platt_transfer": "Platt … does not transfer (ECE 0.2767).",
  "do_not_quote": {"value": 0.9935, "why": "length-confounded Cohort 2"}
}
```

Do **not** display 0.9935 as a quality number. Do **not** rank 2b tools by accuracy.

## POST `/predict`

Request: `{ "sequence": "GIGKFLHSAKKFGKAFVGEIMNS" }`

Success (length 5–100):

```json
{
  "sequence": "GIGKFLHSAKKFGKAFVGEIMNS",
  "length": 23,
  "valid": true,
  "errors": [],
  "primary": {
    "model": "rf_homology_platt",
    "p_amp": 0.99,
    "label": "AMP",
    "calibrated": true,
    "threshold": 0.5
  },
  "secondary": {"model": "cnn1d_T", "p_amp": 0.99, "temperature": 1.283257835158267, "calibrated": true},
  "features_preview": {
    "length": 23,
    "net_charge_pH7": 3.0,
    "GRAVY": 0.1,
    "hydrophobic_moment": 0.5,
    "aromatic_fraction": 0.1,
    "aac_nonzero": {"K": 0.17}
  },
  "nearest_train": {
    "train_id": "POS_DRAMP_DRAMP02271",
    "identity": 1.0,
    "train_length": 23,
    "train_label": "AMP",
    "exact_match": true,
    "note": "Exact match to a homology-train peptide. Score is train-set recall, not a held-out test case."
  }
}
```

Invalid (including length >100): `valid: false`, `primary: null`, `nearest_train: null`.
If length >100 the error string points at `POST /scan`.

`nearest_train.identity` is **ungapped identity** among train peptides with `|Δlength| ≤ 2`.
It is **not** an MMseqs 30% cluster wall. Do not caption it as “<30% homology”.

## POST `/predict-batch`

Request:

```json
{
  "sequences": [
    {"id": "magainin-2", "sequence": "GIGKFLHSAKKFGKAFVGEIMNS"},
    {"id": "too_short", "sequence": "ACDE"}
  ]
}
```

`id` optional (defaults to `item_1` …). Cap 500; over cap → HTTP 422.

Response:

```json
{
  "version": "ampscan-api-1.1",
  "n": 2,
  "n_valid": 1,
  "n_invalid": 1,
  "results": [
    {"id": "magainin-2", "valid": true, "primary": {"p_amp": 0.99, "label": "AMP"}, "nearest_train": {}},
    {"id": "too_short", "valid": false, "errors": ["length 4 is outside 5–100"], "primary": null}
  ]
}
```

Each `results[]` row is a `/predict` payload plus `id`. Mixed valid/invalid is OK.
Use this for FASTA paste. Keep `/explain` per sequence (Captum is not batched).

## POST `/scan`

For chains longer than 100 aa (also legal for shorter peptides).

Request: `{ "sequence": "...", "window": 25, "step": 1 }`

Coordinates are **1-based inclusive**, same as `scripts/scan_protein.py`.
First FASTA record only (does not concatenate multi-FASTA).

Success:

```json
{
  "valid": true,
  "errors": [],
  "sequence_length": 170,
  "window": 25,
  "step": 1,
  "n_windows": 146,
  "protein_level_call": false,
  "note": "Window scores from the locked RF. This is not a protein-level AMP call.",
  "windows": [{"start": 1, "end": 25, "seq": "MKTQR...", "p_amp": 0.12, "label": "non-AMP"}],
  "summary": {
    "max_p_amp": 0.99,
    "max_start": 134,
    "max_end": 158,
    "n_windows_ge_0.5": 20,
    "n_windows_ge_0.9": 8
  }
}
```

UI must show `protein_level_call: false` / the `note`. Do not collapse windows into “this protein is AMP”.

## POST `/explain`

Unchanged: `{ "sequence": "..." }` → residue IG vector + canonical-train banner for magainin-2 / LL-37 / melittin.

## Scoring (do not reimplement on Vercel)

```
p_rf_cal = sigmoid(a * p_rf_raw + b)     # a, b from homology_rf_platt.json
p_cnn_cal = sigmoid(logit / T)           # T from homology_cnn_temperature.json
label = AMP if p_rf_cal >= 0.5 else non-AMP
```

The 0.5 cut was fit on Cohort 1. On Cohort 2b it over-calls AMP (ECE 0.2767); ranking still holds.

## Out of scope

No TSI, no pathogen radar, no DBAASP multi-task heads, no live retraining.
