# Phase 2 report — classical baselines

**Status:** locked and accepted  
**Date:** 2026-08-19  
**Scope:** AAC + DPC + physchem features; Logistic Regression (L2) and Random Forest (200 trees). No ESM / CNN / app.

## Features (425-d)

- Amino-acid composition (20)
- Dipeptide composition (400)
- Physchem (5): length, net charge at pH 7 (Henderson–Hasselbalch), GRAVY (Kyte–Doolittle), Eisenberg hydrophobic moment (100°/res), aromatic fraction (F+W+Y)

## Models (CPU, seed 42)

- L2 logistic regression, `C=1.0`, `class_weight=balanced`, StandardScaler on train
- Random forest, 200 trees, `class_weight=balanced`, unscaled features

sklearn 1.9.0, numpy 2.5.2, scipy 1.18.0.

## Test results

| split | model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| homology | logreg | 0.8375 | 0.8374 | 0.9016 | 0.9113 | 1367 | 240 | 285 | 1338 |
| homology | **rf** | **0.8734** | **0.8734** | **0.9515** | **0.9542** | 1388 | 219 | 190 | 1433 |
| random | logreg | 0.8747 | 0.8747 | 0.9384 | 0.9395 | 1411 | 188 | 213 | 1388 |
| random | rf | 0.9231 | 0.9231 | 0.9791 | 0.9804 | 1449 | 150 | 96 | 1505 |

Leakage gap (random − homology ROC-AUC): logreg +0.037, RF +0.028.  
**Honest baseline for later phases: homology RF, ROC-AUC 0.9515.**

## Paths (do not modify)

- `data/processed/features/*.npz`
- `models/baseline/`
- `reports/baseline/SUMMARY.md`
