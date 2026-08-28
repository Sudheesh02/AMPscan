# Plan: learn from other AMP tools, steal only what survives an audit

**Status:** plan only (2026-08-24). No retrain. No TSI. Locked Cohort 1 RF ROC-AUC **0.9515** stays the v1 headline.

**Goal:** one honest architecture comparison (how *they* optimized vs how *we* did), then upgrades that are (a) engineering-only for v1.1 or (b) new-model experiments for v2. Antigravity-style “add peptidy + PC6 + TSI and call it Pro” is **out**.

---

## Why this is not “copy the SOTA stack”

On the **same** locked homology test:

| model | ROC | acc@0.5 | ECE | what they optimized |
| --- | ---: | ---: | ---: | --- |
| **AMPscan RF Platt** | **0.9515** | **0.877** | **0.023** | homology split, 425-D AAC/DPC/physchem, Platt |
| Macrel ONNX RF | 0.949 | 0.785 | 0.204 | 22-D + speed + metagenome pipeline + hemo head |
| AMPlify BiLSTM+attn | 0.928 | 0.856 | 0.118 | sequence model, attention, wet-lab follow-up |
| AMPscan CNN | 0.942 | 0.865 | 0.040 | IG explainer |
| AI4AMP PC6 | 0.791 | 0.745 | 0.153 | physicochemical tensor encoding |
| AmpGram n-gram RF | 0.790 | 0.723 | 0.164 | 10-mer proteome scan |

Cohort 2b (length-matched DBAASP vs **fragment** non-AMPs): RF **0.903**, Macrel **0.900**, AMPlify **0.899**. Ranking tied. RF **acc 0.645 / ECE 0.28** — Platt does not transfer.

**Implication:** we already match or beat them on ranking + calibration **in-family**. “Take good things” is mostly **product/engineering** and **honest extra heads**, not a new backbone.

---

## How each tool optimized (vs us)

### Macrel — throughput and a second task
Tiny 22-D features, 101 trees, **ONNX** (~6600 seq/s vs our Python loop). Dual AMP + **Hemo** checkpoints (different label, not a TSI). Built for contigs/smORFs.
**We differ:** 425-D + DPC, Platt, IG, homology-aware metrics. We win ECE; they win speed.
**Take:** batch `rf.predict(X)`; optional ONNX of *our* RF later; optional **foreign** Macrel-Hemo score with a disclaimer. **Do not** divide P(AMP)/P(Hemo).
Note: Cohort 1 Macrel is **FN-heavy** (FP 22, FN 661), not “high FPR.”

### AMPlify — sequence grammar and attention
5× BiLSTM+attention, pad to 200, 20 AA only. Paper ~0.98 → **0.928** on our 30% split. TF 1.12 / no RTX 5060 in TF 2.10.
**We differ:** composition RF beats their DL at 5–100 aa. ESM-150M frozen linear 0.9521 did not justify LoRA.
**Take:** optional side-by-side attention via `amp-tf` CLI. Not the hot path. Not “hybrid 512-D + 425-D” without a v2 val gate (≥ +0.01 ROC on homology val).

### AI4AMP — continuous residue physics (PC6)
200×6 z-scored physchem + CNN/LSTM. **0.791** on our split = domain shift.
**Take only in v2:** extra CNN channels **if** homology val ROC improves by ≥ **0.01** vs locked CNN. Default expectation: will not beat the RF.

### AmpGram — long proteins via 10-mers
Ranger n-grams, R, ~1 seq/s.
**Take:** scanner mode that slides *our locked RF* on proteins >100 aa (window 20–30, step 1). Do not port their R model.

### peptidy — feature library, not a predictor
TPSA / instability / rotatable bonds. Dead weight on a **frozen** 425-D RF.
**Take only in v2 ablation:** retrain, select on val, freeze a **new** metric. Never keep 0.9515.

### Skip / different task
hemopi2 (hemolysis, sklearn 1.3.1 ≠ 1.9); zswitten (MIC, ≤50 aa); sAMPpred-GAT (>100 GB); ESM already tried.

---

## Filter

| Idea | v1.1 (no retrain) | v2 (new metric) | Never |
| --- | --- | --- | --- |
| Vectorized / batched scoring | **Yes** | — | — |
| Sliding-window scanner with locked RF | **Yes** (scan, not protein-AMP) | — | — |
| Macrel Hemo as *foreign* P(Hemo) | Maybe, labeled not-ours | Calibrate if hemolysis **values** exist | TSI = P(AMP)/(P(Hemo)+ε) |
| Dual IG + AMPlify attention | Optional, slow path | — | Attention = wet-lab map |
| peptidy / Macrel CTDD extras | No | Ablation on val | Claim better stability with no number |
| AI4AMP PC6 channels | No | Ablation vs CNN val | 21→27 channels without beating RF |
| DBAASP TARGET GROUP heads | No | Only clean labels | Radar from tags |
| ONNX of *our* RF | Later | — | Claim 6600 seq/s before measuring |
| Retrain on DBAASP, keep 0.9515 | — | New table | Mixing |

---

## Workstreams (this order)

### W0 — Comparison report (done 2026-08-24)
`reports/architecture_comparison_v1.md`. Remaining 2-month list: `reports/two_month_remaining_work.md`.

### W1 — v1.1 engineering (weights frozen)
1. Batch scorer: featurize many sequences → one `predict_proba`. Honest speedup ~3–8× CPU, not “45 s on the 5060” (RF is CPU; `n_jobs` already 4).
2. UI copy: *P≥0.5 was calibrated on DRAMP/AMPlify; on short OOD it over-calls.*
3. Optional `scripts/scan_protein.py`: windowed locked RF for proteins >100.

Do **not** add features to `scoring.py` here.

### W2 — v2 experiments (new freeze, val-gated)
On **homology val** only until the end: (1) RF + peptidy vs 425-D, (2) CNN + PC6 vs 21×100. Keep only if val ROC ≥ locked val **+ 0.01** and ECE not worse. Then **one** test shot under `models/v2/`. 0.9515 remains “v1 locked.” Expected: extras fail the gate; still useful.

### W3 — not now
TSI, radar, hemopi2 in `amp-data`, sAMPpred-GAT, live `.wslconfig` resize, quoting 0.993.

---

## Success
- A judge can answer “why RF not BiLSTM?”
- v1.1 does not change 0.9515 / 0.903 / Platt JSON
- Stolen features are either unused-in-frozen-RF (forbidden) or behind a v2 val gate
- Hemolysis, if shown, is named Macrel-Hemo / hemopi2, not “AMPscan safety index”

## Who
Gemini: W1 batch scorer + optional scanner (intern brief).
Grok: W0 comparison report + audit of any v2 ablation.
