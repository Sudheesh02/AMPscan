# INTERN BRIEF v1.1 — paste this whole file into Antigravity (Gemini)

You are a careful intern. **Grok already designed v1.1.** Run the scripts, make the small UI edit, fill the handoff. Do **not** invent science.

Parent plan: `reports/architecture_lessons_and_selective_upgrade_plan.md`.

When finished, fill `reports/antigravity_briefs/INTERN_HANDOFF_v11.md` (do **not** overwrite `INTERN_HANDOFF.md` from Cohort 2b).

---

## Why you are here

AMPscan already **matches Macrel on ROC** (0.9515 vs 0.949) and **beats everyone on calibration** (ECE 0.023). We are not copying BiLSTM/PC6/TSI.

v1.1 is **engineering on frozen weights**:

1. Batch scoring (Python `for seq` is why 18k peptides took ~30 min). `featurize_many` already exists in `scripts/run_baseline.py`. RF `n_jobs` is already 4. GPU will **not** speed the RF. Honest target: **3–8×** on Cohort 1 test (`n=3230`), not “45 seconds on the 5060.”
2. Protein **scanner** using the **locked RF**, AmpGram-style windows, for sequences **>100 aa**.
3. One sentence on Classify: P≥0.5 does **not** transfer to short DBAASP OOD (Cohort 2b acc 0.65, ECE 0.28).

Locked headline remains Cohort 1 RF ROC-AUC **0.9515**.

---

## Hard rules

1. Do **not** edit `models/`, `data/splits/train.fasta`, `val.fasta`, `test.fasta`.
2. Do **not** change the 425-D feature layout in `services/predict_api/scoring.py`. You may **import** `featurize_one` / `featurize_many` / `get_artifacts`. Do not add peptidy/PC6 columns.
3. Do **not** add TSI, hemolysis, radar, or Macrel Hemo to the API.
4. Do **not** retrain. Do not quote 0.9935.
5. Batched RF/CNN probabilities on `data/splits/test.fasta` must match `reports/benchmarks/cohort_1_ampscan_scores.csv` within **1e-5** abs (same Platt / T).
6. Conda: `source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh && conda activate amp-data`.
7. Work in `/home/sudheesh02/SIH TEST`.

---

## What to run (in order)

```bash
cd "/home/sudheesh02/SIH TEST"
source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh
conda activate amp-data

python scripts/benchmark/score_ampscan_batched.py \
  --fasta data/splits/test.fasta \
  --out reports/benchmarks/cohort_1_ampscan_batched_scores.csv \
  --verify reports/benchmarks/cohort_1_ampscan_scores.csv \
  --speed-md reports/benchmarks/batch_scoring_speed.md

python scripts/scan_protein.py \
  --fasta data/splits/test.fasta \
  --window 25 --step 5 \
  --out reports/benchmarks/scan_smoke_test.csv
```

`--window 25 --step 5` on peptides 5–100 is a **smoke test** (many sequences will skip as shorter than the window). That is OK. Then run once on a **long** protein if you have one; otherwise document “no >100 aa FASTA in splits; smoke test only.”

Do **not** rescore Cohort 2b (22k) unless batch verify passed and you have time. Optional: batched RF only on `data/splits/dbaasp_ood/cohort2b_fair.fasta` to show speed — **do not** replace 2b metrics.

---

## UI edit (one sentence)

File: `frontend/app/predict/page.tsx`

In the “Trust this number.” paragraph (around the P ≥ 0.5 sentence), **append** this exact meaning, short:

> The 0.5 cut was fit on our DRAMP vs AMPlify homology test. On shorter external peptides it can over-call AMP; ranking (ROC) still holds, calibration may not.

Do not add TSI, hemolysis, or “phase” coaching. Keep dark theme. Do not change IG copy except if you must wrap lines.

---

## Scripts already written for you

| file | job |
| --- | --- |
| `scripts/benchmark/score_ampscan_batched.py` | vectorized RF + batched CNN; verify vs locked CSV; write speed note |
| `scripts/scan_protein.py` | sliding-window locked RF; `SRC=SCAN`; never call the whole protein AMP |

If a script errors, **fix the script**. Do not change Platt JSON or the forest.

---

## Done when

- [ ] `cohort_1_ampscan_batched_scores.csv` exists; max |Δp_rf| and |Δp_cnn| vs locked CSV **< 1e-5**
- [ ] `batch_scoring_speed.md` reports seq/s sequential vs batched and a **factor**. Factor should be >1. If <1, you broke something — stop.
- [ ] `scan_protein.py --help` works; smoke CSV written; header/docs say **window scores, not protein AMP**
- [ ] Classify page has the 0.5-transfer sentence
- [ ] `INTERN_HANDOFF_v11.md` filled
- [ ] no TSI, no retrain, no 0.9515 change

## Out of scope (Grok / later)

Architecture comparison report (`architecture_comparison_v1.md`), peptidy/PC6 v2 ablation, ONNX export, Macrel Hemo in the API.
