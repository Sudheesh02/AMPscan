# Phase 5 report — calibrated confidence

**Status:** complete  
**Date:** 2026-08-20  
**Scope:** temperature scaling (ESM-2, CNN) and Platt scaling (RF). No IG, Streamlit, or new models.

Locked directories `models/baseline/`, `models/esm2_35M/`, `models/cnn1d/` weights
and earlier phase reports were read, not rewritten.

## Setup

| Item | Value |
| --- | --- |
| Fit set | homology **val** (primary) |
| Eval set | homology **test** |
| ECE bins | 15, equal-width |
| ESM / CNN | one scalar T, NLL on val logits |
| RF | Platt logistic on `p_rf` (not temperature) |
| Seed | 42 |

## Homology test

| model | uncal ECE | cal ECE | uncal Brier | cal Brier | ROC-AUC uncal | ROC-AUC cal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF (Platt) | 0.0776 | 0.0235 | 0.0958 | 0.0883 | 0.9515 | 0.9515 |
| Phase 3 ESM-2 35M linear (T) | 0.0376 | 0.0185 | 0.0956 | 0.0938 | 0.9450 | 0.9450 |
| Phase 4 1D-CNN (T) | 0.0624 | 0.0403 | 0.0991 | 0.0957 | 0.9424 | 0.9424 |

ROC-AUC is essentially unchanged after calibration (temperature is a monotone
rescaling of logits; Platt `a` was 10.085, so rank order is preserved).

## Random-split control

| model | uncal ECE | cal ECE | Brier uncal | Brier cal | ROC-AUC cal |
| --- | ---: | ---: | ---: | ---: | ---: |
| RF | 0.0876 | 0.0151 | 0.0677 | 0.0558 | 0.9791 |
| ESM-2 linear | 0.0198 | 0.0191 | 0.0733 | 0.0732 | 0.9657 |
| 1D-CNN | 0.0350 | 0.0226 | 0.0613 | 0.0592 | 0.9749 |

## Parameters (homology)

- RF Platt: a=10.084666, b=-5.083873
- ESM T=1.285468
- CNN T=1.283258

T > 1 softens over-confident logits; T < 1 sharpens under-confident ones.

## Files

- `models/calibration/`
- `reports/calibration/SUMMARY.md`
- `reports/phase_5_report.md`
- `data/processed/calibration/*.npz`

## What this does not claim

Calibration adjusts **confidence**, not biology. It does not change the homology-split
ranking story from Phases 2–4.
