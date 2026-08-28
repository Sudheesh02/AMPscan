# Tool Profile: AMPlify (bcgsc/AMPlify)

**Published**: *BMC Genomics* 23:77 (2022); Data Note: *BMC Res Notes* 16:11 (2023)  
**Authors**: Chengyu Li, Dan Sutherland, Shaun A. Hammond, Caren Yang, Olena I. Taho, Nicholas K. Bergman, Inanc Birol (BC Cancer Genome Sciences Centre)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: 5-Fold Ensemble of Deep Attentive Bidirectional Recurrent Neural Networks.
- **Pipeline**:
  1.  with zero-padding masking for variable lengths (2 to 200 aa).
  2.  $	o 200 	imes 1024$ hidden representation.
  3.  for multi-hop residue-residue relationships.
  4. Hierarchical Context  layer collapsing time steps into a 512-D context vector.
  5.  predicting (	ext{AMP})$.
- **Models Provided**:
  - : 5 models trained on 1:1 AMP vs non-AMP data (3,110 pos / 3,110 neg).
  - : 5 models trained on 1:6 ratio (3,110 pos / 15,550 neg) for genomic candidate mining.

---

## 2. Benchmark Performance on Locked 30% Homology Test Set (Cohort 1, N=3,230)
- **ROC-AUC**: **0.9277** (vs AMPscan RF **0.9515**, Macrel **0.9491**)
- **PR-AUC**: **0.9450**
- **Accuracy**: **0.8558** (MCC: **0.7313**)
- **Calibration Error ($	ext{ECE}_{15}$)**: **0.1183** (Significant overconfidence compared to AMPscan Platt RF at **0.0235**)
- **Throughput**: **14.88 seq/s** on CPU (evaluated across 5 BiLSTM passes per sequence).
- **Skipped Sequences**: 48 sequences containing ambiguous amino acid  (strictly rejects non-standard residues).

---

## 3. Strengths vs. AMPscan
1. **End-to-End Attentive Representation**: Models long-range residue dependencies without manual feature engineering.
2. **Native Self-Attention Attribution**: Extracts attention $lpha_t$ weights during forward pass.
3. **In Vitro Validated**: Authors validated top predictions experimentally against WHO priority pathogens (*E. coli*, *S. aureus*).

---

## 4. Weaknesses & Pitfalls
1. **Slow Inference**: 14.9 seq/s makes screening large 100k+ metagenomic libraries cumbersome.
2. **Poor Calibration ($	ext{ECE} = 0.118$)**: Saturated probabilities distort downstream triage economics.
3. **Generalization Drop on Strict Clusters**: ROC-AUC drops from published >0.98 to 0.9277 when tested on truly novel sequence clusters ($<30\%$ sequence identity).

---

## 5. Genuine Integration Potential for AMPscan
- **Hybrid Context Embedding**: Extract the 512-D context vector from AMPlify's attention layer and append it to AMPscan's 425-D tabular vector.
- **Dual Attribution Visualizer**: Display AMPlify's attention maps side-by-side with AMPscan's 1D-CNN Integrated Gradients heatmaps in the UI.
