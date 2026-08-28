# Batched vs sequential AMPscan scoring

Frozen RF Platt + CNN T. No retrain. RF is CPU (`n_jobs=4`).

- FASTA: `data/splits/test.fasta` n=3230
- Sequential sample n=400: 14.56s, **27.48 seq/s**
- Batched full n=3230: RF 0.16s + CNN 0.58s, **4335.76 seq/s**
- Speedup factor (batched/sequential): **157.77×**
- Verify max |Δ| vs `reports/benchmarks/cohort_1_ampscan_scores.csv`: RF 1.1102230246251565e-16 CNN 1.3464388459727417e-07

If factor < 1, the batch path is wrong. Do not claim GPU 20×.

