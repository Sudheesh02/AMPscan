# AMP vs non-AMP Streamlit demo (Phase 7)

Offline only. No APIs. No training. Loads locked Phase 2–6 artifacts.

## Run

From the project root (`SIH TEST`):

```bash
/home/sudheesh02/miniforge3/envs/amp-data/bin/streamlit run app/streamlit_app.py
```

Shorter if that env is already on `PATH`:

```bash
streamlit run app/streamlit_app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Pages

- **Predict** — paste a sequence or upload FASTA (cap 50). Primary score is Platt-calibrated RF P(AMP). Secondary is CNN P(AMP) after T = 1.283. CNN Integrated Gradients heatmap per sequence. Magainin-2 / LL-37 / melittin show the locked Phase-6 heatmaps plus a training-set banner.
- **Metrics** — static homology vs random table, ECE before/after calibration, limitations.

## Models loaded (read-only)

- `models/baseline/homology_rf.joblib`
- `models/calibration/homology_rf_platt.json` (a = 10.0847, b = −5.0839)
- `models/cnn1d/homology_cnn1d.pt`
- `models/calibration/homology_cnn_temperature.json` (T = 1.2833)
- `reports/explain/heatmap_*.png` for the three canonical peptides
