# ESM-2 35M frozen head vs classical RF

Built: 2026-08-20T02:11:24Z
Phase 3 only. ESM-2 encoder is **frozen**. No 150M, CNN, Streamlit, or IG.

## Setup

- Encoder: `facebook/esm2_t12_35M_UR50D` (hidden size 480, 12 layers)
- Pooling: mean over residue tokens; CLS / EOS / PAD excluded
- Batch size `32`, fp16 autocast on CUDA, no ESM gradient updates
- Seed `42`, class_weight=balanced (linear) / pos_weight (MLP)
- Selected head: **linear**
- Linear: L2 logistic regression, C=1.0, StandardScaler fit on train embeddings
- Tiny MLP (fallback): 480→128 ReLU Dropout(0.2)→1, trained only if linear under-fits val
- Homology split is the honest number. Random split is the leakage control.

## Package / hardware versions

- python: `3.12.13`
- numpy: `2.5.2`
- sklearn: `1.9.0`
- torch: `2.11.0+cu128`
- transformers: `5.15.1`
- cuda_available: `True`
- device: `cuda`
- gpu_name: `NVIDIA GeForce RTX 5060 Laptop GPU`
- seed: `42`
- esm_model: `facebook/esm2_t12_35M_UR50D`
- pooling: `mean of residue tokens (exclude CLS/EOS/PAD)`
- esm_frozen: `True`
- batch_size: `32`
- amp_fp16: `True`

## Homology test: classical RF vs ESM-2 35M head

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Phase 2 RF | 0.8734 | 0.8734 | 0.9515 | 0.9542 | 1388 | 219 | 190 | 1433 |
| ESM-2 35M linear | 0.8622 | 0.8622 | 0.9450 | 0.9424 | 1376 | 231 | 214 | 1409 |

## Random-split test (leakage control)

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| Phase 2 RF | 0.9231 | 0.9231 | 0.9791 | 0.9804 |
| ESM-2 35M linear | 0.9009 | 0.9009 | 0.9657 | 0.9663 |

## All ESM-2 head metrics

| split | head | fold | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| homology | linear | val | 0.8676 | 0.8676 | 0.9451 | 0.9479 |
| homology | linear | test | 0.8622 | 0.8622 | 0.9450 | 0.9424 |
| random | linear | val | 0.8888 | 0.8888 | 0.9614 | 0.9625 |
| random | linear | test | 0.9009 | 0.9009 | 0.9657 | 0.9663 |

## Notes

- Existing Phase-1 FASTAs and Phase-2 `models/baseline/`, `reports/baseline/` were not modified.
- Random-split embedding matrices reuse the homology-extracted ID→vector store
  (same 21,337 peptides; no second ESM pass).

## Files

- Embeddings: `data/processed/embeddings/esm2_35M/*.npz`
- Model + scaler: `models/esm2_35M/`
- This report: `reports/esm2_35M/`

