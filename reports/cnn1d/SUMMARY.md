# Phase 4 — 1D-CNN on one-hot peptides

Built: 2026-08-20T02:41:43Z
Homology train only for the primary model. A second CNN with the same
hyperparameters is trained on the random-split train fold for the leakage table
(same protocol as Phases 2–3). ESM embeddings are **not** used as input.

## Architecture

- Input: 21-channel one-hot (20 standard AA + **X**), length padded to 100 with zeros
- Conv1d 21→64 (k=5) → 64→128 (k=5) → 128→128 (k=3), ReLU, dropout
- Global max pool → Linear 128→64→1
- Selected dropout after homology val sweep: **0.2**
- Adam 1e-3, weight_decay 1e-4, pos_weight for class balance, seed 42
- Early stopping on val ROC-AUC (patience 8, max 40 epochs)

## Homology test (primary)

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF | 0.8734 | 0.8734 | 0.9515 | 0.9542 | 1388 | 219 | 190 | 1433 |
| Phase 3 ESM-2 35M linear | 0.8622 | 0.8622 | 0.9450 | 0.9424 | 1376 | 231 | 214 | 1409 |
| Phase 4 1D-CNN | 0.8650 | 0.8648 | 0.9424 | 0.9465 | 1334 | 273 | 163 | 1460 |

## Random-split test (leakage control, separately trained)

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| Phase 2 RF | 0.9231 | 0.9231 | 0.9791 | 0.9804 |
| Phase 3 ESM-2 35M linear | 0.9009 | 0.9009 | 0.9657 | 0.9663 |
| Phase 4 1D-CNN | 0.9203 | 0.9203 | 0.9749 | 0.9772 |

Homology-train ∩ random-test IDs: 2253 / 3200.
That is why a **separately trained** random-split CNN is used for the leakage table.

## Versions

- python: `3.12.13`
- numpy: `2.5.2`
- torch: `2.11.0+cu128`
- cuda_available: `True`
- device: `cuda`
- gpu_name: `NVIDIA GeForce RTX 5060 Laptop GPU`
- seed: `42`
- dropout: `0.2`
- homology_val_roc_auc: `0.9542096734448156`
- random_val_roc_auc: `0.9710038421329187`
- sweep: `[{'dropout': 0.2, 'val_roc_auc': 0.9542096734448156, 'epochs': 16}, {'dropout': 0.35, 'val_roc_auc': 0.9528063969755669, 'epochs': 22}]`
- n_params: `105473`
- input: `21-channel one-hot (20 AA + X), not ESM`

## Files

- Weights: `models/cnn1d/`
- Metrics/plots: `reports/cnn1d/`
- Integer encodings (new folder only): `data/processed/cnn1d/`

