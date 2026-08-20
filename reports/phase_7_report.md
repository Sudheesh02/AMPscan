# Phase 7 report — offline Streamlit demo

**Status:** complete  
**Date:** 2026-08-20  
**Scope:** local demo only. No retraining. No DeepLoc / GO / Pfam. No APIs.

## Pages

| Page | What it does |
| --- | --- |
| Predict | Paste one sequence or upload FASTA (max 50). Locked preprocess. Platt-calibrated RF is the primary P(AMP). Temperature-scaled CNN (T = 1.283) is secondary. Label at 0.5 on the RF score. Length, net charge, GRAVY. CNN IG heatmap. |
| Metrics | Static homology vs random table (RF / ESM-2 / CNN), ECE before/after calibration, one-paragraph limitations. |

## Models loaded (read-only)

- `models/baseline/homology_rf.joblib` — primary score
- Platt map `p = sigmoid(10.0847 * p_rf − 5.0839)` from `models/calibration/homology_rf_platt.json`
- `models/cnn1d/homology_cnn1d.pt` — secondary score + IG
- CNN temperature T = 1.2833 from `models/calibration/homology_cnn_temperature.json`

No Phase 3 ESM weights are loaded in the demo (too heavy for a CPU-first judge laptop). ESM numbers appear only on the static Metrics page.

## Train-set warning

Magainin-2 (`POS_DRAMP_DRAMP02271`), LL-37 (`POS_DRAMP_DRAMP03571`), and melittin (`POS_DRAMP_DRAMP03002`) are **exact matches in the homology training set**. The Predict page shows the banner:

> These three examples are in the TRAINING set.

and the precomputed Phase-6 heatmaps from `reports/explain/`.

## Run command

```bash
streamlit run app/streamlit_app.py
```

(from `SIH TEST`, using the `amp-data` conda env).

## Files

- `app/streamlit_app.py`
- `app/README.md`
- `reports/phase_7_report.md`
