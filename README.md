# AMPscan: Binary Antimicrobial Peptide Classifier
  
Internal SIH-style hackathon (NIT Raipur, **PS20**). 
Official problem title: *AI-Based Protein and Biomolecule Classification Assistant*.

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

## References

These are the **upstream papers we actually used** (data, clustering, encoder, calibration). There is no AMPscan journal article.

1. **Ma T, et al.** DRAMP 4.0: an open-access data repository dedicated to the clinical translation of antimicrobial peptides. *Nucleic Acids Research* 53(D1):D403–D410 (2025). [doi:10.1093/nar/gkae1046](https://doi.org/10.1093/nar/gkae1046) — **AMP sequences (DRAMP General).**

2. **Shi G, et al.** DRAMP 3.0: an enhanced comprehensive data repository of antimicrobial peptides. *Nucleic Acids Research* 50(D1):D488–D496 (2022). [doi:10.1093/nar/gkab651](https://doi.org/10.1093/nar/gkab651)

3. **Li C, Sutherland D, Hammond SA, et al.** AMPlify: attentive deep learning model for discovery of novel antimicrobial peptides effective against WHO priority pathogens. *BMC Genomics* 23:77 (2022). [doi:10.1186/s12864-022-08310-4](https://doi.org/10.1186/s12864-022-08310-4) — **method and negative-class construction.**

4. **Li C, Warren RL, Birol I.** Models and data of AMPlify: a deep learning tool for antimicrobial peptide prediction. *BMC Research Notes* 16:11 (2023). [doi:10.1186/s13104-023-06279-1](https://doi.org/10.1186/s13104-023-06279-1) · data: [10.5281/zenodo.7320306](https://doi.org/10.5281/zenodo.7320306) — **non-AMP FASTAs.**

5. **Lin Z, Akin H, Rao R, et al.** Evolutionary-scale prediction of atomic-level protein structure with a language model. *Science* 379:1123–1130 (2023). [doi:10.1126/science.ade2574](https://doi.org/10.1126/science.ade2574) — **ESM-2** (`esm2_t12_35M_UR50D`, `esm2_t30_150M_UR50D`).

6. **Steinegger M, Söding J.** MMseqs2 enables sensitive protein sequence searching for the analysis of massive data sets. *Nature Biotechnology* 35:1026–1028 (2017). [doi:10.1038/nbt.3988](https://doi.org/10.1038/nbt.3988) — **homology clustering / split.**

7. **Guo C, Pleiss G, Sun Y, Weinberger KQ.** On calibration of modern neural networks. *ICML* (2017). [doi:10.48550/arXiv.1706.04599](https://doi.org/10.48550/arXiv.1706.04599) — **temperature scaling** (CNN / ESM heads).

Data licenses (CC BY 4.0 for DRAMP and AMPlify): [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md). Code in this repo is MIT (`LICENSE`).
