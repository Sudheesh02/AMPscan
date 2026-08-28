# Two months left — what is actually worth doing

v1 is pitchable: **0.9515** locked, **0.903** fair-ish OOD, batch scoring, scanner, 0.5-transfer warning. This list is ordered by **honesty × payoff**. Do not start ten intern Pro stacks.

---

## Do next (high value)

### 1. Error analysis on Cohort 1 (1–2 days)
FP/FN vs length, charge, GRAVY, μH. Question: do we fail **anionic / cysteine-rich / long** AMPs? That tells you whether peptidy/PC6 can help or whether the misses are label noise. Write `reports/cohort1_error_analysis.md`. No retrain.

### 2. Operating-point table, no new model (half day)
Cohort 1 is 50/50. Real screens are AMP-rare. Publish precision/recall at P ≥ 0.5 / 0.8 / 0.9 / 0.95 on Cohort 1 **and** 2b. Puts LIMITATIONS.md on Evidence. Still frozen weights.

### 3. DeLong / bootstrap: RF vs Macrel vs AMPlify (1 day)
The 0.951 vs 0.949 gap is probably **not significant**. Honest slide: *ranking tied with Macrel; we win calibration.* Stronger than “SOTA ROC.”

### 4. Evidence page: two tables (1 day)
Cohort 1 0.9515 + ECE. Cohort 2b 0.903 + fragment disclaimer. Do **not** put 0.993 on the site.

### 5. v2 ablation, val-gated (3–7 days, expect a miss)
Retrain **copies** only:

- RF + peptidy extras (instability, aliphatic, TPSA, H-bond counts) vs locked 425-D
- CNN + PC6 channels vs 21×100

**Keep only if homology val ROC ≥ locked val + 0.01 and ECE not worse.** Then **one** test shot under `models/v2/`. Headline becomes a new number; **0.9515 stays v1.** If it fails, write the negative result — that is a takeaway (“we tried Macrel/AI4AMP features; composition RF was enough”).

---

## Worth it if a judge asks “what about X?”

| Item | Time | Notes |
| --- | --- | --- |
| ONNX of **our** RF | 1–2 days | Macrel’s real lesson. Measure seq/s. Don’t claim 6600 before measuring. |
| Scanner in Classify for seq >100 | 1–2 days | Window track, not protein AMP. |
| Nearest train peptide (MMseqs) | 2 days | “Closest train ID = 42%” is honest homology context. |
| Macrel Hemo as **foreign** score | 1 day + caveat | Label “Macrel HemoPI, not AMPscan.” No TSI. Optional: vs DBAASP “Mammalian Cell” **tag** (weak). |
| Length-aware Platt on **val only** | 1–2 days | Might cut 2b ECE; must not hurt Cohort 1 test ECE. New JSON, not overwrite v1 Platt. |

---

## Low payoff / skip

- Hybrid AMPlify 512-D + 425-D without the +0.01 val gate
- ESM LoRA (already failed)
- DBAASP multi-label TARGET GROUP heads (186 messy strings)
- hemopi2 inside `amp-data` (sklearn 1.3 vs 1.9)
- zswitten MIC on our binary labels
- sAMPpred-GAT 100 GB
- Live `.wslconfig` RAM dance
- Quoting 0.993 or 2b accuracy 0.65 as quality

---

## Suggested calendar

| Week | Work |
| --- | --- |
| Now | Error analysis + operating points + DeLong (defense ammo) |
| Next | Evidence UI: two honest tables |
| Then | v2 ablation (intern OK if they cannot touch `models/baseline/`) |
| If ablation fails | ONNX + scanner UI + nearest-train card |
| Last | Freeze slides. Stop adding heads. |

---

## Takeaways already earned (use these, don’t re-derive)

1. Short peptides: **composition RF ≥ BiLSTM ≥ PC6 CNN** on a homology split.
2. **Calibration is our product**, not 0.002 ROC over Macrel.
3. External DBAASP is **0.90** when lengths match; **0.99 was length**.
4. 0.5 is a **Cohort 1** cut.
5. Other tools’ “good ideas” are mostly **speed, a hemo checkpoint, attention, windows** — we can take those without replacing the forest.
