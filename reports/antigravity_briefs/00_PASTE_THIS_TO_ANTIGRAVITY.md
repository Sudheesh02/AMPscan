# INTERN BRIEF — paste this whole file into Antigravity (Gemini)

You are a careful intern. **Grok already designed the experiment.** Your job is to **run the scripts, not invent science.** Do not retrain AMPscan. Do not add TSI, peptidy features, PC6 channels, pathogen radar, or hemolysis to the API.

When finished, write `reports/antigravity_briefs/INTERN_HANDOFF.md` with what you ran, file paths, numbers, and anything that failed.

---

## Why you are here (read this)

Cohort 2 DBAASP OOD was built and scored, but **it is not a fair test**.

- DBAASP novel AMPs: median length **14 aa**
- Negatives we could find: median length **76 aa**
- Full-set AMPscan RF ROC **0.9935** is **length-confounded**. Do **not** quote it as better than locked **0.9515**.
- Fair slice (balanced, length ≤30) was only **302 vs 302**, RF ROC **0.942**.
- Intact unused short non-AMPs on disk: only **~395** sequences of length 5–30 (`data/processed/negatives_alphabet.fasta` minus train/val/test). After MMseqs walls we kept **302**. There are **not** enough real short non-AMP peptides left in this repo.

**Your upgrade:** make **fragment non-AMPs** from unused *long* negatives that already pass the 30% wall vs train, length-match them to DBAASP, re-score **frozen** tools, write a **fair** Cohort 2b table.

Locked AMPscan v1 number remains Cohort 1 RF ROC-AUC **0.9515**.

---

## Hard rules

1. Do **not** edit `models/`, `data/splits/train.fasta`, `val.fasta`, `test.fasta`, or `services/predict_api/scoring.py` feature layout.
2. Do **not** ship TSI = P(AMP)/(P(Hemo)+1e-4). Grok rejected it.
3. Do **not** use train / val / test sequences as Cohort 2 labels (no leakage from Cohort 1).
4. Fragment negatives must be labeled `SRC=FRAGMENT_NEG` in FASTA headers. Never call them “experimentally inactive.”
5. Same MMseqs settings as the locked split: `--min-seq-id 0.3 -c 0.8 --cov-mode 1`.
6. Conda: `amp-data` (AMPscan, Macrel, mmseqs), `amp-tf` (AI4AMP, AMPlify). Skip AmpGram unless the fair set is ≤4000 sequences (too slow).
7. Work in `/home/sudheesh02/SIH TEST`. Activate conda with:
   `source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh && conda activate amp-data`

---

## What to run (in order)

```bash
cd "/home/sudheesh02/SIH TEST"
source /home/sudheesh02/miniforge3/etc/profile.d/conda.sh
conda activate amp-data

# 1) harvest short fragment negatives + rebuild length-matched Cohort 2b
python scripts/benchmark/rebuild_cohort2_fair.py

# 2) score AMPscan RF/CNN + Macrel
python scripts/benchmark/run_cohort2_fair_score.py

# 3) score AI4AMP
conda activate amp-tf
export TF_CPP_MIN_LOG_LEVEL=2 CUDA_VISIBLE_DEVICES=
export AMP_BENCH_FASTA="/home/sudheesh02/SIH TEST/data/splits/dbaasp_ood/cohort2b_fair.fasta"
export AMP_BENCH_OUT="/home/sudheesh02/SIH TEST/reports/benchmarks/cohort_2b_ai4amp_scores.csv"
export AMP_BENCH_META="cohort2b_ai4amp_meta.txt"
python scripts/benchmark/adapters/score_ai4amp.py

# 4) score AMPlify
export AMP_BENCH_OUT="/home/sudheesh02/SIH TEST/reports/benchmarks/cohort_2b_amplify_scores.csv"
export AMP_BENCH_META="cohort2b_amplify_meta.txt"
python scripts/benchmark/adapters/score_amplify.py

# 5) write the fair report (amp-data)
conda activate amp-data
python scripts/benchmark/report_cohort2_fair.py
```

If a script errors, **fix the script**, do not silently skip a homology wall.

---

## Science you must keep in the report

Say this in `reports/benchmarks/cohort_2b_fair_results.md`:

- Cohort 2b negatives are **windows cut from unused long UniProt-style non-AMPs**, not assayed non-AMPs.
- They are length-matched to DBAASP novels and `<30%` ID to train **and** to DBAASP novels.
- Primary table = **length-matched** set (target 1:1 if possible).
- Put the old 0.993 table in an appendix titled **length-confounded, do not quote**.
- Compare ROC to Cohort 1 0.9515 as a **second** number, not a replacement.

Success = `n_neg` in the same length band as DBAASP (median within ~5 aa of 14, and at least **2000** negatives of length 5–30 after walls). If you cannot hit 2000, stop and write why in the handoff — do not pad with long sequences.

---

## Files you may write / overwrite

- `data/splits/dbaasp_ood/cohort2b_fair.fasta`
- `data/splits/dbaasp_ood/cohort2b_index.csv`
- `data/splits/dbaasp_ood/cohort2b_meta.json`
- `reports/benchmarks/cohort_2b_*.csv`
- `reports/benchmarks/cohort_2b_fair_results.md`
- `reports/benchmarks/02b_cohort2b_roc.png`
- `reports/antigravity_briefs/INTERN_HANDOFF.md`

Do not overwrite `cohort_2_dbaasp_ood_results.md` (that documents the confound).

---

## Done when

- [ ] `cohort2b_fair.fasta` exists, sha256 in meta
- [ ] length median pos vs neg differ by **≤ 8 aa**
- [ ] AMPscan RF + CNN + Macrel + AI4AMP + AMPlify scored
- [ ] report states fragment-neg limitation in the first screen
- [ ] `INTERN_HANDOFF.md` lists commands, wall times, and the fair ROC table
- [ ] no TSI, no retrain, no 0.993 as headline
