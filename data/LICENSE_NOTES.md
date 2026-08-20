# Data licenses and provenance — AMP vs non-AMP set

Built: 2026-08-19T10:41:40Z
Purpose: homology-aware AMP (1) vs non-AMP (0) peptide dataset. No model weights.

## Positives
Source used: DRAMP
File: data/raw/general_amps.fasta
URL: https://dramp.cpu-bioinfor.org/downloads/download.php?filename=download_data/DRAMP3.0_new/general_amps.fasta
Records in raw file: 11687
License: CC BY 4.0
Required citation:
- DRAMP 4.0: Ma et al., Nucleic Acids Research 53:D403–D410 (2025). https://doi.org/10.1093/nar/gkae1046
- DRAMP 3.0: Shi et al., Nucleic Acids Research 50:D488–D496 (2022). PMID 34390348

DRAMP license confirmation: https://dramp.cpu-bioinfor.org/downloads/ and the homepage state the data are CC BY 4.0.

## Negatives
Source used: AMPLIFY
Files: data/raw/AMPlify_non_AMP_train_balanced.fa, data/raw/AMPlify_non_AMP_test_balanced.fa, data/raw/AMPlify_non_AMP_train_imbalanced.fa, data/raw/AMPlify_non_AMP_test_imbalanced.fa
Imbalanced AMPlify negatives added: True
URL / DOI: 10.5281/zenodo.7320306 (CC BY 4.0)
Citation: Li, Sutherland, Hammond et al., BMC Genomics 23:77 (2022);
          Li, Warren & Birol, BMC Research Notes 16:11 (2023).
MD5 (Zenodo):
- AMPlify_non_AMP_train_balanced.fa   7652c9ab3b42404d8a037ed22825bd97
- AMPlify_non_AMP_test_balanced.fa    7dbc53abf6fcd66c0ad64d9e7925b476
- AMPlify_non_AMP_train_imbalanced.fa 7f4d2514935597b0c0a073bd2acbb5a6
- AMPlify_non_AMP_test_imbalanced.fa  35c764b23c325e0ff0c5b0741ecc1f6f

## Preprocessing
- Length 5–100 inclusive
- Uppercase; B,Z,U,O,J mapped to X; leftover non-AA dropped (X allowed)
- Exact sequence dedup, keep first
- Cross-class exact duplicate → keep positive
- Final cleaned: 10678 positives, 10659 negatives
  (19 cross-class conflicts resolved)
See data/processed/preprocess_counts.json and alphabet_filter_counts.json

## Homology split
mmseqs easy-cluster combined_clean.fasta \
  --min-seq-id 0.3 -c 0.8 --cov-mode 1
Whole clusters assigned to train/val/test (targets 70/15/15, seed 42),
stratified by pos_only / neg_only / mixed. A cluster is never split.
Clusters: total=9241 pos_only=4778 neg_only=4391 mixed=72
Homology fold sizes: train=14904 (pos=7444 neg=7460), val=3203 (pos=1611 neg=1592), test=3230 (pos=1623 neg=1607)

## Random-split control (not for primary evaluation)
Same cleaned sequences, clusters ignored, 70/15/15, seed 42, stratified by class.
Files: data/splits/random_*
Random fold sizes: train=14936 (pos=7475 neg=7461), val=3201 (pos=1602 neg=1599), test=3200 (pos=1601 neg=1599)
