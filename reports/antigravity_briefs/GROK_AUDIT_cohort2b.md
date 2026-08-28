# Grok audit of intern Cohort 2b (2026-08-24)

**Verdict: PASS, with one scientific caution.** Length match is real. Numbers recompute. Lock/TSI rules held. Do not pitch RF **accuracy 0.645** or treat 0.903 as a replacement for locked **0.9515**.

## Checklist

| # | item | result |
| --- | --- | --- |
| 1 | Lock intact (no retrain / no split rewrite) | **Pass.** No TSI in API. `train/val/test.fasta` untouched. |
| 2 | No TSI / peptidy / radar | **Pass.** |
| 3 | Length median gap ≤ 8 | **Pass.** pos 14 / neg 14 / gap **0**. Means 15.99 vs 15.92. |
| 4 | n_neg ≥ 2000; fragments explained | **Pass.** 11190 negs; 11012 fragment / 178 intact. Report says so up front. |
| 5 | Fragment labels | **Pass with nit.** Index `src=fragment`. FASTA `SRC=FRAGMENT` (not the string `FRAGMENT_NEG` the intern wrote in the handoff). Still unambiguous. |
| 6 | MMseqs 0.3 / 0.8 / cov-mode 1 vs train and DBAASP | **Pass.** `cache/dbaasp_ood_fair/*.m8` present (`frag_vs_train`, `frag_vs_dbaasp`, parents, intact). |
| 7 | Headline not 0.9935; lock 0.9515 | **Pass.** |
| 8 | ROC ≥ 0.98 ⇒ too easy | **Pass.** RF **0.903** — this is *harder*, not easier. |
| 9 | Spot-check: short, not in train | **Pass.** sha256 matches. 10 random negs length 7–19, **0 exact train overlap** of 22380. |
| 10 | Tool order vs Cohort 1 | **Pass.** RF ≳ Macrel ≈ AMPlify > CNN > AI4AMP. Same family. |

Recomputed AMPscan RF from CSV: ROC **0.9030**, acc **0.6449**, ECE **0.2767**, confusion **TN 3643 / FP 7547 / FN 401 / TP 10789**. Matches the intern table.

## How to read the numbers (this is the science)

Cohort 1 (locked): RF ROC **0.9515**, acc **0.877**, ECE **0.023**, peptides vs AMPlify-style non-AMPs.

Cohort 2b (fair-ish OOD): DBAASP novels vs **windows cut from unused long UniProt-like chains**, length-matched.

| | Cohort 1 | Cohort 2b |
| --- | ---: | ---: |
| RF ROC-AUC | 0.9515 | **0.9030** |
| RF acc @ 0.5 | 0.8765 | **0.6449** |
| RF ECE | 0.0235 | **0.2767** |
| Macrel ROC | 0.9491 | 0.8998 |
| AMPlify ROC | 0.9277 | 0.8991 |

- Ranking still works (~0.90). **0.5 threshold does not.** Mean P(AMP) is 0.93 on DBAASP and **0.62 on fragments**, so Platt (trained on Cohort 1) calls most fragments AMP (7547 FP). Quote **ROC/PR**, not accuracy.
- Macrel/AMPlify **accuracy ~0.82** looks better than RF **0.64** only because they are more conservative. ROC is **tied** (~0.90). Do not say “Macrel beats AMPscan on OOD.”
- Negatives are **not** assayed non-AMPs. A drop from 0.95 → 0.90 is expected and usable; it is not “we fail OOD.”

## Intern grade

Followed the brief. Did not invent TSI. Did not quote 0.99. AmpGram skip is correct.

Nit: handoff said `SRC=FRAGMENT_NEG`; files say `SRC=FRAGMENT`. Harmless.

## Pitch lines

- Locked: **Cohort 1 RF ROC-AUC 0.9515** (homology, calibrated).
- External: **Cohort 2b RF ROC-AUC 0.903** on length-matched DBAASP vs fragment non-AMPs; calibration does not transfer (ECE 0.28).
- Do not use Cohort 2b accuracy or the old 0.993 table.
