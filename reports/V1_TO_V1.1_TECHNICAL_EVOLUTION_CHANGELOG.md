# AMPscan: v1.0 to v1.1 Technical Evolution & Scientific Changelog

---

## 1. Executive Summary

AMPscan v1.0 established the locked machine learning baseline: 21,337 clean peptides, MMseqs2 30% identity clustering, a 425-D Random Forest with Platt calibration achieving **0.9515 ROC-AUC / 0.0235 ECE**, and a secondary 1D-CNN with Integrated Gradients attribution.

**AMPscan v1.1 is an engineering, benchmarking, and user-experience upgrade on frozen model weights**:
- Zero retraining of primary weights (`homology_rf.joblib`, `homology_cnn1d.pt`).
- Zero changes to locked baseline metrics (0.9515 ROC-AUC, 0.0235 ECE).
- Complete expansion into high-throughput batching, whole-protein sliding scanning, sub-millisecond nearest-neighbor search, SOTA multi-tool empirical benchmarks, length-matched external DBAASP validation, and a flagship Next.js 14 web workbench.

```
========================================================================================================================
                                   AMPSCAN SYSTEM ARCHITECTURE EVOLUTION
========================================================================================================================

   ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
   │                                           AMPSCAN v1.0 BASELINE                                             │
   │  • 21,337 Clean Peptides (DRAMP + AMPlify)        • MMseqs2 30% Identity Cluster Split (70/15/15)          │
   │  • 425-D Feature Random Forest (Platt Calibrated) • Homology ROC-AUC: 0.9515 (Random Leakage Control: 0.9791)  │
   │  • Local Offline Streamlit App (Single/Slow Loop) • Basic 1D-CNN (Temperature Scaled) + Captum IG Heatmaps  │
   └──────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                                          │
                              UPGRADE VECTOR: STRICT ENGINEERING ON FROZEN WEIGHTS
                                (No retrain, no fake metrics, zero scientific leakage)
                                                          │
                                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
   │                                         AMPSCAN v1.1 PRODUCTION SUITE                                       │
   ├──────────────────────────────────────────────┬──────────────────────────────────────────────────────────────┤
   │             HIGH-THROUGHPUT ENGINE           │                   FULL-STACK WORKBENCH                       │
   │  • Vectorized Batching: POST /predict-batch  │  • Next.js 14 Production App (App Router + Tailwind)        │
   │    (Cap 500, 157.77× speedup, 4,335.76 seq/s)│  • In Silico Point-Mutation Studio (Live IG Recompute)      │
   │  • Sliding-Window Scanner: POST /scan        │  • Evidence Evaluation Dashboard (Multi-Tool Comparisons)    │
   │    (Up to 5,000 aa, LL-37 hCAP-18 validated) │  • Multi-FASTA Drag-and-Drop Batch Manager                   │
   │  • TrainIndex Sub-ms Nearest-Neighbor Engine │  • Calibrated Uncertainty Triage (P >= 0.90 -> 97.4% Prec)   │
   │    (14,904 peptides, uint8 bucketed, <3ms)   │  • Dark / Bio-Luminescent Clinical Theme                    │
   ├──────────────────────────────────────────────┴──────────────────────────────────────────────────────────────┤
   │                                  COMPREHENSIVE SCIENTIFIC BENCHMARKS                                        │
   │  • SOTA 10-Tool Empirical Evaluation (Cohort 1, N=3,230):                                                   │
   │    - Paired bootstrap vs Macrel (ROC 0.9515 vs 0.9491, tie; AMPscan wins ECE 0.023 vs 0.204)                │
   │    - Paired bootstrap vs AMPlify (ROC 0.9515 vs 0.9277, stat. significant win: Delta +0.0228, CI [0.013, 0.032])│
   │  • Length-Matched DBAASP OOD Validation (Cohort 2b, N=22,380):                                              │
   │    - Exact median 14 aa length match; Cross-tool tie at ~0.90 ROC (AMPscan 0.9030, Macrel 0.8998)          │
   │    - Honest audit: Rejection of length-confounded 0.9935 table; Platt calibration transfer limits documented│
   └─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Comprehensive Comparative Matrix

| Feature / Capability | AMPscan v1.0 | AMPscan v1.1 |
| :--- | :--- | :--- |
| **User Interface** | Local Streamlit script (`app/streamlit_app.py`). Single sequence inputs, blocking execution. | Flagship Next.js 14 App Router UI (`frontend/`, port 3000) with *in silico* point mutations, Evidence Dashboard, and dark/light themes. Streamlit kept as offline fallback. |
| **Inference Throughput** | Sequential Python `for` loops (~27.5 seq/s). | Vectorized NumPy feature matrix extraction + scikit-learn batch evaluation (`POST /predict-batch`, cap 500) executing at **4,335.76 seq/s (157.77× speedup)**. |
| **Long Sequence Support** | Rejected sequences $>100$ aa with error. | Sliding-window scanner (`POST /scan`) supporting proteins up to **5,000 aa** (cap 2,000 windows) with explicit domain disclaimer (`protein_level_call: false`). |
| **Memorization Guard** | Hardcoded 3-item check (`magainin-2`, `LL-37`, `melittin`). | In-memory `TrainIndex` indexing **all 14,904 training peptides** in length-stratified uint8 ASCII matrices for sub-millisecond ($<3\text{ ms}$) nearest-neighbor lookups. |
| **SOTA Multi-Tool Benchmark** | Internal model comparison only. | 10-tool comparative landscape + empirical 5-tool evaluation on Cohort 1 ($N=3,230$) with 2,000-resample paired bootstrap confidence intervals vs Macrel, AMPlify, AI4AMP, AmpGram. |
| **External OOD Validation** | Unvalidated externally. | Rigorous length-matched DBAASP validation on Cohort 2b ($N=22,380$, ROC 0.9030), explicitly debunking the length-confounded 0.9935 table. |
| **Translational Triage** | Fixed threshold at 0.50. | Calibrated operating points established ($P \ge 0.90$ providing **97.4% precision** and **98.3% specificity**). |
| **API Contract & Testing** | Informal documentation. | Formal API Contract (`services/predict_api/API_CONTRACT.md`) and automated smoke test suite (`scripts/smoke_api_v11.py`). |

---

## 3. Detailed Upgrade Logs: WHAT, WHERE, and WHY

### Upgrade 1: Next.js 14 Scientific Workbench & In Silico Mutation Studio
- **WHAT Changed**: Built a production Next.js 14 App Router web platform. Added an interactive *in silico* point-mutation workbench (click any residue in the Integrated Gradients track to mutate it into any of the 20 standard amino acids, recalculating $P(\text{AMP})$ and 425-D properties live), an Evidence Dashboard with 4 tabbed panels, and multi-FASTA batch support.
- **WHERE Changed**: `frontend/app/predict/page.tsx`, `frontend/app/metrics/page.tsx`, `frontend/lib/api.ts`, `frontend/lib/sequence.ts`.
- **WHY It Changed**:
  - *Scientific Rationale*: Preclinical peptide engineering requires lead optimization. Biologists need to test specific amino acid substitutions (e.g. adding cationic or hydrophobic residues) to observe predicted potency changes while monitoring physicochemical balance (charge, GRAVY, hydrophobic moment).
  - *Engineering Rationale*: Streamlit re-runs the entire Python script on every click. Next.js 14 provides client-side reactivity, optimistic updates, and decoupled rendering.

### Upgrade 2: Vectorized Batch Inference Engine (`POST /predict-batch`, Cap 500)
- **WHAT Changed**: Replaced single-item inference loops with vectorized NumPy matrix featurization (`featurize_many`) and batched PyTorch CNN evaluation, boosting throughput by **157.77×** (from 27.5 to **4,335.76 seq/s**). Verified numerical score deviation $< 10^{-7}$ against locked weights.
- **WHERE Changed**: `services/predict_api/main.py`, `services/predict_api/scoring.py`, `scripts/benchmark/score_ampscan_batched.py`.
- **WHY It Changed**:
  - *Scientific Rationale*: Screening large combinatorial libraries or metagenomic small open reading frames (smORFs) requires evaluating thousands of peptides in seconds.
  - *Engineering Rationale*: Eliminates Python loop overhead and GIL contention through contiguous C-array allocations and parallel SIMD vectorization.

### Upgrade 3: Sliding-Window Protein Scanner (`POST /scan`)
- **WHAT Changed**: Added a sliding-window scanning engine capable of scanning proteins up to 5,000 aa using the locked Random Forest. Tested on 170-aa human cathelicidin precursor (hCAP-18), successfully pinpointing the cleaved active LL-37 domain (residues 134–170, $P > 0.99$).
- **WHERE Changed**: `services/predict_api/main.py`, `services/predict_api/scoring.py`, `scripts/scan_protein.py`.
- **WHY It Changed**:
  - *Scientific Rationale*: Natural AMPs are often expressed as inactive pro-proteins requiring cleavage. Scanning identifies localized active domains within full-length precursors.
  - *Engineering Rationale*: Whole-protein prediction requires distinct annotation heads. Providing a sliding-window scanner with explicit domain disclaimers maintains strict mathematical domain validity.

### Upgrade 4: Sub-Millisecond Nearest-Neighbor Index (`TrainIndex`, 14.9k Sequences)
- **WHAT Changed**: Created an in-memory database of all 14,904 training peptides stored as length-stratified uint8 ASCII NumPy matrices, providing exact $O(1)$ hash checks and ungapped identity searches across $|\Delta L| \le 2$ in $<3\text{ ms}$.
- **WHERE Changed**: `services/predict_api/scoring.py`, `services/predict_api/main.py`.
- **WHY It Changed**:
  - *Scientific Rationale*: Prevents false claims where users paste textbook AMPs (e.g. Magainin-2) and mistake training set recall for true de novo generalization.
  - *Engineering Rationale*: Avoids spawning heavy alignment tools (BLAST/MMseqs2) during HTTP requests by running fast vectorized broadcast character comparisons in RAM.

### Upgrade 5: Multi-Tool SOTA Benchmark & Statistical Significance Evaluation
- **WHAT Changed**: Evaluated 5 external tools (Macrel, AMPlify, AI4AMP, AmpGram, and classical baselines) on the locked Cohort 1 test set ($N=3,230$). Ran 2,000-resample paired bootstrap tests proving a ranking tie with Macrel ($\Delta\text{ROC} = +0.0014$, 95% CI $[-0.0049, +0.0075]$) with a 10-fold calibration win (ECE 0.023 vs 0.204), and a statistically significant win over AMPlify ($\Delta\text{ROC} = +0.0228$, 95% CI $[0.0127, 0.0324]$).
- **WHERE Changed**: `reports/benchmarks/AMPscan_v1.0_benchmark_report.md`, `reports/benchmarks/delong_bootstrap_auc.json`, `reports/benchmarks/defense_ammo.md`.
- **WHY It Changed**:
  - *Scientific Rationale*: Claims of state-of-the-art performance require head-to-head empirical testing on identical holdout sets with non-parametric bootstrap confidence intervals.

### Upgrade 6: Cohort 2b Fair Length-Matched DBAASP External OOD Validation
- **WHAT Changed**: Evaluated locked models on $N=22,380$ length-matched DBAASP synthetic peptides (14 aa pos vs 14 aa neg fragments), achieving **0.9030 ROC-AUC**. Audited and debunked the unconstrained 0.9935 table due to length confounding (14 aa vs 76 aa). Documented that Platt calibration parameters do not transfer directly to short fragment backgrounds ($P \ge 0.5$ acc is 0.645), requiring threshold triage ($P \ge 0.90 \to 97.4\%$ precision).
- **WHERE Changed**: `reports/benchmarks/cohort_2b_fair_results.md`, `services/predict_api/locked_metrics.py`, `frontend/app/metrics/page.tsx`.
- **WHY It Changed**:
  - *Scientific Rationale*: Enforcing a strict median length gap of 0 residues eliminates length artifacts and measures genuine biochemical generalization.

### Upgrade 7: Automated Smoke Test Suite & Production API Contract
- **WHAT Changed**: Created `scripts/smoke_api_v11.py` covering 11 automated integration tests (health, metrics constants, Magainin-2 recall, batch scoring parity, sliding-window scan on hCAP-18, and sub-ms TrainIndex latency). Formalized `services/predict_api/API_CONTRACT.md`.
- **WHERE Changed**: `scripts/smoke_api_v11.py`, `services/predict_api/API_CONTRACT.md`.
- **WHY It Changed**:
  - *Engineering Rationale*: Ensures zero regressions across model paths, metric values, and API routes before live demonstrations.

---

## 4. Deliberately Rejected Proposals (What We Refused to Build)

1. **No Therapeutic Selectivity Index ($TSI = P(\text{AMP}) / [P(\text{Hemo}) + \epsilon]$)**: Dividing uncalibrated probabilities from models trained on disparate datasets produces mathematically meaningless pseudo-metrics.
2. **No Fake Pathogen Radar Charts**: DBAASP tag annotations are sparse and non-exhaustive; multi-class pathogen heads without negative experimental confirmation produce false confidence.
3. **No Retraining on DBAASP while quoting 0.9515**: Combining test datasets into training destroys the locked homology-held-out baseline.
4. **No Deep Learning / LoRA Bloat for the Demo**: ESM-2 150M tied the Random Forest on homology test ($0.9521$ vs $0.9515$, $\Delta = +0.0006$) while requiring heavy GPU memory and failing the validation gate ($0.9372$). The Random Forest runs instantly on standard CPU hardware.
