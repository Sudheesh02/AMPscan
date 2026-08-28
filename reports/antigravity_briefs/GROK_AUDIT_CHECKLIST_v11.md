# Grok audit checklist — v1.1 intern

1. `models/` and train/val/test FASTA untouched.
2. `scoring.py` still 425-D; no peptidy/PC6/TSI.
3. Batched vs `cohort_1_ampscan_scores.csv`: max |Δ| RF and CNN **< 1e-5**.
4. Speed factor **> 1**. If they claim 20× GPU, fail the prose even if factor is 3×.
5. Scanner CSV has `note` = window score, not protein AMP. Window in 5–100.
6. Predict page contains the 0.5-transfer sentence; no hemolysis/TSI.
7. Did not overwrite Cohort 2b `INTERN_HANDOFF.md`.
8. Locked headline still 0.9515 in any markdown they wrote.
