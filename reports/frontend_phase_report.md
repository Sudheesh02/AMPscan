# Frontend phase — FastAPI + Next.js (Streamlit kept)

**Date:** 2026-08-20  
**Science:** unchanged. No retraining. No metric edits. No touch of `data/splits/` or `models/` weights.

## Structure

```
services/predict_api/     FastAPI, port 8000
  main.py                 GET /health /metrics  POST /predict /explain
  scoring.py              same RF Platt + CNN T + IG as app/streamlit_app.py
  locked_metrics.py       display tables quoted to judges (not recomputed)
frontend/                 Next.js 14 App Router + TS + Tailwind, port 3000
  app/page.tsx            landing
  app/predict/page.tsx    sequence → RF primary, CNN secondary, IG + train banner
  app/metrics/page.tsx    homology vs random + ECE
  app/about/page.tsx      limitations
  lib/api.ts              typed fetch wrappers
app/streamlit_app.py      FALLBACK — not deleted
```

## Run commands

From project root, conda env `amp-data`:

```bash
uvicorn main:app --app-dir services/predict_api --host 127.0.0.1 --port 8000
cd frontend && npm install && npm run dev
```

- **One origin:** http://localhost:3000 (`./scripts/run_web.sh`)
- `/api/*` rewrites to FastAPI `:8000`
- Dark mode default; light toggle persisted in `localStorage`
- Env: `NEXT_PUBLIC_API_URL=/api`

## What is still Streamlit vs replaced

| Surface | Status |
| --- | --- |
| Judge demo (Predict / Metrics / Limitations) | **Replaced** by Next.js |
| Scoring formulas, Platt a/b, CNN T, canonical IDs | **Copied**, not retrained |
| `app/streamlit_app.py` | **Kept** as offline fallback |
| Homology RF ROC-AUC 0.9515 / random 0.9791 | **Unchanged** |

## Models loaded (read-only)

- `models/baseline/homology_rf.joblib`
- `models/calibration/homology_rf_platt.json`
- `models/cnn1d/homology_cnn1d.pt`
- `models/calibration/homology_cnn_temperature.json`

ESM-2 heads are **not** loaded in this API (same as Streamlit). They appear only as locked rows on `/metrics`.

## Smoke test (locked RF, magainin-2)

`POST /predict` `{ "sequence": "GIGKFLHSAKKFGKAFVGEIMNS" }`

- `valid: true`, length 23
- primary `rf_homology_platt` **P(AMP) = 0.993312**, label **AMP**, calibrated
- secondary CNN T-scaled P(AMP) ≈ 0.9788, T = 1.283257835158267
- `POST /explain` `train_set_warning: true`, `matched_train_id: POS_DRAMP_DRAMP02271`

Next.js `GET / /predict /metrics /about` → HTTP 200. Streamlit file still at `app/streamlit_app.py`.
