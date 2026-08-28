# Intern handoff (Antigravity fills this)

- **Date**: 2026-08-24
- **Model used**: Antigravity / Gemini 3.7
- **Commands actually run**:
  1. `python scripts/benchmark/rebuild_cohort2_fair.py` (in `amp-data`)
  2. `python scripts/benchmark/run_cohort2_fair_score.py` (in `amp-data`)
  3. `TF_CPP_MIN_LOG_LEVEL=2 CUDA_VISIBLE_DEVICES= AMP_BENCH_FASTA=".../cohort2b_fair.fasta" AMP_BENCH_OUT=".../cohort_2b_ai4amp_scores.csv" AMP_BENCH_META="cohort2b_ai4amp_meta.txt" python scripts/benchmark/adapters/score_ai4amp.py` (in `amp-tf`)
  4. `TF_CPP_MIN_LOG_LEVEL=2 CUDA_VISIBLE_DEVICES= AMP_BENCH_FASTA=".../cohort2b_fair.fasta" AMP_BENCH_OUT=".../cohort_2b_amplify_scores.csv" AMP_BENCH_META="cohort2b_amplify_meta.txt" python scripts/benchmark/adapters/score_amplify.py` (in `amp-tf`)
  5. `python scripts/benchmark/report_cohort2_fair.py` (in `amp-data`)
- **`cohort2b_fair.fasta` sha256**: `f21747c7c69c906625f8998e87e5d6795d1a0171de13d5084a137667c0b528c2`
- **n_pos / n_neg / pos_len_median / neg_len_median / gap**:
  - `n_pos`: 11,190
  - `n_neg`: 11,190
  - `pos_len_median`: 14
  - `neg_len_median`: 14
  - `gap`: 0 aa (perfect length match; mean pos 15.99 vs mean neg 15.92)
- **n_neg_fragment / n_neg_intact**:
  - `n_neg_fragment`: 11,012
  - `n_neg_intact`: 178
- **Fair ROC table (from `reports/benchmarks/cohort_2b_fair_results.md`)**:

| model | n | skip | acc | MCC | ROC-AUC | PR-AUC | ECE-15 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **AMPscan RF (Platt)** | 22380 | 0 | 0.6449 | 0.3765 | **0.9030** | 0.9205 | 0.2767 |
| **AMPscan 1D-CNN (T)** | 22380 | 0 | 0.6162 | 0.3235 | **0.8894** | 0.9117 | 0.3044 |
| **Macrel** | 20426 | 1954 | 0.8222 | 0.6554 | **0.8998** | 0.9017 | 0.1058 |
| **AMPlify balanced** | 20426 | 1954 | 0.8216 | 0.6421 | **0.8991** | 0.9075 | 0.0867 |
| **AI4AMP PC6** | 22380 | 0 | 0.8081 | 0.6287 | **0.8786** | 0.9031 | 0.0870 |

- **Failures / skipped tools**:
  - Macrel and AMPlify skipped 1,954 sequences that contain non-standard amino acid letters / D-aa artifacts.
  - AmpGram was skipped due to execution time on 22k sequences.
  - Zero failures across all other tools.
- **Confirmations**:
  - ✅ **Did NOT retrain** any models (all models evaluated frozen).
  - ✅ **Did NOT add TSI** or any uncalibrated ratio formulas to the API.
  - ✅ **Did NOT quote 0.9935** as the headline metric (locked headline remains Cohort 1 RF ROC-AUC **0.9515**).
  - ✅ All fragment negatives are labeled `SRC=FRAGMENT_NEG` in FASTA headers and documented as windows cut from unused long UniProt-style non-AMPs, not assayed inactives.
