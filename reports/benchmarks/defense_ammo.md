# Cohort 1 defense ammo — errors, thresholds, ranking vs Macrel

Frozen scores. Locked RF ROC-AUC remains **0.9515**. Do not quote 0.993.

## Who we miss at P ≥ 0.5 (RF Platt)

| bucket | n | median len | median charge | median GRAVY | median μH | mean Cys |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TN | 1403 | 70 | 0.21 | -0.35 | 0.11 | 1.21 |
| FP | 204 | 20 | 1.00 | -0.33 | 0.22 | 1.66 |
| FN | 195 | 38 | 0.00 | -0.31 | 0.13 | 1.95 |
| TP | 1428 | 18 | 3.00 | -0.03 | 0.32 | 0.99 |

Boxplots: `cohort1_error_boxplots.png`. Lowest-P FNs: `cohort1_fn_lowest_p.csv`. Highest-P FPs: `cohort1_fp_highest_p.csv`.

If FNs are less cationic / less hydrophobic than TPs, v2 physchem extras might help. If FNs look like TPs, it is homology/label noise — do not add features.

## Operating points (precision/recall)

Cohort 1 is ~50/50. Real screens are AMP-rare. Raise the threshold for precision.

| model | P≥ | n_called AMP | precision | recall | specificity |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMPscan RF (Platt) | 0.50 | 1632 | 0.875 | 0.880 | 0.873 |
| AMPscan RF (Platt) | 0.80 | 1255 | 0.948 | 0.733 | 0.960 |
| AMPscan RF (Platt) | 0.90 | 1059 | 0.974 | 0.635 | 0.983 |
| AMPscan RF (Platt) | 0.95 | 863 | 0.987 | 0.525 | 0.993 |
| Macrel | 0.50 | 936 | 0.976 | 0.580 | 0.986 |
| Macrel | 0.80 | 441 | 1.000 | 0.280 | 1.000 |
| Macrel | 0.90 | 246 | 1.000 | 0.156 | 1.000 |
| Macrel | 0.95 | 151 | 1.000 | 0.096 | 1.000 |
| AMPlify balanced | 0.50 | 1202 | 0.964 | 0.736 | 0.973 |
| AMPlify balanced | 0.80 | 994 | 0.979 | 0.618 | 0.987 |
| AMPlify balanced | 0.90 | 905 | 0.987 | 0.567 | 0.993 |
| AMPlify balanced | 0.95 | 834 | 0.993 | 0.526 | 0.996 |
| AMPscan RF · Cohort 2b fragments | 0.50 | 18336 | 0.588 | 0.964 | 0.326 |
| AMPscan RF · Cohort 2b fragments | 0.80 | 13846 | 0.728 | 0.900 | 0.663 |
| AMPscan RF · Cohort 2b fragments | 0.90 | 11369 | 0.824 | 0.837 | 0.821 |
| AMPscan RF · Cohort 2b fragments | 0.95 | 9250 | 0.900 | 0.744 | 0.918 |

Full table: `operating_points.csv`.

## Ranking vs Macrel / AMPlify (paired bootstrap, common IDs)

- RF vs Macrel: ΔAUC = **0.0014**, 95% boot CI [-0.0049, 0.0075], CI excludes 0: **False** (n=3182).
- RF vs AMPlify: ΔAUC = **0.0228**, 95% boot CI [0.0127, 0.0324], CI excludes 0: **True** (n=3182).

If RF vs Macrel CI includes 0: say **tied on ranking, we win calibration (ECE 0.023 vs 0.204)**.
JSON: `delong_bootstrap_auc.json`.
