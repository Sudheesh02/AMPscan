# AMPscan: Binary Antimicrobial Peptide Classifier

**Short name:** AMPscan  
Internal SIH-style hackathon (NIT Raipur, **PS20**). Official problem title: *AI-Based Protein and Biomolecule Classification Assistant*.

[![License: MIT (code)](https://img.shields.io/badge/license-MIT%20(code)-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-3776AB.svg)](https://www.python.org/)
[![Scope](https://img.shields.io/badge/scope-peptides%205–100%20aa-0B6E4F.svg)](#scope)
[![Honest split](https://img.shields.io/badge/split-MMseqs2%2030%25%20homology-C73E1D.svg)](#homology-split)

AMPscan tells you whether a **short peptide** looks like a known **antimicrobial peptide (AMP)** or not. It is a **homology-aware sequence-pattern classifier** with calibrated probabilities and residue-level CNN explanations — **not** a wet-lab assay, **not** Gene Ontology, **not** Pfam, **not** a full-protein annotator.

**Primary score (demo):** Platt-calibrated Random Forest **P(AMP)**  
**Honest metric:** homology-test ROC-AUC **0.9515** (RF). Random-split RF **0.9791** is leakage — do not quote it as the result.

Study pack for the team: [`reports/defense/AMPscan_Study_Guide.pdf`](reports/defense/AMPscan_Study_Guide.pdf) · [`reports/STUDY_GUIDE.md`](reports/STUDY_GUIDE.md)

---

## Scope

| In | Out |
| --- | --- |
| Peptides **5–100** amino acids | Full-length proteins |
| Binary **AMP vs non-AMP** | GO / Pfam / EC / DeepLoc |
| FASTA paste or upload (max 50) | MIC, hemolysis, in vivo claims |
| Homology cluster split + calibration + IG | Fine-tuned / LoRA ESM (not run) |

Hardware used to train and embed: **RTX 5060 Laptop GPU, 8 GB VRAM**, 16 GB RAM.

---

## What goes in, what comes out

**Input** (FASTA or raw letters):

```text
>example
GIGKFLHSAKKFGKAFVGEIMNS
```

Rules: length 5–100; `B/Z/U/O/J → X`; leftover non-AA → **error**.

**Output:**

| Field | Meaning |
| --- | --- |
| **RF P(AMP)** (calibrated) | **Primary** — trust this for the label |
| Label | `AMP` if RF P ≥ 0.5, else `non-AMP` |
| CNN P(AMP) | Secondary, temperature **T = 1.283** |
| length, net charge (pH 7), GRAVY | Simple peptide properties |
| CNN IG heatmap | Which residues push the CNN logit — **not** a mechanism |

Magainin-2, LL-37, and melittin are in the **homology training set**. The app banners that. Do not present them as held-out proof.

---

## Locked homology-test metrics

Cluster split: MMseqs2 `easy-cluster --min-seq-id 0.3 -c 0.8 --cov-mode 1`, whole clusters, 70/15/15, seed 42. Test **n = 3230**.

| model | accuracy | macro-F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| **Random Forest (primary)** | 0.8734 | 0.8734 | **0.9515** | 0.9542 |
| Frozen ESM-2 35M + linear | 0.8622 | 0.8622 | 0.9450 | 0.9424 |
| 1D-CNN (one-hot) | 0.8650 | 0.8648 | 0.9424 | 0.9465 |
| Frozen ESM-2 150M + linear | 0.8762 | 0.8761 | 0.9521 | 0.9516 |

ESM-2 150M vs RF: **Δ +0.0006** → **tie**. 150M val ROC-AUC was **0.9372**, so LoRA was **not** run.

Random-split RF ROC-AUC **0.9791** is the leaky number. **Quote 0.9515.**

Calibration (homology test, 15-bin ECE): RF **0.078 → 0.023** (Platt, not temperature). CNN **T = 1.283**. ROC-AUC unchanged.

---

## Homology split (why this repo exists)

Random train/test puts **close homologs on both sides**. The model memorizes families and looks 98%. We clustered at **30% identity**, **80% coverage on the shorter sequence**, and assigned **whole clusters** to train **or** val **or** test.

- **21,337** cleaned peptides (10,678 AMP + 10,659 non-AMP)
- **9,241** clusters; **72 mixed** (AMP and non-AMP together — still one fold)
- Details: [`reports/mixed_clusters.md`](reports/mixed_clusters.md)

```text
download DRAMP + AMPlify
        → clean (5–100, alphabet, dedup)
        → MMseqs2 cluster 30%
        → whole cluster → train / val / test
        → RF (composition)  |  frozen ESM  |  1D-CNN
        → calibrate (Platt / T)
        → Streamlit: RF primary, CNN IG
```

---

## How to run the demo

Weights and FASTAs are **not** in this GitHub snapshot (`.gitignore`). Inference needs the local `models/` and `data/` trees on the machine that trained them.

```bash
streamlit run app/streamlit_app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

- **Predict** — paste a sequence or upload FASTA (cap 50)
- **Metrics** — locked tables + limitations

---

## Data (not vendored)

Do **not** expect FASTAs in this clone. Reconstruct from upstream:

| Role | Source | License |
| --- | --- | --- |
| Positives | [DRAMP General](https://dramp.cpu-bioinfor.org/downloads/) | CC BY 4.0 |
| Negatives | [AMPlify non-AMP FASTAs](https://doi.org/10.5281/zenodo.7320306) | CC BY 4.0 |

Cleaning: length 5–100; `B,Z,U,O,J → X`; exact-seq dedup; cross-class duplicate → keep AMP (19 cases).  
Provenance: [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md) · [`data/data_manifest.json`](data/data_manifest.json).

**Code** in this repo is MIT (`LICENSE`). We do **not** own DRAMP/AMPlify sequences.

---

## Limitations (say these out loud)

1. Pattern matching on a **balanced** test, not a proteome (AMP prevalence is tiny).
2. Non-AMP means “not annotated AMP,” not “experimentally inactive.”
3. DRAMP General includes **synthetic** AMPs — composition models like that.
4. Famous peptides in the IG demo are **training examples**.
5. Not MIC, hemolysis, GO, or Pfam. Full list: [`reports/LIMITATIONS.md`](reports/LIMITATIONS.md).

---

## Repo layout

```
app/streamlit_app.py          demo (Predict + Metrics)
scripts/                      reproduction (weights not in git)
data/LICENSE_NOTES.md         DRAMP / AMPlify licenses
data/splits/*_ids.txt         homology + random ID lists
reports/defense/*.pdf         full study guide
reports/phase_*_report.md     locked phase write-ups
LICENSE                       MIT for code only
```

On the laptop only (gitignored): `models/`, `data/raw/`, embeddings, FASTAs, `archive/`.

---

## Cite the data, not a fake paper

- DRAMP: Ma et al., *NAR* 2025; Shi et al., *NAR* 2022  
- AMPlify: Li et al., *BMC Genomics* 2022; Li et al., *BMC Res Notes* 2023  
