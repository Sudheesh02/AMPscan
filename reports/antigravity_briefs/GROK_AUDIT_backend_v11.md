# PASTE THIS TO GROK — audit AMPscan API v1.1 (backend)

You are auditing **backend work already committed in the working tree**. Do not retrain. Do not “improve” Platt, 425-D, or the forest. Pass / fail in chat with file:line evidence.

Repo: `/home/sudheesh02/SIH TEST`  
Contract: `services/predict_api/API_CONTRACT.md`  
Smoke: `scripts/smoke_api_v11.py` (amp-data env)  
Headline that must still be quoted: **RF homology-test ROC-AUC 0.9515**.

This audit is for **Grok’s API v1.1**, not the frontend intern (that brief is `FRONTEND_v1.1.md` and may not be done yet).

---

## 0. Scope of the diff

Read, do not rewrite unless you find a real bug:

- `services/predict_api/scoring.py`
- `services/predict_api/main.py`
- `services/predict_api/locked_metrics.py`
- `services/predict_api/README.md`
- `services/predict_api/API_CONTRACT.md`
- `scripts/smoke_api_v11.py`

Confirm **untouched**:

- `models/baseline/homology_rf.joblib`
- `models/cnn1d/homology_cnn1d.pt`
- `models/calibration/homology_rf_platt.json`
- `models/calibration/homology_cnn_temperature.json`
- `data/splits/train.fasta`, `val.fasta`, `test.fasta`

`git diff --stat` those model/split paths must be empty. If not → **FAIL**.

---

## 1. Locked science (automatic FAIL if any miss)

1. `VERSION` is `ampscan-api-1.1` but **headline.quote is still 0.9515** on `GET /metrics`.
2. Single-seq `rf_calibrated` still `featurize_one` → `predict_proba` → `sigmoid(a * p_raw + b)` with **a/b loaded from the JSON**, not hardcoded differently.
3. CNN still `sigmoid(logit / T)` with T from `homology_cnn_temperature.json`.
4. Feature width still **425**. No peptidy, PC6, TSI, hemolysis, radar, DBAASP heads.
5. `GET /metrics` `cohort_2b.ampscan_rf.roc_auc == 0.9030`, `pr_auc == 0.9205`, `ece_15 == 0.2767`, `do_not_quote.value == 0.9935` with a length-confound why. `recomputed` is **false**.
6. No prose that ranks Cohort 2b tools by accuracy, or that calls 0.9935 SOTA.

---

## 2. `/predict-batch`

1. Body is `{ sequences: [{ id?, sequence }] }`, cap **500** (HTTP 422 over cap).
2. Valid rows scored with **`featurize_many` + one `rf.predict_proba`** and batched CNN — not a Python `for seq: featurize_one`.
3. Mixed valid/invalid: invalid rows `valid: false`, valid rows keep order and `id`.
4. Each valid row schema **matches** `/predict` plus `id` (primary RF Platt, secondary CNN T, `features_preview`, `nearest_train`).
5. Empty list → 422. One-item batch P(AMP) equals `/predict` on the same seq (RF Δ **0**; CNN < 1e-6).

---

## 3. `/scan`

1. Default `window=25`, `step=1`; window clamped **5–100**.
2. First FASTA record only (must **not** concatenate multi-FASTA).
3. Caps: protein length **5000**, windows **2000**; over cap is an error that says increase `step`, not a silent trim.
4. Every window has `p_amp` from **locked RF Platt**, 1-based inclusive `start`/`end`, same formula as `scripts/scan_protein.py`.
5. Response has `protein_level_call: false` and note ≈ “not a protein-level AMP call”.
6. No AMP/non-AMP label for the **whole protein**. Summary may have max window only.
7. A 25-mer scored via `/scan` equals `rf_calibrated` on that mer.

---

## 4. Nearest train (honesty)

1. Index is `data/splits/train.fasta` (~14904), loaded at startup, not MMseqs.
2. Identity is **ungapped**, candidates with `|Δlength| ≤ 2`. Exact seq → `identity=1`, `exact_match=true`, train-set-recall note.
3. Note on inexact hits **explicitly says this is not an MMseqs 30% cluster wall**.
4. Magainin-2 `GIGKFLHSAKKFGKAFVGEIMNS` → `POS_DRAMP_DRAMP02271`. LL-37 → `POS_DRAMP_DRAMP03571`.
5. Per-query time after warmup **< 3 ms** (smoke prints this). If >15 ms, fail.

---

## 5. `/predict` backward compat + CORS

1. Old fields still present: `sequence`, `length`, `valid`, `errors`, `primary`, `secondary`, `features_preview`. New key `nearest_train` is additive.
2. Length >100 → `valid: false` and error text points at **`POST /scan`**.
3. `/explain` unchanged in meaning: IG on CNN, canonical banner only for magainin-2 / LL-37 / melittin.
4. CORS allow-list includes `http://localhost:3000` **and** `https://ampscan.vercel.app`. Random origins must not get `Access-Control-Allow-Origin`.

---

## 6. Run (do not skip)

```bash
cd "/home/sudheesh02/SIH TEST"
/home/sudheesh02/miniforge3/envs/amp-data/bin/python scripts/smoke_api_v11.py
```

Expect `SMOKE OK`. If you cannot run it, say so; do not invent pass.

Spot-check in that same env (TestClient or curl):

- `GET /health` version `ampscan-api-1.1`, `n_train` ~14904
- `GET /metrics` headline 0.9515
- `POST /predict` magainin-2
- `POST /predict-batch` 2 valid + 1 short
- `POST /scan` hCAP-18 from `reports/benchmarks/hcap18_test.fasta` window 25 step 5 — max P high near C-terminus (LL-37), `protein_level_call` false

Optional: `rf_calibrated_many` vs loop `rf_calibrated` on 3 seqs, max |Δ| RF must be **0**.

---

## 7. Product lies to hunt

FAIL if any of these appear in API JSON, README, or contract:

- TSI, HC50, hemolysis-as-ours, pathogen radar
- “protein is AMP”
- “<30% identity to train” as a computed MMseqs wall on `/predict`
- 0.9935 as a metric to quote
- GPU 20× / “ONNX 6600 seq/s” claims for this API
- Changing Platt a/b or T
- ESM/LoRA/GAT in the request path

---

## Reply format

```
VERDICT: PASS | FAIL | PASS WITH NITS
Locked weights: …
Batch: …
Scan: …
Nearest-train honesty: …
Metrics 2b payload: …
CORS / compat: …
Smoke: …
Nits (non-blocking): …
Must-fix (if FAIL): …
```

Do not start frontend work in this audit. Do not retrain.

---

## After the intern lands `FRONTEND_v1.1.md` (separate pass)

Only then audit `frontend/` + `INTERN_HANDOFF_frontend.md`:

1. Classify FASTA uses **one** `/predict-batch`, not a loop of `/predict`.
2. IG is lazy (active row), not 500 Captum calls.
3. Length >100 shows scan track + disclaimer; no protein AMP badge.
4. Nearest-train copy does **not** say MMseqs 30%.
5. Evidence 2b table is **ROC-AUC first**; caption forbids ranking by acc@0.5.
6. Hero still 0.9515. No 0.9935 stat. No TSI/radar.
7. `npx tsc --noEmit` clean.
