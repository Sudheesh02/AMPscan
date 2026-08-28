# Grok audit result — backend v1.1 (this worktree)

**Date:** 2026-08-25  
**Repo audited:** `/home/sudheesh02/SIH TEST` (uncommitted API v1.1)  
**Not audited:** Grok worktree `~/.grok/worktrees/sudheesh02-sih-test/test` (still old FastAPI).  
**Frontend:** not scored. `FRONTEND_v1.1.md` is a later pass.

Smoke re-run here: `amp-data` → `python scripts/smoke_api_v11.py` → **SMOKE OK**.

---

## Checklist vs previous FAIL

| # | Previous (old tracked API / Grok worktree) | This worktree (`/home/sudheesh02/SIH TEST`) |
| --- | --- | --- |
| 1 Frozen weights / 425-D / no TSI | PASS (code) | **PASS.** `git diff` empty on joblib / pt / Platt JSON / train FASTA. `len(FEATURE_NAMES)=425`. No TSI/hemo/radar/peptidy/PC6 in API. |
| 2 Batch = sequential RF Δ 0 | PASS on CSVs | **PASS** on API too. `rf_calibrated_many` vs loop: max \|Δ\| **0.0**. CNN 3.0e-8. `POST /predict-batch` exists, cap 500 → 422. |
| 3 Scan disclaimer | PASS CLI only | **PASS.** `POST /scan` (`main.py`). `protein_level_call: false`. hCAP-18 smoke: 30 windows, max P **0.992608** at start **141**. |
| 4 Nearest-train | FAIL (canonical trio) | **PASS** with documented method. `TrainIndex` on `train.fasta` n=**14904**. Magainin-2 → `POS_DRAMP_DRAMP02271` identity **1.0**. Double-terminal mutant → same ID **0.913**. Ungapped, \|ΔL\|≤2, **not** MMseqs. ~**0.10 ms**/query. `/explain` still canonical-only (contract). `/predict` and batch carry `nearest_train`. |
| 5 2b payload | FAIL (no key) | **PASS.** `headline.do_not_quote` stays **0.9791** (leakage control). New `cohort_2b`: ROC **0.9030**, PR **0.9205**, ECE **0.2767**, `do_not_quote.value` **0.9935**. Smoke asserts both. |
| 6 CORS Vercel | FAIL localhost | **PASS** in source. `https://ampscan.vercel.app` is in `allow_origins` (`main.py`). |
| 7 Smoke script | FAIL missing | **PASS.** `scripts/smoke_api_v11.py` exists; re-ran here. |

---

## Evidence (file:line)

- Version `ampscan-api-1.1`: `services/predict_api/scoring.py:35`
- CORS Vercel: `services/predict_api/main.py:62-68`
- `GET /metrics` + `cohort_2b`: `services/predict_api/main.py:164-180`, payload `locked_metrics.py:73-166`
- Batch path: `main.py:192-230`, `scoring.py:364-369` (`featurize_many` + one `predict_proba`)
- Scan: `main.py:233-275`, `SCAN_NOTE` `scoring.py:57`
- Nearest: `TrainIndex` `scoring.py:207-329`; note “not an MMseqs 30% cluster wall” `scoring.py:50-52`
- `/explain` canonical banner only: `main.py:278-310`

Locked weights mtimes unchanged (joblib 2026-08-19, Platt JSON 2026-08-20). API files mtime 2026-08-25.

---

## Smoke (this run)

```
health ok ampscan-api-1.1 n_train 14904
metrics ok  0.9515 + 2b 0.9030
predict magainin-2 p= 0.993312 nearest POS_DRAMP_DRAMP02271
predict mutant identity 0.913 train_id POS_DRAMP_DRAMP02271
predict >100 points at /scan
predict-batch mixed ok
batch cap 500 -> 422
scan 25-mer matches rf_calibrated 0.28931
scan hCAP-18 windows 30 max_p 0.992608 at 141
nearest-train 0.10 ms/query
SMOKE OK
```

Extra probes (TestClient, same env):

- Poly-K `/predict`: p=0.988976, `nearest_train.train_id=POS_DRAMP_DRAMP31549`, identity **0.6667**, `exact_match=false`, note says ungapped / not MMseqs.
- Poly-K `/explain`: `train_set_warning=false` (canonical-only). Expected.
- Multi-FASTA `/scan`: first record only (`A`×25), does not concatenate `K`×25.

---

## Nits (non-blocking)

1. Diff is **uncommitted**. The Grok worktree / last committed FastAPI will still fail items 4–7 until this slice is committed or copied.
2. Live `https://ampscan.vercel.app/api` is still the old serverless API (`ampscan-api-1.0`, no `cohort_2b`, magainin CNN 0.476). This audit is the local FastAPI, not Vercel.
3. `/explain` does not use `TrainIndex`. Contract says so. Do not call that nearest-train.
4. Identity is ungapped + length window. Captioning it as “30% MMseqs hold-out” would be a real FAIL; the note currently prevents that.

---

## Frontend (not this pass)

See `FRONTEND_v1.1.md` after that intern lands. Do not mix.

---

## Verdict

**PASS WITH NITS**
