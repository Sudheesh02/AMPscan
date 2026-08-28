# AMPscan Study Guide — Member 4
## Bioinformatics & Homology Control Lead

---

### 1. Primary Datasets, Sourcing & Licenses

| Role | Source Database | Raw Records | Cleaned Records | License | Key References |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Positives (AMPs)** | **DRAMP General** FASTA (`general_amps.xlsx` / raw FASTA) | 11,687 | **10,678** | CC BY 4.0 | Ma et al. *Nucleic Acids Res* (2025); Shi et al. *Nucleic Acids Res* (2022) |
| **Negatives (Non-AMPs)** | **AMPlify** Published Non-AMP Pools (Zenodo `10.5281/zenodo.7320306`) | 4,173 (balanced) + 6,579 (imbalanced) | **10,659** | CC BY 4.0 | Li et al. *BMC Genomics* (2022); *BMC Res Notes* (2023) |
| **Total Clean Dataset** | **Combined Benchmark Dataset** | **22,439** | **21,337** | CC BY 4.0 | **AMPscan Locked Dataset** |

#### Why AMPlify Published Negatives Were Selected (Scientific Justification)
- "Non-AMP" is **not an innate biological category**; it is an operational negative class. 
- Ad-hoc scraping of UniProt Swiss-Prot with home-made keyword filters (e.g., filtering out "antimicrobial") introduces subtle ascertainment biases, length distribution mismatches, and unverified negative labels.
- The AMPlify negative pool was derived from UniProt with strict length-matching, subcellular localization balance, and peer-reviewed documentation specifically calibrated for machine learning classifiers.
- To balance the 10,678 clean DRAMP positives, AMPscan initially ingested the 4,173 balanced AMPlify negatives and augmented them with 6,579 sequences from the published AMPlify imbalanced set, achieving a near-perfect balanced pool of **21,337 peptides**.

---

### 2. Data Cleaning & Sanitization Pipeline (Exact Attrition Table)

```
Raw Data Ingestion (11,687 DRAMP AMPs + 4,173 AMPlify Non-AMPs)
   │
   ▼
[Step 1: Length Filtering] ──> Enforce 5 ≤ Length ≤ 100 aa (drops 228 AMPs, 74 Non-AMPs)
   │
   ▼
[Step 2: Non-Standard AA Mapping] ──> Map B, Z, U, O, J → X (418 AMPs mapped; 0 Non-AMPs)
                                      Drop remaining non-alphabet chars (48 AMPs dropped)
   │
   ▼
[Step 3: Exact Deduplication] ──> Keep first occurrence (drops 733 duplicate AMPs)
   │
   ▼
[Step 4: Negative Augmentation] ──> Add 6,579 clean records from AMPlify imbalanced pool
   │
   ▼
[Step 5: Conflict Resolution] ──> 19 identical sequences present in both AMP & Non-AMP
                                  Resolved by retaining as AMP (Positives)
   │
   ▼
Final Cleaned Corpus: 10,678 AMPs + 10,659 Non-AMPs = 21,337 Sequences
```

#### Step-by-Step Cleaning Rules & Statistics

| Stage / Transformation Step | AMP Count | Non-AMP Count | Total Count | Drop / Transformation Notes |
| :--- | :---: | :---: | :---: | :--- |
| **1. Raw Ingestion** | 11,687 | 4,173 | 15,860 | DRAMP General + AMPlify Balanced |
| **2. Length Filter ($5 \le L \le 100$)** | 11,459 | 4,099 | 15,558 | Excluded short oligomers ($<5$) and large proteins ($>100$) |
| **3. Alphabet Mapping & Sanitization** | 11,411 | 4,099 | 15,510 | $B, Z, U, O, J \to X$ (418 AMPs); 48 AMPs with invalid chars dropped |
| **4. Exact Sequence Deduplication** | 10,678 | 4,099 | 14,777 | Redundant identical sequences collapsed |
| **5. Imbalanced Pool Augmentation** | 10,678 | 10,678 | 21,356 | $+6,579$ length-matched non-AMPs from AMPlify pool |
| **6. Cross-Label Conflict Resolution** | **10,678** | **10,659** | **21,337** | **19 conflicts resolved in favor of AMP** |

---

### 3. MMseqs2 Homology Clustering & Split Protocol

#### Clustering Command & Parameters
AMPscan used MMseqs2 (`easy-cluster`) to enforce strict homology separation across training, validation, and testing folds:

$$\text{Command: } \texttt{mmseqs easy-cluster data/processed/clean.fasta clusterRes tmp --min-seq-id 0.3 -c 0.8 --cov-mode 1}$$

- `--min-seq-id 0.3`: Sequences sharing $\ge 30\%$ sequence identity in aligned regions cluster together.
- `-c 0.8`: Requires at least **80% alignment coverage**.
- `--cov-mode 1`: Coverage is calculated relative to the **shorter sequence** in the pair:
  $$\text{Coverage} = \frac{\text{Aligned Residues}}{\text{Length of Shorter Peptide}} \ge 0.80$$
  *Why `--cov-mode 1` is critical:* Prevents a 15-aa AMP from appearing unrelated to an 80-aa non-AMP peptide when the 15-aa sequence is fully embedded inside the longer sequence.

#### Cluster Stratification & Fold Partitioning
- **Total Clusters Generated:** **9,241 MMseqs2 clusters**
  - AMP-only clusters: **4,778**
  - Non-AMP-only clusters: **4,391**
  - Mixed clusters: **72**
- **Partitioning Strategy:** Whole clusters were assigned atomically to a single split (70% Train / 15% Val / 15% Test) with cluster-level stratification based on positive/negative composition (Random Seed: `42`).

| Split Fold | Total Peptides | AMP (Positives) | Non-AMP (Negatives) | Clusters Count | Fold % (Target 70/15/15) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Train Fold** | **14,904** | 7,444 | 7,460 | 6,469 | 69.85% |
| **Validation Fold** | **3,203** | 1,611 | 1,592 | 1,386 | 15.01% |
| **Test Fold (Locked)**| **3,230** | 1,623 | 1,607 | 1,386 | 15.14% |
| **Total** | **21,337** | **10,678** | **10,659** | **9,241** | **100.00%** |

---

### 4. Homology Leakage vs. Random Split Experiment

To quantify the exact scientific distortion caused by **homology leakage** (where evolutionary cousins appear in both train and test sets), AMPscan generated a twin **random stratified split** (70/15/15, Seed 42) on the exact same 21,337 peptides.

| Architecture / Model | Random Split ROC-AUC *(Leaky)* | Homology Split ROC-AUC *(Locked Honest)* | Performance Inflation ($\Delta$ Leakage Gap) |
| :--- | :---: | :---: | :---: |
| **Random Forest (Primary)** | **0.9791** | **0.9515** | **+0.0276** (+2.76%) |
| **ESM-2 35M + Linear Head** | **0.9657** | **0.9450** | **+0.0207** (+2.07%) |
| **1D-CNN (One-Hot)** | **0.9749** | **0.9424** | **+0.0325** (+3.25%) |

```
Homology Split (Honest, 30% MMseqs2):   ████████████████████████ 0.9515
Random Split (Leaky, Family Memorized): ███████████████████████████ 0.9791  (+0.0276 Leakage Artifact)
```

**Takeaway for Judges:** In naive random splits, models memorize family-level sequence patterns instead of discovering generalizable antimicrobial motifs. Quoting 0.98+ ROC-AUC is a scientific failure of split design. AMPscan's true generalization capacity is **0.9515**.

---

### 5. Detailed Audit of the 72 Mixed Clusters

A mixed cluster occurs when an MMseqs2 cluster contains at least one AMP (DRAMP) and at least one non-AMP (AMPlify).

#### Mixed Cluster Key Statistics

| Property | Value | Scientific Explanation |
| :--- | :---: | :--- |
| **Total Mixed Clusters** | **72** | Only 0.78% of all 9,241 clusters contain mixed labels. |
| **Distribution Across Folds** | **47 Train / 15 Val / 10 Test** | Whole mixed clusters are assigned to a single fold; **zero cross-fold leakage**. |
| **Total Peptides in Mixed Clusters** | **709** (264 AMPs, 445 Non-AMPs) | 3.32% of total dataset sequences. |
| **Cluster Size Range** | Min: 2, Median: 5, Max: 73 | Representative examples span small pairs to large families. |
| **Mean Peptide Length** | **AMPs: 46.6 aa** vs. **Non-AMPs: 62.9 aa** | Non-AMPs are ~16.3 residues longer on average. |

#### Root Cause Analysis
Under MMseqs2 `--cov-mode 1`, coverage is computed against the shorter sequence. Short antimicrobial fragments (e.g., 20–40 aa) align with $\ge 30\%$ identity across a sub-region of a longer UniProt peptide (e.g., 70–90 aa). This reflects genuine biological sequence overlap rather than an operational data error.

---

### 6. Top 5 Judge Defense Questions & Verbatim Answers

**Q1: Why did you cluster at 30% sequence identity instead of standard 70% or 90%?**  
> *"30% identity is the structural homology threshold where proteins adopt similar tertiary folds. Clustering at 70% or 90% leaves distantly related homologs across train and test sets, allowing models to cheat by memorizing family features. A 30% MMseqs2 split is significantly more rigorous and reflects true discovery of novel AMP chemotypes."*

**Q2: What is `--cov-mode 1` and why was it necessary?**  
> *" `--cov-mode 1` calculates coverage based on the shorter sequence. Because our peptides vary from 5 to 100 residues, a 20-aa AMP aligning against an 80-aa protein covers only 25% of the long protein, but 100% of the short peptide. Without `--cov-mode 1`, that pair would bypass the cluster wall and leak into opposite folds."*

**Q3: Did your 72 mixed clusters leak across the train and test splits?**  
> *"No. Every single mixed cluster was assigned in its entirety to either train, validation, or test. Zero sequences leaked across folds. The 72 mixed clusters simply demonstrate that 30% identity allows short AMP fragments to align with unannotated UniProt peptides. We audited and documented all 72 clusters in `reports/mixed_clusters.md`."*

**Q4: Why didn't you build a 10-class AMP family classifier using DRAMP's family labels?**  
> *"We ran a formal audit on DRAMP's `Family` column. 54.7% of sequences have missing labels, and the largest classes are actually viral taxa like *Retroviridae* rather than AMP structural classes. Furthermore, strict 30% clustering places entire families into single folds (e.g., Cyclotides have 79 sequences in val and only 1 in test). Training a classifier on that data would be scientifically invalid."*

**Q5: Why did you resolve duplicate conflicts in favor of AMPs?**  
> *"In public databases, active peptides are occasionally present in general proteomic releases without functional annotation. Given experimental curation from DRAMP, active annotations take precedence over unannotated negative controls."*

---

### 7. Spoken Presentation Scripts

#### 30-Second Intro Script:
> *"I lead the bioinformatics data engineering and homology control for AMPscan. The critical pitfall in peptide ML is homology leakage, where models memorize gene families across random splits. We curated 21,337 clean sequences and clustered them with MMseqs2 at 30% sequence identity and 80% coverage on the shorter sequence, ensuring true biological holdout evaluation."*

#### 60-Second Deep-Dive Script:
> *"We ingested 10,678 verified AMPs from DRAMP General and 10,659 length-matched non-AMPs from AMPlify's peer-reviewed negative pool. To eliminate homology leakage, we clustered the complete 21,337-peptide corpus using MMseqs2 with --min-seq-id 0.3, -c 0.8, and --cov-mode 1, ensuring coverage is computed relative to the shorter peptide.
> 
> We partitioned the 9,241 resulting clusters into a strict 70/15/15 split. While a naive random split produces an inflated ROC-AUC of 0.9791, our homology holdout reveals the true generalizable performance of 0.9515. We also audited 72 mixed clusters where short AMPs aligned with longer UniProt peptides, confirming all 72 were placed atomically into single folds with zero cross-fold leakage."*
