# AMPscan Study Guide — Member 6
## Full-Stack Systems & API Engineering Lead

---

### 1. Domain Scope & Responsibilities
- **Production Next.js 14 App Router UI**: TypeScript, Tailwind CSS, live *in silico* point mutation workbench, and Evidence Dashboard.
- **FastAPI v1.1 High-Throughput Microservice**: Asynchronous lifespan, vectorized batch featurization (`POST /predict-batch`, cap 500), and formal API Contract.
- **Sliding-Window Proteome Scanner (`POST /scan`)**: Scanning chains up to 5,000 aa (validated by detecting mature LL-37 in 170-aa hCAP-18).
- **Sub-Millisecond `TrainIndex` Nearest-Neighbor Engine**: In-memory length-bucketed ASCII byte matrix indexing 14,904 training peptides ($<3\text{ ms}$ query latency).
- **End-to-End Smoke Testing & Vercel Deployment**: Automated test suite (`scripts/smoke_api_v11.py`) and CORS allow-listing.

---

### 2. System Architecture & Component Interactions

```
                ┌──────────────────────────────────────────────────────────┐
                │                 Next.js 14 Web Frontend                  │
                │        (App Router, TypeScript, Tailwind, Lucide)        │
                │                   Runs on Port 3000                      │
                └─────────────────────────────┬────────────────────────────┘
                                              │
                         HTTP Reverse Proxy   │ Rewrites /api/*
                         (Zero CORS Overhead) │ to Port 8000
                                              ▼
                ┌──────────────────────────────────────────────────────────┐
                │               FastAPI v1.1 Inference Engine              │
                │           (Asynchronous Lifespan, Pydantic v2)           │
                │                   Runs on Port 8000                      │
                └──────┬──────────────────────┬──────────────────────┬─────┘
                       │                      │                      │
                       ▼                      ▼                      ▼
        ┌────────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
        │   Platt-Calibrated RF  │ │ 1D-CNN (T-Scaled)  │ │   `TrainIndex`     │
        │   425-D Feature Engine │ │ Captum IG Engine   │ │ Sub-ms In-Memory   │
        │  `homology_rf.joblib`  │ │`homology_cnn1d.pt` │ │ 14,904 Train Seqs  │
        └────────────────────────┘ └────────────────────┘ └────────────────────┘
```

---

### 3. FastAPI v1.1 Core REST Endpoints

| Method | Endpoint | Request Schema | Max Limits | Description |
| :--- | :--- | :--- | :---: | :--- |
| `GET` | `/health` | None | N/A | Server status, model paths, calibration parameters, `TrainIndex` status ($n=14,904$). |
| `GET` | `/metrics` | None | N/A | Locked benchmark JSON: Cohort 1 SOTA table, Random split leakage, Calibration ECEs, Cohort 2b OOD metrics. |
| `POST` | `/predict` | `{"sequence": str}` | $5 \le L \le 100$ | Calibrated RF $P(\text{AMP})$, CNN $P(\text{AMP})$, 5 physicochemical features, `TrainIndex` nearest neighbor hit. |
| `POST` | `/predict-batch` | `{"sequences": [{"id": str, "sequence": str}]}` | **Cap: 500 seqs** | Vectorized batch feature extraction and dual-model inference with per-item validation errors. |
| `POST` | `/scan` | `{"sequence": str, "window": int, "step": int}` | **$\le 5,000$ aa / 2,000 wins** | Sliding-window locked-RF scoring across full proteins; returns window array and peak domain coordinates. |
| `POST` | `/explain` | `{"sequence": str}` | $5 \le L \le 100$ | Captum Integrated Gradients per-residue attribution vector (32 steps) + Canonical training set warning flag. |

---

### 4. In-Memory `TrainIndex` Nearest-Neighbor Engine

#### Algorithmic Design & In-Memory Data Structure
- Ingests **14,904 homology-train sequences** from `data/splits/train.fasta` during FastAPI startup.
- Peptides are indexed into length-specific 2D NumPy ASCII matrices (`_LenBucket` of shape $[N_L, L]$ with `uint8` encoding).

#### Two-Tiered Lookup Algorithm
1. **Tier 1 (Exact Match):** Python $O(1)$ hash table check (`self.exact`). If matched, returns identity = 1.0 with training accession ID (e.g., `POS_DRAMP_DRAMP02271`) and exact training match warning.
2. **Tier 2 (Ungapped Approximate Search):** If no exact match, queries length buckets $L \pm 2$:
   $$\text{Identity} = \max_{\text{offsets}} \frac{\sum_{i=1}^{\min(L_1, L_2)} \mathbb{I}(q_i == t_i)}{\max(L_1, L_2)}$$
   Implemented via vectorized NumPy broadcasting `(arr == q).sum(axis=1)` for sub-millisecond execution ($<0.82\text{ ms}$ on CPU).

---

### 5. Sliding-Window `/scan` Engine & hCAP-18 Validation

#### Operational Constraints & Verification
- Enforces strict safety bounds: maximum length 5,000 aa, window size 5–100 aa, and max 2,000 windows.
- Attaches an immutable scientific disclaimer: `"protein_level_call": false`.
- **Validation on Human Cathelicidin Precursor (hCAP-18, 170 aa):**
  - Residues 1–133 (Inactive Cathelin domain): scores non-AMP ($P < 0.15$).
  - Residues 134–170 (Cleaved mature LL-37 peptide): **detects peak domain at residue 141 with $P(\text{AMP}) = 0.9926$**.

---

### 6. Top 5 Judge Defense Questions & Verbatim Answers

**Q1: Why did you build a decoupled FastAPI + Next.js architecture instead of just using Streamlit?**  
> *"Streamlit is excellent for prototyping, but its execution model reruns the entire Python script on every user interaction, making it unsuitable for responsive tools like our *in silico* point mutation studio or high-throughput batching. Our decoupled Next.js 14 frontend communicates with an asynchronous FastAPI backend via server-side rewrites, providing sub-10ms UI updates, zero CORS overhead, and production-grade client-server separation."*

**Q2: How does your sub-millisecond `TrainIndex` work and why is it important?**  
> *"During startup, FastAPI loads the 14,904 homology-train sequences into length-bucketed 2D NumPy ASCII matrices. When a user submits a peptide, `TrainIndex` runs an $O(1)$ exact hash lookup followed by vectorized broadcast matrix comparison across length bins $L \pm 2$. It executes in under 0.8 milliseconds and instantly alerts users if a predicted AMP is merely memorizing a known training sequence like Magainin-2 or LL-37."*

**Q3: What prevents your sliding-window `/scan` endpoint from crashing on full human proteomes?**  
> *"We enforce strict safety bounds: maximum sequence length of 5,000 amino acids, maximum window count of 2,000, and single-record FASTA parsing. If a user inputs a massive protein with a step size of 1, the API returns a structured validation error advising them to increase the step size before allocating memory. In addition, window scoring is fully vectorized via NumPy batch featurization."*

**Q4: Is the `/scan` endpoint claiming to make whole-protein functional predictions?**  
> *"No, and our API explicitly returns `"protein_level_call": false` in its response schema. The `/scan` endpoint applies our peptide model across sliding windows to identify localized antimicrobial candidate domains within larger precursors—as demonstrated by identifying mature LL-37 at the C-terminus of hCAP-18."*

**Q5: How do you verify API integrity before deployment?**  
> *"We run our automated smoke test script `scripts/smoke_api_v11.py`, which executes 11 end-to-end assertions covering model paths, metric constants, batch scoring parity, sliding-window accuracy, and sub-millisecond TrainIndex latency."*

---

### 7. Spoken Presentation Scripts

#### 30-Second Intro Script:
> *"I lead the full-stack engineering and serving systems for AMPscan. We engineered a production Next.js 14 workbench on port 3000 backed by a high-throughput FastAPI v1.1 microservice on port 8000, featuring batch scoring, whole-protein scanning, and sub-millisecond training memorization lookups."*

#### 60-Second Deep-Dive Script:
> *"We developed a decoupled enterprise stack: Next.js 14 with TypeScript and Tailwind CSS communicating with an asynchronous FastAPI engine via server rewrites. During startup, the API loads all locked weights and initializes `TrainIndex`—an in-memory database of 14,904 training peptides stored as length-stratified NumPy matrices that checks for exact training matches in under 0.8 milliseconds.
> 
> For high-throughput screening, our `/predict-batch` endpoint scores up to 500 multi-FASTA sequences in parallel at 4,335 sequences per second. For long proteins, our `/scan` endpoint performs sliding-window analysis up to 5,000 residues. In testing on human hCAP-18, `/scan` accurately located the cleaved LL-37 antimicrobial domain with peak probability 0.993 while correctly classifying the inactive precursor as non-AMP."*
