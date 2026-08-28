# FRONTEND v1.1 — paste this whole file into Antigravity

You are wiring the **Next.js 14 Classify + Evidence UI** to the **already-shipped** AMPscan API v1.1.

Grok already built the backend. You do **not** retrain, do **not** edit Python scoring, do **not** invent TSI/radar/hemolysis.

When finished, fill `reports/antigravity_briefs/INTERN_HANDOFF_frontend.md` (do **not** overwrite other `INTERN_HANDOFF*.md` files).

Repo: `/home/sudheesh02/SIH TEST`  
Frontend: `frontend/` (Next 14, `next dev -p 3000`, rewrite `/api/*` → `http://127.0.0.1:8000/*`)  
Live site later: `https://ampscan.vercel.app`  
Contract: `services/predict_api/API_CONTRACT.md`  
Locked headline stays **0.9515**.

---

## Why you are here

API v1.1 already has:

| Method | Path | Use from the UI |
| --- | --- | --- |
| POST | `/predict` | One peptide 5–100 + `nearest_train` |
| POST | `/predict-batch` | FASTA lists, cap **500** |
| POST | `/scan` | Length **>100**. Window scores. **Not** a protein AMP call |
| POST | `/explain` | CNN IG, **one sequence**. Not batched |
| GET | `/metrics` | Same tables + new `cohort_2b` object |
| GET | `/health` | `version` must be `ampscan-api-1.1` |

Classify still loops `BATCH_CAP=10` one-by-one on `/predict`. Length >100 is only an error. Evidence 2b table still leads with accuracy (Macrel 0.82 vs RF 0.65) — that invites a wrong ranking.

---

## Hard rules

1. Do **not** edit `models/`, `data/splits/train.fasta`, `val.fasta`, `test.fasta`.
2. Do **not** edit `services/predict_api/scoring.py` feature math, Platt, CNN T, or joblib/pt files.
3. Do **not** add TSI, hemolysis, pathogen radar, Macrel Hemo, or any “protein is AMP” label.
4. Do **not** quote **0.9935** as quality. Do **not** replace 0.9515 with 0.903.
5. Do **not** caption nearest-train identity as “MMseqs 30% cluster wall” or “<30% homology”. It is **ungapped identity**, `|Δlength| ≤ 2`.
6. Keep dark theme, biological copy, IG as the explainer (no LLM).
7. Keep the existing “Trust this number.” + 0.5-transfer paragraph on Classify.
8. `/explain` stays per selected row. Do **not** fire 500 Captum calls.
9. If `/predict-batch` or `/scan` returns 404 (old API), fall back without crashing: sequential `/predict` for 5–100; for >100 show “scan needs API 1.1”.
10. Work only under `frontend/` plus the handoff markdown. `npx tsc --noEmit` must pass.

---

## Files you may edit

```
frontend/lib/api.ts
frontend/lib/sequence.ts
frontend/app/predict/page.tsx
frontend/app/metrics/page.tsx
frontend/components/ResidueHeatmap.tsx      # only if you add a scan strip; do not break IG
frontend/components/Workflow.tsx            # one line: >100 → window scan
frontend/app/about/page.tsx                 # one sentence: scan ≠ protein AMP
frontend/app/page.tsx                       # do not change the 0.9515 hero
```

Optional new: `frontend/components/ScanTrack.tsx` (window P vs position).

Copy `/figures/cohort1_error_boxplots.png` is **already** in `frontend/public/figures/`. Use it; do not regenerate.

---

## 1) Types + clients (`frontend/lib/api.ts`)

Add these types. Extra JSON keys must be ignorable.

```ts
export type NearestTrain = {
  train_id: string | null;
  identity: number | null;      // 0–1, already rounded to 4 dp
  train_length: number | null;
  train_label: "AMP" | "non-AMP" | null;
  exact_match: boolean;
  note: string;
};

// PredictResponse: keep existing fields; ADD
nearest_train: NearestTrain | null;

export type BatchPredictResponse = {
  version: string;
  n: number;
  n_valid: number;
  n_invalid: number;
  results: Array<PredictResponse & { id: string }>;
};

export type ScanWindow = {
  start: number;   // 1-based inclusive
  end: number;
  seq: string;
  p_amp: number;
  label: "AMP" | "non-AMP";
};

export type ScanResponse = {
  valid: boolean;
  errors: string[];
  sequence_length: number;
  window: number;
  step: number;
  n_windows: number;
  protein_level_call: false | boolean;
  note: string;
  windows: ScanWindow[];
  summary: {
    max_p_amp: number | null;
    max_start: number | null;
    max_end: number | null;
    n_windows_ge_0.5: number;
    n_windows_ge_0.9: number;
  } | null;
};
```

Extend `MetricsResponse` with optional `cohort_2b` (see API_CONTRACT.md). Do not require it (old backends).

New functions:

```ts
predictBatch(items: { id?: string; sequence: string }[]): Promise<BatchPredictResponse>
scan(sequence: string, window = 25, step = 1): Promise<ScanResponse>
```

POST JSON exactly as the contract. Do not send a raw FASTA string as `sequences`.

`BATCH_CAP` in `sequence.ts`: raise **10 → 500** (API cap). Slice FASTA to 500. If over, tell the user “first 500 records”.

`validateSeq`: keep alphabet + min length 5. **Do not** treat length >100 as a hard Classify death — the page will route those to `/scan`.

---

## 2) Classify (`frontend/app/predict/page.tsx`)

### A. Peptides 5–100 (including multi-FASTA)

Replace the `for` loop of `predict()` with **one** `predictBatch()`.

Then `explain()` **only the active row** (the one shown). When the user clicks another row, fetch IG if missing. Never IG-all.

Show `nearest_train` under the dial:

- `exact_match === true` → warning banner (same visual as current canonical banner). Text: training-set recall, not a held-out test. Use `train_id` / `train_label`. This **generalizes** magainin-2 / LL-37 / melittin; keep the IG canonical names if present.
- else → muted line:  
  `Closest train {train_id} · {(identity*100).toFixed(1)}% ungapped identity (length ±2). Not an MMseqs 30% cluster wall.`

Keep HudDial = **RF Platt P(AMP)**. CNN stays secondary bar.

Keep the 0.5-transfer sentence that is already on the page.

### B. Length >100 → scan track

If the pasted **first** record has length >100 (or user pastes a protein FASTA):

- Do **not** only show “outside 5–100”.
- Call `POST /scan` `{ sequence, window: 25, step: 1 }`.
- If API says too many windows (cap 2000), retry with a larger `step` (5, then 10) **or** expose window/step inputs. Do not silently drop the C-terminus without saying so.
- Banner **verbatim meaning**: “Window scores from the locked RF. This is not a protein-level AMP call.” Bind `protein_level_call === false`.
- Plot: x = window start (1-based), y = `p_amp`. Highlight `summary.max_start`–`max_end`. Click a window to show its `seq` + P. Optional: “Classify this window” → `/predict` on that 25–100 mer (then IG).
- Do **not** put a single AMP/non-AMP badge on the whole protein.
- LL-37 lighting up on hCAP-18 is **train-set recall**. If `nearest_train` on a clicked window is exact LL-37, say so.

Mixed FASTA (shorts + longs): batch the 5–100 records; longs get a per-row “scan this chain” action. Do not concatenate multi-FASTA (backend `/scan` already uses the first record only).

### C. Examples

Keep magainin-2 / LL-37 / melittin chips (train). Optional fourth chip: “hCAP-18 scan” using `reports/benchmarks/hcap18_test.fasta` contents (170 aa). If you add it, hardcode the sequence in `sequence.ts`; do not fetch the CSV.

---

## 3) Evidence (`frontend/app/metrics/page.tsx`)

Hero stats stay: **0.9515 first**. External 2b **0.903** is already the fourth stat — keep it smaller than 0.9515. Never add 0.9935 as a Stat.

**External (2b) table — column order must become:**

`model | n | skip | ROC-AUC | PR-AUC | ECE-15 | acc @ 0.5 | MCC`

Caption under the table, exact meaning:

> Do not rank tools by Cohort 2b accuracy at 0.5. Platt fitted on Cohort 1 does not transfer (RF ECE 0.28). Ranking is a ~0.90 ROC tie.

If `GET /metrics` returns `cohort_2b.tools`, **use that** (numbers stay locked; still display 4 decimals). If missing, keep the hardcoded rows that are already on the page — just reorder columns.

Models tab: add the existing figure:

```tsx
<Fig src="/figures/cohort1_error_boxplots.png" cap="Cohort 1 errors: FN tend to be longer, charge ~0, more Cys than TP" />
```

One sentence: FN (n=195) median length 38 vs TP 18; net charge ~0 vs +3; mean Cys 1.95 vs 0.99. Do not invent other error stats.

---

## 4) Tiny copy (optional, one line each)

- `Workflow.tsx` step 01: mention windowed scan if length >100.
- `about/page.tsx`: “Chains longer than 100 aa get a sliding-window RF score, not a protein-level AMP call.”
- Home hero **0.9515** stays. Do not promote 0.903 to the big number.

---

## 5) How to run

```bash
# terminal A — API (amp-data)
cd "/home/sudheesh02/SIH TEST"
/home/sudheesh02/miniforge3/envs/amp-data/bin/uvicorn main:app \
  --app-dir services/predict_api --host 127.0.0.1 --port 8000

# terminal B — UI
cd "/home/sudheesh02/SIH TEST/frontend"
npm run dev
```

`GET http://127.0.0.1:8000/health` → `"version": "ampscan-api-1.1"`.

Vercel: `NEXT_PUBLIC_API_URL` should point at the 1.1 API. CORS already allows `https://ampscan.vercel.app`. Do not weaken CORS from the frontend repo.

---

## Manual QA (you must click these)

1. Magainin-2 → AMP, nearest `POS_DRAMP_DRAMP02271`, `exact_match`, IG heatmap still works, mutate still works.
2. Paste a 3-record FASTA of 5–100 mers → **one** network call to `/predict-batch` (DevTools). IG only after selecting a row.
3. 501-record FASTA → UI caps at 500; no crash.
4. Paste hCAP-18 (170 aa) → scan track, disclaimer visible, max window near C-term (LL-37). **No** protein-level AMP badge.
5. Length 4 → error. Length 140 without API 1.1 → no crash.
6. Evidence → 0.9515 still first. 2b table ROC-AUC before accuracy. 0.9935 only in the existing footnote, not a Stat.
7. Desktop + ~375px wide. Dark theme. No TSI/radar.

---

## Out of scope

ONNX, Macrel Hemo, peptidy, retraining, Streamlit, new color system, LLM chat, rewriting ResidueHeatmap interaction except scan strip.

---

## Fill this when done

Write `reports/antigravity_briefs/INTERN_HANDOFF_frontend.md` with:

- Files changed
- BATCH_CAP new value
- Confirm `/predict-batch` used (yes/no) and IG lazy (yes/no)
- Scan disclaimer screenshot-level description (what the user sees)
- Nearest-train copy (exact sentence you shipped)
- 2b table column order
- `npx tsc --noEmit` result
- Anything you skipped
