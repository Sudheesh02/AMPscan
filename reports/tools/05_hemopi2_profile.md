# Tool Profile: hemopi2 (raghavagps/hemopi2)

**Published**: *Communications Biology* 8:176 (2025)  
**Authors**: Archana Rathore, Sherry Bhalla, Gajendra P. S. Raghava (IIIT-Delhi)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Objective**: Binary classification of mammalian erythrocyte hemolysis and regression of hemolytic concentration ($	ext{HC}_{50} / 	ext{EC}_{50}$ in $\mu	ext{M}$).
- **Components**:
  1. **Random Forest Classifier**: Trained on 654 Pfeature descriptors (AAC, DPC, ATC, BTC, PCP, PAAC, QSO, CTD).
  2. **Fine-Tuned ESM-2**:  (6 layers, 320 hidden dims) fine-tuned for sequence-level hemolytic classification.
  3. **MERCI Motif Search**: Searches positive/negative motif matches with heuristic $\pm 0.5$ score shifts.
  4. **Random Forest Regressor**:  (97.8 MB) predicting continuous $	ext{HC}_{50}$ in $\mu	ext{M}$.

---

## 2. Pretrained Model Weights Status
- Pretrained weights are installed in :
  -  (5.85 MB)
  -  (97.79 MB)
  -  (31.41 MB ESM-2 checkpoint)
  -  & 

---

## 3. Strengths vs. AMPscan
1. **Direct Mammalian Safety Profiling**: Addresses the critical clinical bottleneck of host erythrocyte lysis.
2. **ESM-2 Transformer Representation**: Captures deep evolutionary constraints via fine-tuned ESM2-t6.
3. **Quantitative Concentration ($	ext{HC}_{50}$)**: Predicts concentration at which 50% of RBCs are lysed.

---

## 4. Weaknesses & Pitfalls
1. **Unprincipled Additive Heuristic**: Adding $\pm 0.5$ for motif matches distorts probability calculus and causes artificial score clamping at 0.0 and 1.0.
2. **Small Benchmark Dataset**: CV dataset contains only 1,541 peptides; test set contains 387 peptides.
3. **Assay Inconsistency**: Merges $	ext{HC}_{50}$ values across widely varying assay protocols without standardization.

---

## 5. Genuine Integration Potential for AMPscan
- **Tier 3 Pre-Clinical Safety Head**: Use the fine-tuned ESM-2 representations and Random Forest weights to predict (	ext{Toxicity})$ and calculate the **Therapeutic Selectivity Index ($)**:
  342841TSI = rac{P(	ext{AMP})}{P(	ext{Hemolytic}) + 10^{-4}}342841
