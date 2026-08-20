# Phase 1 report — AMP vs non-AMP dataset

**Status:** locked and accepted  
**Date:** 2026-08-19  
**Scope:** data only. No training.

## What was built

A clean binary AMP (1) vs non-AMP (0) peptide set with a homology-aware 70/15/15 split and a random-split leakage control.

## Sources

| Role | Source | License | Fallback used? |
| --- | --- | --- | --- |
| Positives | DRAMP General (`general_amps.fasta`) | CC BY 4.0 | No (APD / AMPlify AMP not needed) |
| Negatives | AMPlify published non-AMP FASTAs (Zenodo 10.5281/zenodo.7320306) | CC BY 4.0 | UniProt **not** used |

After cleaning, AMPlify **balanced** negatives were short of the positive count, so **6,579** sequences were added from the published **imbalanced** AMPlify non-AMP files (Q3 lock).

## Cleaning funnel

| stage | pos | neg |
| --- | ---: | ---: |
| raw (DRAMP / AMPlify balanced) | 11687 | 4173 |
| length 5–100 | 11459 | 4099 |
| after alphabet (X allowed) | 11411 | 4099 |
| after exact dedup | 10678 | 4099 |
| + imbalanced AMPlify | — | +6579 |
| after conflict resolve (keep AMP) | **10678** | **10659** |

Combined clean set: **21,337** sequences. Mapped B/Z/U/O/J→X: 418 pos / 0 neg. Dropped leftover non-AA: 48 / 0. Cross-class exact conflicts: 19.

## Homology split

MMseqs2 `easy-cluster --min-seq-id 0.3 -c 0.8 --cov-mode 1` (v18.8cc5c). Whole clusters assigned, seed 42.

**9,241 clusters** — 4,778 pos_only / 4,391 neg_only / **72 mixed**

| fold | n | pos | neg |
| --- | ---: | ---: | ---: |
| train | 14904 | 7444 | 7460 |
| val | 3203 | 1611 | 1592 |
| test | 3230 | 1623 | 1607 |

Random-split control (`data/splits/random_*`) uses the same sequences, ignores clusters, 70/15/15, seed 42.

## Key paths

- `data/LICENSE_NOTES.md`
- `data/data_manifest.json`
- `data/splits/split_stats.json`
- `scripts/build_amp_dataset.py`
