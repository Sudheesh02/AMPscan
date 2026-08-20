# AMPscan: Binary Antimicrobial Peptide Classifier

Official SIH Internal Hackathon (PS20) title: *AI-Based Protein and Biomolecule Classification Assistant*.

**Scope:** peptides of length **5–100 aa**, binary **AMP vs non-AMP**. Not all proteins, not Gene Ontology, not Pfam, not a wet-lab assay.

Primary score in the demo: **Platt-calibrated Random Forest**. Homology-split metrics are the honest numbers. Random-split metrics are a leakage control only.

Hardware used: NVIDIA GeForce RTX 5060 Laptop GPU (**8 GB VRAM**), 16 GB RAM.

Full study document: [`reports/defense/AMPscan_Study_Guide.pdf`](reports/defense/AMPscan_Study_Guide.pdf) (also [`reports/STUDY_GUIDE.md`](reports/STUDY_GUIDE.md)).

## How to run Streamlit

From this directory, with a Python env that has the packages in `scripts/` (see local `amp-data` conda env if you have the full laptop snapshot):

```bash
streamlit run app/streamlit_app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

- **Predict** — paste one sequence or upload FASTA (max 50). Invalid length/alphabet errors out.
- **Metrics** — locked homology vs random table, calibration ECE, limitations.

Weights and FASTAs are **not** in this GitHub snapshot (see `.gitignore`). You need the local `models/` and `data/` trees to run inference.

## Locked homology-test metrics

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| **RF (Phase 2, primary)** | 0.8734 | 0.8734 | **0.9515** | 0.9542 |
| ESM-2 35M linear, frozen (Phase 3) | 0.8622 | 0.8622 | 0.9450 | 0.9424 |
| 1D-CNN (Phase 4) | 0.8650 | 0.8648 | 0.9424 | 0.9465 |
| ESM-2 150M linear, frozen (Phase 9) | 0.8762 | 0.8761 | 0.9521 | 0.9516 |

Phase 9 is a **tie** with RF (Δ +0.0006). Val was 0.9372, so LoRA was not run.

Random-split RF ROC-AUC is **0.9791** (leakage). Quote **0.9515**. Calibration does not change ROC-AUC; RF ECE 0.078 → 0.023 after Platt.

## Data (not vendored here)

Do **not** copy DRAMP/AMPlify FASTAs from this repo — they are gitignored.

| | |
| --- | --- |
| Positives | [DRAMP General](https://dramp.cpu-bioinfor.org/downloads/) FASTA, CC BY 4.0 |
| Negatives | [AMPlify](https://doi.org/10.5281/zenodo.7320306) published non-AMP FASTAs, CC BY 4.0 |
| Filters | length 5–100; B,Z,U,O,J → X; drop leftover non-AA |
| Split | MMseqs2 `easy-cluster --min-seq-id 0.3 -c 0.8 --cov-mode 1`, whole clusters, 70/15/15, seed 42 |
| Clean set | 10678 AMP + 10659 non-AMP |

Licenses and citations: [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md). Manifest: [`data/data_manifest.json`](data/data_manifest.json).

## Limitations (read before claiming)

- Pattern matching on a **balanced** peptide set, not MIC / in vivo activity.
- Magainin-2, LL-37, and melittin are in the **homology training set**. IG heatmaps of those peptides are not held-out discovery.
- 72 mixed AMP/non-AMP clusters exist; they stay in one fold. See `reports/LIMITATIONS.md` and `reports/mixed_clusters.md`.

## Repo layout

```
app/                 Streamlit demo
scripts/             build / train / calibrate / IG (reproduction; weights not included)
data/LICENSE_NOTES.md
data/data_manifest.json
data/splits/         IDs, split_stats, cluster_assignments (FASTAs gitignored)
reports/             phase reports, study guide, PDF
LICENSE              MIT for *code* only; sequences remain DRAMP/AMPlify CC BY 4.0
```

Local laptop only (gitignored, still on disk): `models/`, `data/raw/`, embeddings, FASTAs, `archive/`.
