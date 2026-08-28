# INTERN BRIEF 03 — v2 ablation (ONLY after defense job is done)

Do **not** run this in the same sitting as brief 02 unless Grok said defense passed.

Retrain **copies** under `models/v2/` only. Never overwrite `models/baseline/homology_rf.joblib` or Platt JSON.

Gate: homology **val** ROC must be ≥ locked RF **val 0.9513 + 0.01 = 0.9613** (and ECE not worse). If miss, **stop**. Do not touch test except one shot if the gate passes. Write `reports/benchmarks/v2_ablation.md` with the miss or the new number. 0.9515 stays v1.

Grok will issue a fuller script if we open this job. Until then, **do not start**.
