# AMPscan v1.0 vs other AMP tools — Cohort 1

Locked DRAMP/AMPlify homology test (`data/splits/test.fasta`), n = 3230 (1623 AMP / 1607 non-AMP). **No retraining.** Each external tool ran in its own environment; scores were joined here.

Skip rules (tool-native, not ours):

- Macrel / AMPlify: non-20 amino acids (48 sequences with X on this split).
- AmpGram: length < 10 (200 sequences) and non-20 AA.
- AI4AMP PC6: unknown letters or length > 200 (X is a valid pad token).

| model | n | skip | acc | macro-F1 | MCC | ROC-AUC | PR-AUC | ECE-15 | seq/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AMPscan RF (Platt) | 3230 | 0 | 0.8765 | 0.8765 | 0.7529 | **0.9515** | 0.9542 | 0.0235 | 28.62 |
| AMPscan 1D-CNN (T) | 3230 | 0 | 0.8650 | 0.8648 | 0.7316 | **0.9424** | 0.9465 | 0.0403 | 28.62 |
| Macrel | 3182 | 48 | 0.7854 | 0.7754 | 0.6217 | **0.9491** | 0.9503 | 0.2035 | 6601.66 |
| AI4AMP PC6 | 3230 | 0 | 0.7449 | 0.7431 | 0.4978 | **0.7905** | 0.8288 | 0.1535 | 572.49 |
| AMPlify balanced | 3182 | 48 | 0.8558 | 0.8534 | 0.7313 | **0.9277** | 0.9450 | 0.1183 | 14.88 |
| AmpGram | 3001 | 229 | 0.7234 | 0.7234 | 0.4496 | **0.7898** | 0.8265 | 0.1643 | 0.93 |

ROC figure: `01_cohort1_roc.png`.

AMPscan RF ROC-AUC **0.9515** is the locked homology-test number. Accuracy **0.8765** is Platt-calibrated RF at 0.5 (locked table 0.8734 was uncalibrated).

On this split AMPscan RF ranks first. Macrel is close on ROC (**0.949**) but conservative (acc **0.785**, ECE **0.204**). AMPlify is next (**0.928**). AI4AMP and AmpGram sit around **0.79** — usable, not competitive here.

## Separate envs (what actually broke)

- **AI4AMP**: original `requirements.txt` pins both TF 2.1 and TF-GPU 1.9. Used conda env `amp-tf` (Python 3.9, TF/Keras 2.10 CPU). Encoder imported `gensim` we did not need; adapter loads the PC6 table itself.
- **AMPlify**: advertised TF 1.12 / Python 3.6. Same `amp-tf` env loaded the five balanced `.h5` weights through the cloned custom layers. RTX 5060 is too new for TF 2.10 CUDA, so this ran on CPU (~3.5 min).
- **AmpGram**: system R could not compile `biogram` (needs `libgmp-dev`; no sudo). Conda env `amp-r` with prebuilt `r-gmp`. AmpGram's DESCRIPTION still Imports shiny/devtools; we sourced predict internals + `AmpGramModel`. 3001 peptides × 13k n-gram regexes took **~54 min**.
- **hemopi2**: hemolysis, not AMP vs non-AMP. Pickle is sklearn **1.3.1**; `amp-data` is 1.9.0 so it will not load there. Do not put it on this ROC.
- **sAMPpred-GAT**: still skipped (>100 GB DBs).

## Run log

- AMPscan RF (Platt): n=3230 skip=0 ROC-AUC=0.9515 acc=0.8765 ECE=0.0235
- AMPscan 1D-CNN (T): n=3230 skip=0 ROC-AUC=0.9424 acc=0.8650 ECE=0.0403
- Macrel: n=3182 skip=48 ROC-AUC=0.9491 acc=0.7854 ECE=0.2035
- AI4AMP PC6: n=3230 skip=0 ROC-AUC=0.7905 acc=0.7449 ECE=0.1535
- AMPlify balanced: n=3182 skip=48 ROC-AUC=0.9277 acc=0.8558 ECE=0.1183
- AmpGram: n=3001 skip=229 ROC-AUC=0.7898 acc=0.7234 ECE=0.1643

## Not in this table

- **hemopi2 / HemoPred**: hemolysis, not AMP vs non-AMP. Do not mix into this ROC.
- **zswitten Antimicrobial-Peptides**: MIC regression (GRAMPA), different label.
- **sAMPpred-GAT**: needs >100 GB BLAST/trRosetta databases. Still skipped.
- DBAASP multi-task / TSI / pathogen radar: **not trained**, not AMPscan v1.

Scripts: `scripts/benchmark/run_v1_benchmark.py` (AMPscan + Macrel), `scripts/benchmark/adapters/score_*.py|R`, `merge_external_scores.py`.
