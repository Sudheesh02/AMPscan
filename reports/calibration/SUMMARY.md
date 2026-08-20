# Phase 5 — calibrated confidence

Built: 2026-08-20T02:44:58Z

Locked Phase 2–4 weights were **not** modified. This phase only fits a scalar
temperature T (ESM-2 linear, 1D-CNN) or a 2-parameter Platt map (RF) on
**validation**, then evaluates on **test**.

## Methods

- **Temperature scaling** (ESM-2, CNN): `p = sigmoid(logit / T)`, T > 0 fit by
  NLL on val. Monotone in the logit, so ROC-AUC is unchanged.
- **Platt scaling** (RF only): `p = sigmoid(a * p_rf + b)` fit by logistic
  regression on val RF probabilities. This is **not** temperature scaling.
- ECE: equal-width, **15 bins** on [0, 1], weighted by bin count.
- Brier: mean squared error of predicted AMP probability.

## Homology test

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | uncal ROC-AUC | cal ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF (Platt) | 0.0776 | 0.0235 | 0.0958 | 0.0883 | 0.9515 | 0.9515 |
| Phase 3 ESM-2 35M linear (T) | 0.0376 | 0.0185 | 0.0956 | 0.0938 | 0.9450 | 0.9450 |
| Phase 4 1D-CNN (T) | 0.0624 | 0.0403 | 0.0991 | 0.0957 | 0.9424 | 0.9424 |

Fitted on homology val: RF a=10.0847, b=-5.0839;
ESM T=1.2855; CNN T=1.2833.

## Random-split test (optional control)

Same recipe, fit on that split's own val using the locked random-split models.

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | uncal ROC-AUC | cal ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RF (Platt) | 0.0876 | 0.0151 | 0.0677 | 0.0558 | 0.9791 | 0.9791 |
| ESM-2 35M linear (T) | 0.0198 | 0.0191 | 0.0733 | 0.0732 | 0.9657 | 0.9657 |
| 1D-CNN (T) | 0.0350 | 0.0226 | 0.0613 | 0.0592 | 0.9749 | 0.9749 |

## Files

- Parameters: `models/calibration/`
- Scores: `data/processed/calibration/` (new folder)
- Plots/tables: `reports/calibration/`
