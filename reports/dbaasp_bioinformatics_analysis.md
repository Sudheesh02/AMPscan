# Comprehensive Bioinformatics & Dataset Analysis: DBAASP Dataset Integration

**Project**: AMPscan (`/home/sudheesh02/SIH TEST`)  
**Target**: DBAASP Master Dataset (`DBAASP/master_DBAASP.csv`, `DBAASP/master_DBAASP.fasta`) vs. Existing Baseline (`data/raw/`, `data/processed/`, `data/splits/`)  
**Date**: August 24, 2026

---

## Executive Summary

An exhaustive bioinformatics inspection and quantitative overlap analysis of the newly merged **DBAASP** dataset was conducted against the existing **AMPscan** project dataset (derived from DRAMP 3.0/4.0 and AMPlify).

### Key Findings:
1. **DBAASP Dataset Scale**: 
   - `master_DBAASP.csv` contains **25,070 peptide records** across 9 annotation fields.
   - `master_DBAASP.fasta` contains **24,400 monomeric sequence records**.
   - Complexity breakdown: **24,398 Monomers (97.32%)**, **436 Multimers (1.74%)**, and **236 Multi-Peptides (0.94%)**.
   - Synthesis provenance: **20,907 Synthetic (83.39%)**, **3,324 Ribosomal/Natural (13.26%)**, and **839 Nonribosomal (3.35%)**.
2. **Truly Novel Sequences for AMPscan**:
   - Current AMPscan positive baseline: **10,678 unique cleaned DRAMP positive sequences**.
   - Shared overlap between DRAMP natural AMPs and DBAASP: **~2,350 sequences** (core natural AMP universe).
   - **~15,500 to ~16,200 unique DBAASP positive sequences are TRULY NOVEL** to AMPscan (never seen in `data/raw/general_amps.fasta` or `data/processed/`).
   - Novelty is heavily concentrated in the **synthetic design space (83.4%)**, including de novo designed AMPs, alanine scans, stereoisomers, and truncated pharmacophores.
3. **Target & Multi-Property Annotations**:
   - DBAASP provides rich multi-label biological annotations: **Gram- (19,943 records, 79.55%)**, **Gram+ (19,302 records, 77.00%)**, **Mammalian Cell / Hemolysis (13,885 records, 55.39%)**, **Fungus (6,960 records, 27.76%)**, **Cancer (4,279 records, 17.07%)**, **Virus (1,581 records, 6.31%)**, and **Biofilm (689 records, 2.75%)**.
   - Primary Mechanism of Action: **Lipid Bilayer (20,631 records, 82.29%)**, followed by **Virus Entry (845 records)**, **Cytoplasmic Protein (550 records)**, **DNA/RNA (416 records)**, and **Membrane Protein (361 records)**.
4. **Chemical Diversity & Modifications**:
   - **45.17% (11,325 entries)** have C-terminal amidation (`AMD`).
   - **5.19% (1,302 entries)** have N-terminal acetylation (`ACT`).
   - **2.31% (~580 entries)** feature N-terminal lipidations/fatty acids (e.g., C16 palmitoyl, C12 lauroyl, C8 octanoyl).
   - **11.54% (2,893 entries)** incorporate D-amino acids (encoded as lowercase).
   - **19.15% (4,800 entries)** contain non-canonical / modified amino acid residues (`X`).

---

## 1. Existing Project Baseline (`data/`)

### 1.1 Positives & Negatives Composition
- **Positives Source**: DRAMP (General AMPs, `data/raw/general_amps.fasta`, CC BY 4.0, 11,687 raw records).
- **Negatives Source**: AMPlify benchmark (`data/raw/AMPlify_non_AMP_*.fa`, CC BY 4.0, 4,173 balanced + 128,445 imbalanced pool).
- **Curation Protocol (`scripts/build_amp_dataset.py`)**:
  - Length filter: 5 <= len <= 100 aa (11,459 positives passed; 228 dropped).
  - Alphabet filter: Uppercase normalization; ambiguous/non-standard translation (`B, Z, U, O, J -> X`); leftover non-AA dropped (418 mapped, 48 dropped).
  - Deduplication: Exact sequence deduplication (733 duplicates dropped).
  - Cross-class conflicts: 19 identical sequences found in positive and negative pools; resolved in favor of positives (negatives dropped).
  - **Final Cleaned Baseline**: **10,678 Positives**, **10,659 Negatives** (**21,337 total clean peptides**).

### 1.2 MMseqs2 Homology Splitting
- MMseqs2 clustering: `--min-seq-id 0.3 -c 0.8 --cov-mode 1`.
- Total clusters: **9,241** (4,778 positive-only, 4,391 negative-only, 72 mixed).
- Cluster-level 70/15/15 split:
  - **Train**: 14,904 sequences (7,444 pos, 7,460 neg)
  - **Val**: 3,203 sequences (1,611 pos, 1,592 neg)
  - **Test**: 3,230 sequences (1,623 pos, 1,607 neg)

---

## 2. Biological Target & Mechanism Quantification

### 2.1 Target Group Annotation (`TARGET GROUP`)
```
Gram-Negative Bacteria (Gram-)      ████████████████████████  19,943 (79.55%)
Gram-Positive Bacteria (Gram+)      ███████████████████████   19,302 (77.00%)
Mammalian Cell (Cytotoxicity/Hem.)   ████████████████          13,885 (55.39%)
Fungus / Yeast (Antifungal)         ████████                  6,960  (27.76%)
Cancer Cells (Anticancer)           █████                     4,279  (17.07%)
Virus (Antiviral)                   ██                        1,581  (6.31%)
Biofilm (Anti-biofilm)              █                         689    (2.75%)
Parasite / Protozoa                 ▌                         440    (1.76%)
```

### 2.2 Mechanism of Action (`TARGET OBJECT`)
- **Lipid Bilayer**: 20,631 records (82.29%) — pore formation, carpet / barrel-stave models.
- **Virus Entry**: 845 records (3.37%) — targeting gp120, gp41, viral capsids.
- **Cytoplasmic Protein**: 550 records (2.19%) — ribosome / chaperone DnaK inhibition.
- **DNA / RNA**: 416 records (1.66%) — nucleic acid binding.
- **Membrane Protein**: 361 records (1.44%) — outer membrane translocons, TolC.
