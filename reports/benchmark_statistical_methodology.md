# Benchmark Statistical Methodology & 5-Cohort Architecture

**Project**: AMPscan Multi-Tool Benchmark (`/home/sudheesh02/SIH TEST`)  
**Date**: August 24, 2026

---

## 1. Five Distinct Benchmarking Cohorts

1. **Cohort 1: Locked DRAMP 30% Homology Test Set (=3,230$, Balanced)**:
   - Evaluates out-of-cluster generalization on natural/curated AMP motifs under strict 30% sequence identity isolation via MMseqs2.
2. **Cohort 2: DBAASP Strict Zero-Shot Novel Scaffolds ( pprox 5,000$ Balanced)**:
   - Measures zero-shot discovery capability on synthetic de novo designs and unnatural chemical spaces (<30% ID to all training data).
3. **Cohort 3: DBAASP Near-Homolog Point Substitutions ( pprox 4,000$)**:
   - Evaluates model stability under alanine scans, point substitutions, charge reversals, and truncations.
4. **Cohort 4: Canonical Overlap Concordance ( pprox 2,350$)**:
   - Measures cross-tool consensus and detection ceiling on canonical benchmark peptides (Magainin-2, LL-37, Melittin).
5. **Cohort 5: Hemolysis & Mammalian Safety Cohort ( pprox 13,885$)**:
   - Direct head-to-head benchmarking of safety classifiers (Macrel, HemoPI, HemoPred vs AMPscan Tier 3) on host toxicity.

---

## 2. Metric Battery Formulations

- **Discrimination**: ROC-AUC, PR-AUC, Balanced Accuracy, Matthews Correlation Coefficient (MCC), Sensitivity@90% Specificity.
- **Calibration**: Expected Calibration Error (ECE_15), Maximum Calibration Error (MCE), Brier Score.
- **Efficiency**: Latency (p50, p95 ms), Throughput (sequences / second), Peak RAM/VRAM footprint.
- **Significance**: 1,000-sample Stratified Bootstrap 95% Confidence Intervals, DeLong Test, McNemar's Test.
