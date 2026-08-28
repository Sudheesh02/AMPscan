# Tool Codebase & Pre-trained Model Weights Inspection

**Project**: AMPscan Multi-Tool Benchmark (`/home/sudheesh02/SIH TEST`)  
**Date**: August 24, 2026

---

## Tool Runtime & Weights Inventory

| Repository | Primary Task | Model Architecture | Weights Included? | Runtime Requirements | Input Length | Readiness Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`AMPlify`** | Binary AMP Classif. | BiLSTM + Multi-Head Attention | Yes (10 H5 models, ~300 MB) | Python 3.6 / TF 1.12 / Keras 2.2 | 2 - 200 aa | **Needs Env Setup** |
| **`macrel`** | AMP & Hemolysis Classif. | Random Forest on 22 PhysChem | Yes (2 ONNX models, ~1.8 MB) | Python >= 3.10 / ONNX Runtime | < 100 aa | **Ready-to-Run** |
| **`AI4AMP_predictor`** | Binary AMP Classif. | 1D-CNN + BiLSTM on PC6 Matrix | Yes (1 H5 model, ~900 KB) | Python 3.x / Keras / TF | <= 200 aa | **Ready-to-Run** |
| **`Antimicrobial-Peptides`** | MIC Regression & Classif. | 1D-CNN Ensembles on GRAMPA | Yes (60 JSON + H5 models) | Python 3.x / TF 2.x / Keras | <= 50 aa | **Ready-to-Run** |
| **`peptidy`** | Feature Extraction | Vectorization Engine | N/A (Toolkit) | Pure Python >= 3.6 | Any | **Ready-to-Run** |
| **`sAMPpred-GAT`** | Short AMP Classif. | Graph Attention Net (GAT) | GAT Included (Ext. DBs needed) | PyTorch 1.11 / PyG / TF 1.14 | <= 30 aa | **Heavy Ext. Setup** |
| **`AmpGram`** | Full Proteome & 10-mers | 2-Level Stacked Random Forest | Needs GitHub R package | R >= 3.5 / `ranger` / `biogram` | >= 10 aa | **Needs R Setup** |
| **`HemoPred`** | Hemolysis Classif. | Random Forest on AAC/DPC | Self-contained (fits on fly) | R / `randomForest` / `protr` | Standard AA | **Needs R Setup** |
| **`hemopi2`** | Hemolysis Classif./Regr.| RF / MERCI / ESM2-t6 | Must download from IIITD | Python 3 / Transformers / Perl | <= 40 aa | **Needs Weight Download** |
| **`peptide-prediction-list`**| Literature Catalog | N/A (Bibliography) | N/A | Markdown / RDS | N/A | **Reference Only** |
