# Grok audit of the Antigravity AMPscan Pro roadmap

Date: 2026-08-24. Cohort 1 numbers below are from `reports/benchmarks/cohort_1_metrics.csv` unless noted.

## Verdict in one line

Cohort 1 ranking is **mostly right** (with caveats). DBAASP as a **separate** `<30%` + negatives table is the **correct** next experiment. The proposed **TSI formula is not sound** for triage. peptidy/PC6 **without retraining** does nothing; **with retraining** it breaks the locked 0.9515 model.

Do **Cohort 2 OOD** next. Do **not** ship TSI / peptidy / PC6-channel CNN into the demo until those are trained **and** tested on hemolysis or a new locked split.

---

## 1. Does Cohort 1 ranking reflect homology-isolated generalization?

**Mostly yes for ranking, no for some of the prose.**

Measured on the same locked `data/splits/test.fasta` (n = 3230; Macrel/AMPlify skip 48 X-seqs):

| model | ROC-AUC | acc | ECE-15 | notes |
| --- | ---: | ---: | ---: | --- |
| AMPscan RF Platt | 0.9515 | 0.8765 | 0.0235 | locked headline |
| AMPscan ESM-2 150M linear | 0.9521 | 0.8762 | **not measured** | Phase 9 test; **not** in Cohort 1 score CSV |
| AMPscan 1D-CNN T | 0.9424 | 0.8650 | 0.0403 | |
| Macrel | 0.9491 | 0.7854 | 0.2035 | skip 48 |
| AMPlify balanced | 0.9277 | 0.8558 | 0.1183 | skip 48 |
| AI4AMP PC6 | 0.7905 | 0.7449 | 0.1535 | |
| AmpGram | 0.7898 | 0.7234 | 0.1643 | skip 229; **omitted from their table** |

What is fair:

- Homology isolation is real (MMseqs 30% / 80% shorter coverage, cluster split). RF 0.9515 vs random-split **0.9791** is the leakage gap. Quote 0.9515, not 0.98.
- Calibration gap vs Macrel is the actual win (ECE 0.023 vs 0.204), not a 0.002 ROC gap.
- AMPlify 0.928 on **our** split is a real drop vs their paper numbers. That is homology + different negatives, not “AMPlify is broken.”

What the Antigravity writeup gets wrong:

- **“Zero leakage”** — false. `reports/mixed_clusters.md`: **72 mixed AMP/non-AMP clusters**. The wall is 30%, not biological independence.
- **ESM-2 150M ECE 0.0310 and 45 seq/s** — not in `reports/calibration/metrics.csv` (that file has RF, CNN, ESM-**35M** only). ROC 0.9521 / acc 0.8762 **are** real from Phase 9. Do not invent ECE/throughput.
- **“AI4AMP overfits our training clusters”** — we never scored AI4AMP on *their* train vs *our* test. 0.7905 means their PC6 model, trained on a different corpus, does not transfer. That is domain shift, not a proven overfit to DRAMP clusters.
- **Macrel “overprediction at 0.5”** — Macrel is **conservative** on this split (FP 22, FN 661), not over-calling AMP. High ECE + low accuracy is **under-calling** AMPs at 0.5.
- AmpGram belongs in the table. It ties AI4AMP (~0.79).

**Answer to Q1:** The order AMPscan RF ≈ Macrel (ROC) > AMPlify ≫ AI4AMP is real **on this balanced peptide test**. It does **not** prove SOTA on metagenomes, MIC, hemolysis, or DBAASP synthetics.

---

## 2. Is DBAASP `<30%` + matched non-AMPs the honest use?

**Yes. That is the only honest DBAASP use for a second ROC table.**

Keep locked 0.9515 untouched. Report Cohort 2 as “external, mostly synthetic, after a 30% wall.”

Musts:

1. MMseqs vs **train** at the **same** settings (`--min-seq-id 0.3 -c 0.8 --cov-mode 1`), not exact identity (the 96.5% figure is catalog recall, not a test).
2. Drop exact overlaps with **test** too (those are not external).
3. **Negatives required.** DBAASP has no non-AMPs. Use the AMPlify UniProt-style negative pool (already on disk), length-matched, also `<30%` to train **and** to the DBAASP-novel positives. Calling them “Swiss-Prot controls” is fine if that is actually the pool; do not pretend we downloaded a new UniProt dump unless we did.
4. Document D-amino acids (lowercase in DBAASP), C-amidation, `X`. Case-folding D-aa into L-aa is a limitation, not a feature.

Must nots:

- Dump all 25k and quote recall.
- Mix DBAASP into train and still claim 0.9515.
- Treat `TARGET GROUP` “Mammalian Cell” as hemolysis labels (annotation present ≠ HC50 positive vs negative).

**Ran it.** Split is in `data/splits/dbaasp_ood/`. Full-set RF ROC **0.9935 is not a win** — positives median 14 aa vs negatives median 76 aa (the short-negative pool ran out). Balanced length ≤30 slice: RF ROC **0.942**. Details: `reports/benchmarks/cohort_2_dbaasp_ood_results.md`. Need more short non-AMPs before this is a fair OOD table.

---

## 3. Is TSI = P(AMP) / (P(Hemo) + 1e-4) sound?

**No. Do not put this in the API as “pre-clinical safety.”**

Classical TSI is a **concentration ratio** (e.g. HC50 / MIC), same assay family, same units. This formula is a ratio of **two classifier scores from two datasets**. Problems:

- Macrel AMP ECE is **0.20** on our split. Their Hemo head is uncalibrated on **our** peptides; we have **no hemolysis labels** on Cohort 1 to check it.
- hemopi2 pickle is sklearn **1.3.1**; `amp-data` is **1.9.0**. MERCI ±0.5 is a real heuristic (their code), but that does not make TSI valid.
- `1e-4` is an arbitrary floor. Rank-order of TSI will be dominated by tiny P(Hemo), not by a therapeutic window.
- P(AMP) high + P(Hemo) high is a common cationic AMP (melittin). A ratio does not magically become a selectivity index.

**Allowed later, after labels:** report Macrel Hemo / hemopi2 **as foreign hemolysis scores**, with a disclaimer, and/or validate against DBAASP rows that actually have hemolysis **values**, not just a “Mammalian Cell” tag. Then, if ever, a **calibrated** score — still do not call it TSI unless HC50 and MIC exist.

---

## What to do from here (priority)

| priority | action | why |
| --- | --- | --- |
| **1 now** | Build DBAASP Cohort 2 split + score frozen tools | Only real scientific upgrade; 2 months is enough |
| 2 | Keep 0.9515 frozen; two tables | Judges can defend both |
| **not now** | peptidy → 435-D / PC6 → 27-ch CNN | Needs **retrain**; breaks lock; 0.5 ms claim is not a metric |
| **not now** | TSI endpoint | Unsound formulation |
| **not now** | AmpGram proteome scanner / AMPlify attention in UI | Extra product, not evidence |
| never as v1 | Fake radar / 4-index GRAVY cutoffs | Already rejected |

Phase order in the plan (peptidy → TSI → DBAASP) is **backwards**. DBAASP OOD first.
