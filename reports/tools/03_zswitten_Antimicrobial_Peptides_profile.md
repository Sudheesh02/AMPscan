# Tool Profile: Antimicrobial-Peptides (zswitten)

**Published**: *bioRxiv* preprint 10.1101/692681 (2019)  
**Authors**: Jacob Witten, Zachary Witten (MIT)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: 1D-CNN Regression and Classification Models trained on the **GRAMPA database**.
- **Model Topology**:
  - Two Conv1D layers (64 filters, =5$) with MaxPooling + Dropout(0.5) + Dense(100) + Dense(20) + Dense(1, linear).
  - Multi-species variant incorporates a 10-dimensional learned Bacterium Embedding layer merged via concatenation.
- **Objective**: Quantitative regression of $	ext{log}_{10}(	ext{MIC})$ in $\mu	ext{M}$ against specific bacterial species (*E. coli*, *P. aeruginosa*, *S. aureus*, *K. pneumoniae*).

---

## 2. Inputs, Outputs & Pretrained Models
- **Input**: One-hot encoded matrix $ or $. Strict length ceiling $\le 46	ext{--}50$ aa.
- **Output**: Continuous $	ext{log}_{10}(	ext{MIC})$ in $\mu	ext{M}$ (where bash = 1\,\mu	ext{M}$,  = 100\,\mu	ext{M}$,  = 10{,}000\,\mu	ext{M}$).
- **Pretrained Weights**: 60  +  model files under  across 5-fold cross-validation and negative sampling ratios (	imes, 3	imes, 10	imes$).

---

## 3. Strengths vs. AMPscan
1. **Quantitative Potency (MIC)**: Estimates physical concentration thresholds ($\mu	ext{M}$) rather than pure qualitative binary classification.
2. **Species Specificity**: Predicts pathogen-specific activity profiles (e.g. *E. coli* vs *P. aeruginosa*).
3. **Standardized GRAMPA Dataset**: Compiled 10,000+ experimental MIC values across literature.

---

## 4. Weaknesses & Pitfalls
1. **Synthetic Negative Artifacts**: Inactive peptides are assigned an arbitrary ceiling $	ext{log}_{10}(	ext{MIC}) = 4.0$, creating an artificial bimodal distribution.
2. **Strict Length Ceiling ($\le 50$ aa)**: Fails on peptides of length 51–100 aa.
3. **Drops Disulfide-Rich AMPs**: Data cleaning strips Cysteine (), dropping entire natural classes like defensins and protegrins.

---

## 5. Genuine Integration Potential for AMPscan
- **Secondary Potency Head**: For candidates verified by AMPscan as high-confidence AMPs ( \ge 0.85$), route sequences of length $\le 50$ to zswitten's *E. coli* and *P. aeruginosa* models to estimate approximate MIC potency ranges.
- **Pathogen Clustering Prior**: Use GRAMPA's species correlation matrix to inform multi-target classification heads.
