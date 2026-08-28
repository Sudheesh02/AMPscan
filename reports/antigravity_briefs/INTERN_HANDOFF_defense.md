# Intern handoff — defense ammo (Antigravity fills this)

- **Date**: 2026-08-24
- **Commands run**:
  1. `python scripts/benchmark/defense_error_thresholds_delong.py` (in `amp-data`)
  2. `cp reports/benchmarks/02b_cohort2b_roc.png frontend/public/figures/02b_cohort2b_roc.png`
  3. `cp reports/benchmarks/cohort1_error_boxplots.png frontend/public/figures/cohort1_error_boxplots.png`
- **FN / FP counts at P≥0.5 (RF)**:
  - FN = 195 (out of 1623 true AMPs)
  - FP = 204 (out of 1607 true non-AMPs)
  - TN = 1403, TP = 1428 (Total N = 3230)
- **FN vs TP: median charge, GRAVY, length (one line)**:
  - FN: median len **38 aa**, median charge **0.00**, median GRAVY **-0.31**, median μH **0.13**, mean Cys **1.95** vs TP: median len **18 aa**, median charge **+3.00**, median GRAVY **-0.03**, median μH **0.32**, mean Cys **0.99** (missed AMPs are longer, non-cationic, less amphipathic peptides with higher disulfide/cysteine content).
- **RF precision/recall at 0.5 and 0.9 (Cohort 1)**:
  - At P ≥ 0.50: precision **0.875**, recall **0.880**, specificity **0.873** (1632 called AMP)
  - At P ≥ 0.90: precision **0.974**, recall **0.635**, specificity **0.983** (1059 called AMP)
- **RF vs Macrel: ΔAUC, 95% CI, ci_excludes_0**:
  - ΔAUC = **+0.0014**, 95% boot CI **[-0.0049, +0.0075]**, `ci_excludes_0`: **False** (n=3182 common IDs).
  - Scientific defense: *Tied on discriminative ranking (CI includes 0); AMPscan cleanly wins probability calibration (ECE 0.023 vs 0.204).*
- **Evidence: External tab present? 0.903 shown? 0.993 absent? 0.9515 still first stat?**:
  - **Yes**: `External (2b)` tab added to `frontend/app/metrics/page.tsx`.
  - **Yes**: 0.903 shown with explicit fragment non-AMP disclaimer (`n=22380`, 11190 vs 11190, length median 14 vs 14).
  - **Yes**: 0.993 table absent (explicitly flagged as length-confounded, not to quote).
  - **Yes**: Homology RF 0.9515 is strictly maintained as the first and primary stat card.
- **Confirmations**:
  - ✅ Did **NOT** retrain any models (all weights frozen).
  - ✅ Did **NOT** add TSI, hemolysis ratios, or fake radars to the API.
  - ✅ Did **NOT** overwrite `INTERN_HANDOFF.md` or `INTERN_HANDOFF_v11.md`.
