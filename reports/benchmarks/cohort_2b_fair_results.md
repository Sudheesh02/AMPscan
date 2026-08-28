# Cohort 2b — length-matched DBAASP OOD (fair-ish)

**Locked AMPscan v1 metric is still Cohort 1 RF ROC-AUC 0.9515.**

Negatives are mostly **random windows** from unused long UniProt-style non-AMPs (`n_neg_fragment=11012`, intact unused shorts `n_neg_intact=178`). Not experimentally inactive peptides.

Length medians: DBAASP pos **14** vs neg **14** (gap 0). Gap must be ≤ 8 aa.

MMseqs vs AMPscan train and vs DBAASP novels: `--min-seq-id 0.3 -c 0.8 --cov-mode 1`.

| model | n | skip | acc | MCC | ROC-AUC | PR-AUC | ECE-15 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AMPscan RF (Platt) | 22380 | 0 | 0.6449 | 0.3765 | **0.9030** | 0.9205 | 0.2767 |
| AMPscan 1D-CNN (T) | 22380 | 0 | 0.6162 | 0.3235 | **0.8894** | 0.9117 | 0.3044 |
| Macrel | 20426 | 1954 | 0.8222 | 0.6554 | **0.8998** | 0.9017 | 0.1058 |
| AI4AMP PC6 | 22380 | 0 | 0.8081 | 0.6287 | **0.8786** | 0.9031 | 0.0870 |
| AMPlify balanced | 20426 | 1954 | 0.8216 | 0.6421 | **0.8991** | 0.9075 | 0.0867 |

ROC: `02b_cohort2b_roc.png`.

## Do not quote

The earlier full Cohort 2 RF ROC **0.9935** (`cohort_2_dbaasp_ood_results.md`) used 14-aa DBAASP vs 76-aa leftovers. That table is length-confounded.

If 2b ROC is still ~0.99, the fragment windows are still too easy (composition). Say that. Do not call it SOTA.

## Length check

     count       mean       std  min   25%   50%   75%    max
y                                                            
0  11190.0  15.928329  8.574178  5.0  10.0  14.0  19.0   98.0
1  11190.0  15.993298  8.821000  5.0  10.0  14.0  19.0  100.0
