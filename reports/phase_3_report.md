# Phase 3 report — frozen ESM-2 35M head

**Status:** complete  
**Date:** 2026-08-20  
**Scope:** frozen `facebook/esm2_t12_35M_UR50D` mean-pooled embeddings + linear head. No ESM fine-tune, no 150M, no CNN, no Streamlit, no Integrated Gradients.

Phase 2 `models/baseline/` and `reports/baseline/` were **not** modified.

## Setup

| Item | Value |
| --- | --- |
| Encoder | `facebook/esm2_t12_35M_UR50D` (12 layers, hidden 480) |
| Trainable ESM params | **0** (frozen) |
| Pooling | mean over residue tokens; CLS / EOS / PAD excluded |
| Hardware | NVIDIA GeForce RTX 5060 Laptop GPU, 8 GB |
| Precision / batch | fp16 autocast, batch 32 |
| Seed | 42 |
| Head selected | **linear** (L2 logistic regression, `class_weight=balanced`, StandardScaler on train embeddings) |
| MLP | not used — linear val ROC-AUC 0.9451 was within 0.02 of Phase-2 RF val (0.9513) |

Embeddings were extracted on the **homology** train/val/test FASTAs. Random-split matrices were assembled from the same ID→vector store (same 21,337 peptides; no second ESM pass).

Stack: torch 2.11.0+cu128, transformers 5.15.1, sklearn 1.9.0, CUDA 12.8, GPU capability sm_120.

## Homology test — classical RF vs ESM-2 35M head

This is the number that matters.

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF (locked) | **0.8734** | **0.8734** | **0.9515** | **0.9542** | 1388 | 219 | 190 | 1433 |
| ESM-2 35M linear | 0.8622 | 0.8622 | 0.9450 | 0.9424 | 1376 | 231 | 214 | 1409 |

ESM-2 35M frozen + linear is **slightly below** the Phase-2 RF on the honest homology split (Δ ROC-AUC = −0.0065). It still beats Phase-2 logistic regression (0.902 ROC-AUC) by a wide margin.

## Random-split test (leakage control)

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| Phase 2 RF | 0.9231 | 0.9231 | 0.9791 | 0.9804 |
| ESM-2 35M linear | 0.9009 | 0.9009 | 0.9657 | 0.9663 |

Both models look better on the random split (homology leakage). Gap for ESM-2: +0.021 ROC-AUC (random − homology).

## Validation (for head selection)

| split | head | val ROC-AUC |
| --- | --- | ---: |
| homology | linear | 0.9451 |
| random | linear | 0.9614 |

## Files written (Phase 3 only)

- Embeddings: `data/processed/embeddings/esm2_35M/{homology,random}_{train,val,test}.npz`
- Model + scaler: `models/esm2_35M/{homology,random}_{logreg,scaler}.joblib`
- Metrics + plots: `reports/esm2_35M/`
- Short compare write-up: `reports/esm2_35M/SUMMARY.md`
- This report: `reports/phase_3_report.md`

## What this does **not** claim

The frozen 35M head is a sequence-pattern classifier under a 30% homology split. It is not a wet-lab AMP assay and is not better than the classical RF on this split. Next phases (if any) can add CNN / IG / a demo without changing these numbers.
