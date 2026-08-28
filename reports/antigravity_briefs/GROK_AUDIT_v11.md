# Grok audit of intern v1.1 (2026-08-24)

**Verdict: PASS.** Frozen scores match. Batch path is real. UI sentence is in. Do not sell the hCAP-18 scan as discovering LL-37 (that peptide is **in train**).

## Checklist

| # | item | result |
| --- | --- | --- |
| 1 | models / train FASTA | **Pass.** No TSI in API. |
| 2 | 425-D unchanged | **Pass.** |
| 3 | batched vs locked CSV \|Δ\| < 1e-5 | **Pass.** Recomputed: RF **0**, CNN **1.35e-7**. |
| 4 | speed factor > 1; no fake GPU 20× | **Pass.** **157.8×** vs the Python one-seq loop (27.5 → 4336 seq/s). Not GPU. RF `n_jobs` was already 4; the win is `featurize_many` + one `predict_proba`. Brief guessed 3–8×; the loop was worse than that. Do not quote “GPU.” |
| 5 | scanner window scores | **Pass.** `note` = `window score; not a protein-level AMP call`. window=25. Smoke: 14199 windows, 1803 proteins ≥25 aa. |
| 6 | Classify 0.5-transfer sentence | **Pass.** Exact text on `frontend/app/predict/page.tsx`. |
| 7 | Cohort 2b handoff intact | **Pass.** |
| 8 | 0.9515 still locked | **Pass.** |

## Nit: hCAP-18 / LL-37

Scanner on 170 aa hCAP-18 (147 windows, step 1) lights up ~141–165 at P≈0.99. **LL-37 (`LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES`) is homology-train** (`POS_DRAMP_DRAMP03571`). The UI already warns when you paste it. This shows the windowing **runs**, not that we found a new domain.

Handoff said `SRC=SCAN`; CSV uses a `note` column instead. Harmless.

## Pitch

- Scoring can be **~150× faster** on CPU by batching. Same P(AMP) as v1.
- Scanner is a **track of peptide windows**, not “this protein is AMP.”
- Classify now says 0.5 may over-call on short OOD. Locked metric remains **0.9515**.
