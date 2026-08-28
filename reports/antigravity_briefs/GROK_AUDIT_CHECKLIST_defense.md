# Grok audit checklist — defense intern

1. models/ and splits untouched; no TSI in API.
2. Recompute one operating-point row and one bootstrap number from CSVs.
3. If `ci_excludes_0` is false for RF vs Macrel, Evidence must **not** say we beat Macrel on ROC.
4. External tab: 0.903 + fragment negs; no 0.993; 0.9515 still headline.
5. Error boxplot exists; FN/FP CSVs have sequences.
6. Prior handoffs (`INTERN_HANDOFF.md`, `_v11.md`) untouched.
7. Operating-point table uses precision/recall, not “accuracy at 0.9.”
