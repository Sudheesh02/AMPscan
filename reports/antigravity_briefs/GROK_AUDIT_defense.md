# Grok audit of intern defense ammo (2026-08-24)

**Verdict: PASS.** Numbers recompute. Evidence says **tie vs Macrel on ROC**, we win ECE. 0.9515 stays first. 0.993 is flagged not-to-quote.

## Checklist

| # | item | result |
| --- | --- | --- |
| 1 | Frozen / no TSI | **Pass.** |
| 2 | Recompute OP + bootstrap | **Pass.** P≥0.5: 1632 called, prec **0.875**, rec **0.880**; P≥0.9: 1059, prec **0.974**, rec **0.635**. ΔAUC vs Macrel **0.0014**, CI **[-0.0049, 0.0075]**, excludes 0: **False**. |
| 3 | Must not claim ROC win vs Macrel | **Pass.** Evidence: *tie on ranking, ECE 0.023 vs 0.204*. |
| 4 | External 0.903, no 0.993 headline, 0.9515 first | **Pass.** |
| 5 | Error files | **Pass.** FN 195 / FP 204 match locked CM. Boxplot + FN/FP CSVs on disk. Figures copied to `frontend/public/figures/`. |
| 6 | Prior handoffs | **Pass.** |
| 7 | Precision/recall not “acc at 0.9” | **Pass.** |

## Science (use on slides)

- **Missed AMPs (FN)** are longer (median 38 vs 18), **not cationic** (charge ~0 vs +3), weaker μH, more Cys. The forest is a **cationic amphipathic** detector. That is the honest limit, and why peptidy/PC6 may only help at the margin.
- **RF vs Macrel:** ranking **tie**. **RF vs AMPlify:** ΔAUC **0.023**, CI excludes 0 — we **do** beat AMPlify on this split.
- At **P≥0.9**: precision **0.974**, recall **0.635**. Use that for “rare AMP” talk, not 0.877 accuracy.

## Nit

External table still shows Macrel **acc 0.82** vs RF **0.65**. Copy underneath is correct (quote ROC). A rushed judge might read the accuracy column. Prefer ROC-first on that table if you touch the page again.

Do **not** start v2 ablation until you want a new filename under `models/v2/`. Defense job is done.
