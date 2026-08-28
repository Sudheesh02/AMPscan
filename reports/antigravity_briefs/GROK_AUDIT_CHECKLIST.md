# Grok audit checklist — use when Antigravity hands back Cohort 2b

Read `INTERN_HANDOFF.md` and `reports/benchmarks/cohort_2b_fair_results.md`. Then:

1. **Lock intact?** No edits under `models/`, `data/splits/train|val|test.fasta`, `scoring.py` features.
2. **No TSI / peptidy / radar** in API or frontend.
3. **Length gap** in `cohort2b_meta.json`: `|pos_median - neg_median| ≤ 8`. If not, intern failed; do not publish ROC.
4. **n_neg ≥ 2000** and `n_neg_fragment` explained in the first paragraph of the report.
5. **Headers** contain `SRC=FRAGMENT_NEG` or src=`fragment` in the index.
6. **MMseqs** flags are 0.3 / 0.8 / cov-mode 1 vs **train** and vs DBAASP novels.
7. **Headline** is 2b ROC, not 0.9935. Locked number still 0.9515.
8. If 2b RF ROC ≥ 0.98, treat as “fragments still too easy,” not a win.
9. Spot-check 10 random FASTA seqs: length 5–30, not in train.fasta exact.
10. Compare tool order to Cohort 1; a total reshuffle is a red flag.

Pass / fail in chat. Do not re-run 18k AmpGram unless n ≤ 4000.
