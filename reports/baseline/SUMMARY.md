# Classical baseline — AMP vs non-AMP

Built: 2026-08-19T11:07:15Z
Phase 2 only: logistic regression (L2) and random forest. No ESM, CNN, or app.

## Setup

- Seed: `42`
- Features: 425-dim = AAC(20) + DPC(400) + physchem(5)
  - AAC: 20 standard amino-acid frequencies (length-normalized; X ignored in counts)
  - DPC: 400 dipeptide frequencies over valid 20×20 pairs
  - Physchem: length; net charge at pH 7 (Henderson–Hasselbalch, N/C termini + D/E/C/Y/H/K/R);
    GRAVY (Kyte–Doolittle mean); Eisenberg hydrophobic moment (100°/residue); aromatic fraction (F+W+Y)/L
- Logistic regression: L2, C=1.0, `class_weight=balanced`, features StandardScaled on train
- Random forest: 200 trees, `class_weight=balanced`, unscaled features, `n_jobs=4`
- Positive class = AMP (label 1). Threshold = 0.5 for accuracy / F1 / confusion matrix.
- Homology split: cluster-aware 70/15/15 from Phase 1. Random split: leakage control.
- Models are trained **separately** on each split's train fold (fair leakage comparison).

## Package versions

- python: `3.12.13`
- numpy: `2.5.2`
- scipy: `1.18.0`
- sklearn: `1.9.0`
- matplotlib: `3.11.1`
- joblib: `1.5.3`
- seed: `42`

## Test-set results

| split | model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| homology | logreg | 0.8375 | 0.8374 | 0.9016 | 0.9113 | 1367 | 240 | 285 | 1338 |
| homology | rf | 0.8734 | 0.8734 | 0.9515 | 0.9542 | 1388 | 219 | 190 | 1433 |
| random | logreg | 0.8747 | 0.8747 | 0.9384 | 0.9395 | 1411 | 188 | 213 | 1388 |
| random | rf | 0.9231 | 0.9231 | 0.9791 | 0.9804 | 1449 | 150 | 96 | 1505 |

## Validation-set results

| split | model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| homology | logreg | 0.8495 | 0.8495 | 0.9137 | 0.9094 |
| homology | rf | 0.8761 | 0.8760 | 0.9513 | 0.9540 |
| random | logreg | 0.8616 | 0.8616 | 0.9279 | 0.9279 |
| random | rf | 0.9082 | 0.9081 | 0.9758 | 0.9770 |

## How to read the leakage gap

The random split assigns homologous peptides to different folds, so test metrics
are typically **higher** than on the homology split. The homology-split numbers
are the honest estimate of generalization to distant sequences. A large gap means
the model is partly memorizing family-level patterns rather than a transferable AMP motif.

## Files

- Features: `data/processed/features/*.npz` (new directory; existing data files untouched)
- Models: `models/baseline/{homology,random}_{logreg,rf,scaler}.joblib`
- Metrics: `reports/baseline/metrics.json`, `reports/baseline/metrics.csv`
- Plots: `reports/baseline/cm_*.png`, `roc_*_test.png`, `pr_*_test.png`

