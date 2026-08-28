# Comprehensive Landscape of State-of-the-Art AMP Prediction Tools vs. AMPscan

**Project**: AMPscan (`/home/sudheesh02/SIH TEST`)  
**Date**: August 24, 2026  

---

## 1. Executive Summary & Landscape Map

Computational identification of Antimicrobial Peptides (AMPs) spans several distinct approaches:
- **Attentive & Recurrent Deep Learning:** AMPlify (BiLSTM + Self-Attention)
- **Metagenomic / Genomic Mining:** Macrel (Random Forest + 22 PhysChem, Contigs/Reads, Hemolysis)
- **MIC & Regression Modeling:** zswitten/Antimicrobial-Peptides (CNN/RNN + GRAMPA MIC database)
- **Short-Peptide Specialists (<=30 aa):** Deep-AmPEP30 (1D-CNN + PseKRAAC), sAMPpred-GAT (GAT + AlphaFold2 3D Contacts)
- **Physicochemical Matrix Encodings:** AI4AMP (1D-CNN-BiLSTM + PC6 Matrix)
- **Sliding-Window Proteome Scanning:** AmpGram (2-Level Stacked RF + n-grams)
- **Multi-Activity / Multi-Label:** iAMP-2L (PseAAC + SVM/KNN), AMPfun (RF/SVM + 2,500 features)
- **Translational Safety Filters:** HemoPI-2 / HemoPred (Hemolysis), ToxinPred3 (Cytotoxicity)
- **Our System (AMPscan):** Homology-isolated 30% MMseqs2 split (21,337 peptides), Platt-calibrated Random Forest (ECE=0.023, ROC-AUC=0.9515), 1D-CNN Integrated Gradients explainability, FastAPI + Next.js interactive studio.

---

## 2. Top Tools Comparison Table

| Tool | GitHub Repo | Architecture | Input / Features | Primary Scope | Calibrated? | Leakage Control |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AMPscan** *(Ours)* | Local / Open-Source | Platt RF (Primary) + 1D-CNN (Explainability) | 425-D AAC, DPC, PhysChem | Binary AMP (5–100 aa) | **Yes (ECE=0.023)** | **MMseqs2 @ 30% ID** |
| **AMPlify** | `bcgsc/AMPlify` | BiLSTM + Multi-Head Self-Attention | Learned Token Embeddings | Binary AMP; Genome Mining | No | CD-HIT @ 40% & 90% |
| **zswitten AMP** | `zswitten/Antimicrobial-Peptides` | CNN / RNN / Character-level DL | One-Hot / Character sequences | MIC Regression & E. coli / P. aeruginosa | No | Random / CD-HIT splits |
| **Macrel** | `BigDataBiology/macrel` | Ensemble Random Forest | 22 PhysChem Descriptors | Metagenomic Contigs, Reads, Hemolysis | No | CD-HIT @ 40%–50% |
| **Deep-AmPEP30** | `cbbio/AxPEP` | 1D-CNN | PseKRAAC (Reduced Alphabet) | Short AMPs (<=30 aa) | No | CD-HIT @ 50% |
| **sAMPpred-GAT** | `HongWuL/sAMPpred-GAT` | Graph Attention Network (GAT) | 3D Contact Matrix + ESM Embeddings | Short AMPs + Structure | No | CD-HIT @ 40% |
| **AI4AMP** | `LinTzuTang/AI4AMP_predictor` | 1D-CNN + BiLSTM + Attention | PC6 (6 PhysChem Properties) | Binary AMP; Template for AVP/ACP | No | CD-HIT @ 40% |
| **AmpGram** | `michbur/AmpGram` | 2-Level Stacked Random Forest | Informative n-grams via QuiPT | Full Proteomes, 10-mer Hotspots | No | CD-HIT @ 50% |
| **iAMP-2L** | Chou Lab / Benchmark Lists | 2-Level SVM + ML-FKNN | PseAAC | 5 Target Activities | No | CD-HIT @ 40% |
| **HemoPI-2** | `raghavagps/hemopi2` | Random Forest / SVM | AAC, DPC, PseAAC | Hemolytic Toxicity (% RBC Lysis) | No | CD-HIT @ 70%–90% |
| **AMPScanner v2**| `dan-veltri/amp-scanner-v2` | 1D-CNN + LSTM | Character Vectors | Binary AMP | No | CD-HIT @ 40% |
| **AMPfun** | `fdblab.csie.ncu.edu.tw` | Multi-Task RF & SVM | 2,500+ Compositional Descriptors | Gram+, Gram-, Fungus, Virus | No | CD-HIT @ 70% |
