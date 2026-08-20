# Phase 9 report — frozen ESM-2 150M

**Status:** complete (one homology-test evaluation)  
**Date:** 2026-08-20  
**Encoder:** `facebook/esm2_t30_150M_UR50D` frozen, mean-pool residue tokens (CLS/EOS/PAD excluded).  
**Head:** linear (linear val ROC-AUC=0.9372).  
Test was scored **once** after val selection.

## Homology

| set | model | ROC-AUC | PR-AUC | accuracy | macro-F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| val | ESM-2 150M linear | 0.9372 | 0.9409 | 0.8539 | 0.8539 |
| val | Phase 2 RF (locked) | 0.9513 | — | — | — |
| **test** | ESM-2 150M linear | **0.9521** | 0.9516 | 0.8762 | 0.8761 |
| **test** | Phase 2 RF (locked) | **0.9515** | 0.9542 | 0.8734 | 0.8734 |

Δ test ROC-AUC vs RF: **+0.0006**.

## Verdict

Frozen ESM-2 150M **beats** locked RF (0.9521 vs 0.9515).

LoRA: not eligible (val not within 0.01 of RF).

Embeddings: `data/processed/embeddings/esm2_150M/` (new folder). Head: `models/esm2_150M/`.
Random-split `.npz` files were assembled from the homology ID map; they were not used for the test comparison.
