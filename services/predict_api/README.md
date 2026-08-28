# AMPscan FastAPI (locked inference)

Loads existing homology-split weights only. No training. No internet.
Primary score is Random Forest + Platt. Secondary is 1D-CNN + temperature.
**v1 headline remains homology-test RF ROC-AUC 0.9515.**

From the **project root**:

```bash
# amp-data env
/home/sudheesh02/miniforge3/envs/amp-data/bin/uvicorn main:app \
  --app-dir services/predict_api \
  --host 127.0.0.1 \
  --port 8000
```

OpenAPI: `http://127.0.0.1:8000/docs`  ·  JSON contract: `API_CONTRACT.md`

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | Models + train-index size |
| GET | `/metrics` | Locked tables + Cohort 2b payload (not recomputed) |
| POST | `/predict` | One peptide, 5–100 aa |
| POST | `/predict-batch` | Up to 500 peptides, `featurize_many` + one RF `predict_proba` |
| POST | `/scan` | Windowed locked RF for sequences >100. **Not** a protein-level AMP call |
| POST | `/explain` | CNN Integrated Gradients (per sequence) |

CORS allows localhost:3000/3001 and `https://ampscan.vercel.app`.

Streamlit fallback remains: `streamlit run app/streamlit_app.py`
