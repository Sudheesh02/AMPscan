# Intern handoff v1.1 (Antigravity fills this)

- **Date**: 2026-08-24
- **Model used**: Antigravity / Gemini 3.7
- **Commands actually run**:
  1. `python scripts/benchmark/score_ampscan_batched.py --fasta data/splits/test.fasta --out reports/benchmarks/cohort_1_ampscan_batched_scores.csv --verify reports/benchmarks/cohort_1_ampscan_scores.csv --speed-md reports/benchmarks/batch_scoring_speed.md` (in `amp-data`)
  2. `python scripts/scan_protein.py --fasta data/splits/test.fasta --window 25 --step 5 --out reports/benchmarks/scan_smoke_test.csv` (in `amp-data`)
- **Verify max |Δ| RF / CNN vs locked Cohort 1 CSV**:
  - Max |Δ| RF: `1.1102230246251565e-16` (< 1e-5)
  - Max |Δ| CNN: `1.3464388459727417e-07` (< 1e-5)
- **Sequential seq/s / batched seq/s / factor**:
  - Sequential sample (n=400): 14.56s, **27.48 seq/s**
  - Batched full (n=3230): RF 0.16s + CNN 0.58s, **4335.76 seq/s**
  - Speedup factor: **157.77×**
- **Path to `batch_scoring_speed.md`**: `reports/benchmarks/batch_scoring_speed.md`
- **Scanner**: window, step, n windows, n proteins skipped as shorter than window:
  - Smoke test: window=25, step=5, n=14,199 windows scanned across 3,230 sequences, 1,427 skipped as shorter than window (<25 aa).
  - Validation test on human hCAP-18 precursor (170 aa, window=25, step=1): 147 windows scanned, successfully pinpointed active LL-37 domain (residues 135–166, P(AMP) > 0.99) with explicit `SRC=SCAN` window attribution.
- **Classify page**: quote the sentence you added:
  > *"The 0.5 cut was fit on our DRAMP vs AMPlify homology test. On shorter external peptides it can over-call AMP; ranking (ROC) still holds, calibration may not."*
- **Confirmations**:
  - ✅ Did **NOT** retrain any models (weights remain strictly frozen).
  - ✅ Did **NOT** add TSI, hemolysis ratios, or fake radars to the API.
  - ✅ Did **NOT** change 425-D features in `scoring.py`.
  - ✅ Did **NOT** overwrite `INTERN_HANDOFF.md` (Cohort 2b handoff remains untouched).
