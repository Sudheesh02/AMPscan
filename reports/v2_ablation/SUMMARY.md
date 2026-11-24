# AMPscan v1.1 vs v2 (Length-Debiased) Ablation Report

- **v1.1**: Trained on `data/splits/train.fasta` (14,904 seqs; pos median 20 aa vs neg median 61 aa; 425-D with raw `length`).
- **v2**: Trained on `data/splits_v2/train.fasta` (7,720 seqs; 5-aa bin length-matched, pos/neg median 32 aa; 424-D without raw `length` + fixed `hydrophobic_moment_v2`).

| Benchmark | Model | N | ROC-AUC | PR-AUC | F1 | Accuracy | ECE |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `v1_homology_test` | `v1.1_rf_425d` | 3230 | 0.9515 | 0.9542 | 0.8774 | 0.8765 | 0.0216 |
| `v1_homology_test` | `v2_rf_424d_debiased` | 3230 | 0.8930 | 0.9088 | 0.8012 | 0.8142 | 0.0563 |
| `v1_homology_test` | `v1.1_cnn` | 3230 | 0.9424 | 0.9465 | 0.8701 | 0.8650 | 0.0363 |
| `v1_homology_test` | `v2_cnn_debiased` | 3230 | 0.9115 | 0.9215 | 0.8175 | 0.8319 | 0.0637 |
| `v2_length_matched_test` | `v1.1_rf_425d` | 1630 | 0.8716 | 0.8902 | 0.7955 | 0.7865 | 0.0853 |
| `v2_length_matched_test` | `v2_rf_424d_debiased` | 1630 | 0.9214 | 0.9301 | 0.8542 | 0.8540 | 0.0263 |
| `v2_length_matched_test` | `v1.1_cnn` | 1630 | 0.9021 | 0.9138 | 0.8087 | 0.7883 | 0.1121 |
| `v2_length_matched_test` | `v2_cnn_debiased` | 1630 | 0.9140 | 0.9181 | 0.8464 | 0.8466 | 0.0335 |
| `cohort_2b_fair_ood` | `v1.1_rf_425d` | 22380 | 0.9030 | 0.9205 | 0.7308 | 0.6449 | 0.2771 |
| `cohort_2b_fair_ood` | `v2_rf_424d_debiased` | 22380 | 0.9054 | 0.9241 | 0.8194 | 0.8089 | 0.0802 |
| `cohort_2b_fair_ood` | `v1.1_cnn` | 22380 | 0.8894 | 0.9117 | 0.7153 | 0.6163 | 0.3035 |
| `cohort_2b_fair_ood` | `v2_cnn_debiased` | 22380 | 0.8982 | 0.9181 | 0.8158 | 0.8029 | 0.1082 |
