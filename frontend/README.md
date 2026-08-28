# AMPscan Frontend (Next.js 14)

Production web interface for **AMPscan** built with Next.js 14 App Router, Tailwind CSS, Lucide icons, and Framer Motion.

## Features

- **Primary Inference UI (`/predict`)**:
  - Calibrated Random Forest $P(\text{AMP})$ score dial and secondary CNN temperature-calibrated probability.
  - **In-Memory Nearest-Neighbor Card**: Sub-millisecond lookup against 14,904 homology-train sequences, displaying closest accession ID, identity percentage, and exact training match warnings.
  - **High-Throughput Batch Scoring**: Paste up to 500 multi-FASTA records in a single click with instant vectorized scoring.
  - **Whole-Protein Sliding-Window Scanner**: Seamlessly scans proteins $>100$ aa (e.g. 170-aa hCAP-18 precursor) with customizable window lengths and peak $P(\text{AMP})$ domain detection.
  - **Interactive Explainability**: CNN Integrated Gradients per-residue attribution track with live *in silico* point mutation workbench.
- **Scientific Evidence Dashboard (`/metrics`)**:
  - 4 tabs: Models (Homology test, multi-tool SOTA ROC curve), Homology vs. Random split leakage, Probability Calibration (Platt & Temperature reliability), and External (2b) length-matched DBAASP OOD validation.
  - Discovery triage operating points ($P \ge 0.90$ delivering 97.4% precision).

## Development Setup

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Configure local environment (points to FastAPI backend on port 8000)
cp .env.example .env.local

# 3. Run development server (port 3000)
npm run dev

# 4. Production build
npm run build
npm start
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Base URL for FastAPI backend (default `/api` which proxies to `http://127.0.0.1:8000`).
