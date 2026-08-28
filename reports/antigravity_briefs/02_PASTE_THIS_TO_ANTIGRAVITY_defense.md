# INTERN BRIEF — defense ammo + Evidence UI

Paste this whole file into Antigravity (Gemini). **Grok designed it.** Frozen weights. No TSI, no retrain, no v2 peptidy in this job.

When finished, fill `reports/antigravity_briefs/INTERN_HANDOFF_defense.md`. Do **not** overwrite `INTERN_HANDOFF.md` or `INTERN_HANDOFF_v11.md`.

---

## Why you are here

Pitch ammo, not a new model.

1. **Error analysis** — who is FP/FN on Cohort 1 at P≥0.5 (length, charge, GRAVY, μH, Cys).
2. **Operating points** — precision/recall at 0.5 / 0.8 / 0.9 / 0.95. Real screens are not 50/50.
3. **Bootstrap AUC diff** — RF vs Macrel vs AMPlify on **common IDs**. 0.951 vs 0.949 is likely a **tie**. Slide: *tied on ranking, we win calibration.*
4. **Evidence UI** — show Cohort 2b **0.903** + fragment disclaimer. Never **0.993**. Keep locked **0.9515**. Keep 0.9791 labeled as the leaky control.

**Out of this job:** peptidy/PC6 retrain (that is brief 03, later), ONNX, TSI, Macrel Hemo in the API, radar.

---

## Hard rules

1. Do **not** edit `models/`, `data/splits/train.fasta`, `val.fasta`, `test.fasta`, `scoring.py` features.
2. Do **not** add TSI / hemolysis / radar.
3. Conda: `source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh && conda activate amp-data`
4. cwd: `/home/sudheesh02/SIH TEST`
5. Do not quote 0.9935. Do not change Platt JSON.

---

## Commands

```bash
cd "/home/sudheesh02/SIH TEST"
source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh
conda activate amp-data
python scripts/benchmark/defense_error_thresholds_delong.py
```

Script is already written. If it errors, **fix the script**. Then:

```bash
cp reports/benchmarks/02b_cohort2b_roc.png frontend/public/figures/02b_cohort2b_roc.png
cp reports/benchmarks/cohort1_error_boxplots.png frontend/public/figures/cohort1_error_boxplots.png
```

---

## Evidence UI (`frontend/app/metrics/page.tsx`)

Add a fourth tab **`external`** labeled `External (2b)`. Do not remove existing tabs.

**Stats row:** keep Homology RF **0.9515**. Keep Random split **0.9791** with subtitle `do not quote · leakage`. Keep ECE. You may add a fourth stat: External 2b RF **0.903** subtitle `length-matched DBAASP · fragment negs`.

**External tab must say, verbatim meaning:**

- Locked v1 is still homology RF **0.9515**.
- Cohort 2b RF ROC-AUC **0.903** (n = 22380, 11190 vs 11190, length median 14 vs 14).
- Negatives are **windows from unused long UniProt-style chains**, not assayed non-AMPs.
- Do **not** quote the length-confounded 0.993 table.
- At P≥0.5 on 2b, accuracy is **0.645** and ECE **0.28** — Platt does not transfer; quote ROC.
- Ranking vs Macrel on 2b is a **tie** (~0.90).

Show `02b_cohort2b_roc.png` in that tab.

**Models tab:** under the locked ROC, add 2–4 lines from `defense_ammo.md`: operating points for **AMPscan RF** at 0.5 and 0.9, and the RF-vs-Macrel bootstrap sentence (CI includes 0 or not — use the JSON, do not invent).

Keep dark theme. No “phase” coaching. No TSI.

If the Next server is not running, do not spend the job starting it. Grok will look at the file.

---

## Done when

- [ ] `reports/benchmarks/defense_ammo.md` exists
- [ ] `operating_points.csv`, `delong_bootstrap_auc.json`, error CSVs + boxplot exist
- [ ] Evidence has External tab + 0.903 + fragment disclaimer; 0.9515 still the first stat
- [ ] `INTERN_HANDOFF_defense.md` quotes the RF-vs-Macrel CI and whether it excludes 0
- [ ] no retrain, no TSI, 2b/v1.1 handoffs untouched
