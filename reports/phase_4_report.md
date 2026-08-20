# Phase 4 report — 1D-CNN

**Status:** complete  
**Date:** 2026-08-20  
**Scope:** small 1D-CNN on 21-channel one-hot peptides. No ESM input, no IG, no Streamlit, no temperature scaling.

Locked Phase 1–3 paths were not modified.

## Setup

| Item | Value |
| --- | --- |
| Input | homology `data/splits/{train,val,test}.fasta` |
| Alphabet | 20 AA + X (21st channel); pad = all-zero columns |
| Max length | 100 |
| Conv | 21→64 (k=5), 64→128 (k=5), 128→128 (k=3) |
| Pool | global max |
| Head | 128→64→1, ReLU, dropout |
| Dropout (val-selected) | 0.2 |
| Loss | BCEWithLogits + pos_weight |
| Seed | 42 |
| Device | cuda |

## Homology test comparison

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF (locked) | 0.8734 | 0.8734 | 0.9515 | 0.9542 | 1388 | 219 | 190 | 1433 |
| Phase 3 ESM-2 35M linear (locked) | 0.8622 | 0.8622 | 0.9450 | 0.9424 | 1376 | 231 | 214 | 1409 |
| Phase 4 1D-CNN | 0.8650 | 0.8648 | 0.9424 | 0.9465 | 1334 | 273 | 163 | 1460 |

## Leakage control (random split, separately trained CNN)

| model | ROC-AUC | PR-AUC | acc |
| --- | ---: | ---: | ---: |
| Phase 2 RF | 0.9791 | 0.9804 | 0.9231 |
| Phase 3 ESM-2 35M linear | 0.9657 | 0.9663 | 0.9009 |
| Phase 4 1D-CNN | 0.9749 | 0.9772 | 0.9203 |

CNN leakage gap (random − homology ROC-AUC): **+0.0325**.

## Light val tuning

Tried dropout ∈ {0.20, 0.35} on homology val ROC-AUC; winner reused for the random-split run.

## Files

- `models/cnn1d/homology_cnn1d.pt`, `models/cnn1d/random_cnn1d.pt`
- `reports/cnn1d/SUMMARY.md`, `metrics.csv`, plots
- `reports/phase_4_report.md`
- `data/processed/cnn1d/*.npz` (integer encodings only; new folder)

## What this does not claim

A 1D-CNN motif detector under a 30% homology split, not a wet-lab AMP assay.

