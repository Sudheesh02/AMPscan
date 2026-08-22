# AMPscan FastAPI (locked inference)

Loads existing homology-split weights only. No training. No internet.

From the **project root**:

```bash
# amp-data env
/home/sudheesh02/miniforge3/envs/amp-data/bin/uvicorn main:app \
  --app-dir services/predict_api \
  --host 127.0.0.1 \
  --port 8000
```

- `GET  /health`
- `GET  /metrics` — locked tables, not recomputed
- `POST /predict`  `{ "sequence": "..." }`
- `POST /explain`  `{ "sequence": "..." }`

Streamlit fallback remains: `streamlit run app/streamlit_app.py`
