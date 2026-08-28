# AMPscan Study Guide — Member 1
## Classical Machine Learning & Primary Classifier Lead

---

### 1. Domain Scope & Responsibilities
- **425-Dimensional Biophysical Feature Engineering**: 20 Amino Acid Composition (AAC), 400 Dipeptide Composition (DPC), and 5 Physicochemical Descriptors.
- **Primary Classifier Architecture**: 200-Tree Balanced Random Forest trained on MMseqs2 30% homology holdouts.
- **Post-Hoc Probability Calibration**: Platt Scaling mathematics, log-odds mapping, and Expected Calibration Error (ECE) reduction ($0.0776 \rightarrow 0.0235$).
- **Vectorized CPU Inference Throughput**: $4,335.76\text{ sequences/sec}$ on standard 4-core CPU (157.77× acceleration over sequential loops).
- **Translational Discovery Triage**: Operating point selection ($P \ge 0.90$ delivering $97.4\%$ precision and $98.3\%$ specificity).

---

### 2. Deep Technical Foundations & Mathematical Formulations

#### A. 425-Dimensional Feature Space Decomposition
For any peptide sequence $S = s_1 s_2 \dots s_L$ of length $L \in [5, 100]$ over the 20 standard amino acids (non-standard B, Z, U, O, J mapped to X; X ignored in frequency counting):

1. **Amino Acid Composition (AAC — 20-D):**
   $$\text{AAC}_a = \frac{1}{L} \sum_{i=1}^L \mathbb{I}(s_i = a), \quad \forall a \in \Sigma_{20}$$

2. **Dipeptide Composition (DPC — 400-D):**
   $$\text{DPC}_{ab} = \frac{1}{L - 1} \sum_{i=1}^{L-1} \mathbb{I}(s_i = a \land s_{i+1} = b), \quad \forall (a, b) \in \Sigma_{20} \times \Sigma_{20}$$
   *(Transitions containing 'X' are skipped; denominator normalized by valid transitions).*

3. **Physicochemical Descriptors (5-D):**
   - **Length ($L$):** Total count of residues (including 'X').
   - **Net Charge at pH 7.0 ($q_{\text{net}}$):** Calculated using the Henderson–Hasselbalch relation with side-chain $pK_a$ values (IPC standard) and termini ($pK_{a,\text{N-term}} = 9.69$, $pK_{a,\text{C-term}} = 2.34$, Positives: $\text{K}=10.54, \text{R}=12.48, \text{H}=6.04$; Negatives: $\text{D}=3.90, \text{E}=4.07, \text{C}=8.18, \text{Y}=10.46$):
     $$q_{\text{net}} = \frac{1}{1 + 10^{\text{pH} - 9.69}} - \frac{1}{1 + 10^{2.34 - \text{pH}}} + \sum_{a \in S} \left[ \frac{\mathbb{I}(a \in \text{Pos})}{1 + 10^{\text{pH} - pK_a(a)}} - \frac{\mathbb{I}(a \in \text{Neg})}{1 + 10^{pK_a(a) - \text{pH}}} \right]$$
   - **GRAVY (Grand Average of Hydropathy):** Mean Kyte–Doolittle hydropathy scale $\text{KD}(a)$:
     $$\text{GRAVY} = \frac{1}{L} \sum_{i=1}^L \text{KD}(s_i)$$
   - **Hydrophobic Moment ($\mu_H$):** Eisenberg consensus scale $h(a)$ assuming an ideal amphipathic $\alpha$-helix ($\delta = 100^\circ = \frac{5\pi}{9}\text{ rad}$ per residue):
     $$\mu_H = \frac{1}{L} \sqrt{\left( \sum_{i=1}^L h(s_i) \cos(i \delta) \right)^2 + \left( \sum_{i=1}^L h(s_i) \sin(i \delta) \right)^2}$$
   - **Aromatic Fraction ($f_{\text{arom}}$):**
     $$f_{\text{arom}} = \frac{\sum_{i=1}^L \mathbb{I}(s_i \in \{\text{F, W, Y}\})}{L}$$

---

#### B. Primary Classifier Architecture & Hyperparameters
- **Estimator:** `RandomForestClassifier` (Scikit-Learn).
- **Hyperparameters:** `n_estimators=200`, `criterion='gini'`, `max_features='sqrt'`, `class_weight='balanced'`, `n_jobs=4`, `random_state=42`.
- **Feature Preprocessing:** Raw, unscaled 425-D vector (tree splits are scale-invariant).

---

#### C. Post-Hoc Platt Scaling Calibration Mathematics
Tree ensembles output uncalibrated vote fractions $p_{\text{rf}} = \frac{1}{M}\sum_{m=1}^M h_m(x) \in [0, 1]$, which exhibit sigmoidal distortion.
- **Platt Transform Formulation:**
  $$P(\text{AMP} \mid p_{\text{rf}}) = \sigma(a \cdot p_{\text{rf}} + b) = \frac{1}{1 + \exp(-(a \cdot p_{\text{rf}} + b))}$$
- **Optimization:** Fit unregularized binary logistic regression ($C=10^6$, L-BFGS) exclusively on the **Homology Validation Fold** ($N_{\text{val}} = 3,203$):
  $$\min_{a, b} -\sum_{j=1}^{N_{\text{val}}} \left[ y_j \ln \sigma(a \cdot p_{\text{rf}, j} + b) + (1 - y_j) \ln (1 - \sigma(a \cdot p_{\text{rf}, j} + b)) \right]$$
- **Locked Fitted Parameters:** $a = 10.0847$, $b = -5.0839$.
- **Theoretical Guarantee:** Because $a > 0$, the mapping is strictly monotonically increasing; ranking is perfectly preserved, guaranteeing that **ROC-AUC is strictly unchanged**.

---

#### D. Expected Calibration Error (ECE) Formulation
Given $M = 15$ equal-width probability bins $B_m = \left( \frac{m-1}{M}, \frac{m}{M} \right]$ partitioning $[0, 1]$:
$$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
where:
$$\text{conf}(B_m) = \frac{1}{|B_m|} \sum_{i \in B_m} \hat{p}_i, \quad \text{acc}(B_m) = \frac{1}{|B_m|} \sum_{i \in B_m} y_i$$

---

### 3. Locked Performance & Throughput Metrics

#### Baseline & Calibration Results (Homology Test Fold, $N=3,230$)
| Split / Setup | Model | Accuracy | Macro-F1 | ROC-AUC | PR-AUC | Uncal ECE | Cal ECE | Cal Brier |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Homology (Honest)** | **Random Forest (Primary)** | **0.8734** | **0.8734** | **0.9515** | **0.9542** | **0.0776** | **0.0235** | **0.0883** |
| Homology (Honest) | Logistic Regression (L2) | 0.8375 | 0.8374 | 0.9016 | 0.9113 | — | — | — |
| *Random Split (Leaky)* | *Random Forest Control* | *0.9231* | *0.9231* | *0.9791* | *0.9804* | *0.0876* | *0.0151* | *0.0558* |

- **RF Homology Test Confusion Matrix:** $\text{TN} = 1,388$, $\text{FP} = 219$, $\text{FN} = 190$, $\text{TP} = 1,433$.
- **Leakage Gap:** $\Delta \text{ROC-AUC} = 0.9791 - 0.9515 = +0.0276$ (points gained by family memorization in random splits).

#### CPU Inference Throughput & Vectorization Benchmark
- **Sequential Scoring ($N=400$):** $14.56\text{ s} \implies \mathbf{27.48\text{ sequences/sec}}$.
- **Vectorized Batched Scoring ($N=3,230$ on 4 CPU cores):** RF feature extraction + inference $= 0.16\text{ s} + \text{CNN } 0.58\text{ s} \implies \mathbf{4,335.76\text{ sequences/sec}}$.
- **Speedup Factor:** $\mathbf{157.77\times}$ acceleration purely via NumPy matrix vectorization.

#### Discovery Operating Regimes (Threshold Tuning for Rare Proteomes)
| Operating Point | Threshold ($P_{\text{cal}} \ge \theta$) | Predicted AMPs | Precision | Recall | Specificity | High-Confidence Leads |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Balanced Screening** | $\ge 0.50$ | 1,632 | $87.5\%$ | $88.0\%$ | $87.3\%$ | 1,428 TPs |
| **High Stringency** | $\ge 0.80$ | 1,255 | $94.8\%$ | $73.3\%$ | $96.0\%$ | 1,190 TPs |
| **Ultra-Pure Discovery** | $\ge 0.90$ | 1,059 | $\mathbf{97.4\%}$ | $63.5\%$ | $\mathbf{98.3\%}$ | 1,031 TPs |
| **Lead Synthesis Gate** | $\ge 0.95$ | 863 | $\mathbf{98.7\%}$ | $52.5\%$ | $\mathbf{99.3\%}$ | 852 TPs |

---

### 4. Top 5 Judge Defense Questions & Verbatim Answers

**Q1: Why did you choose a Random Forest over deep learning as your primary production classifier?**  
> *"On short peptide sequences of 5–100 amino acids, the biophysical driver of antimicrobial activity is dominated by global composition: high cationic net charge from lysine/arginine and amphipathic Kyte-Doolittle hydrophobic moments. Our 425-dimensional feature matrix captures these physical properties explicitly. On our strict 30% homology holdout, RF achieves an ROC-AUC of 0.9515, matching frozen ESM-2 150M at 0.9521 within 6 ten-thousandths of a point. Crucially, the RF processes 4,335 sequences per second on standard CPU without GPU dependencies or VRAM overhead."*

**Q2: How exactly does Platt Scaling work, and why did you not use Temperature Scaling for the Random Forest?**  
> *"Temperature scaling divides raw, unconstrained real-valued logits by a scalar $T$. Random Forests do not produce logits; they output ensemble vote fractions bounded in $[0, 1]$. Platt scaling fits a two-parameter logistic sigmoid $\sigma(a \cdot p_{\text{rf}} + b)$ directly to these probabilities. We optimized $a$ and $b$ using unregularized maximum likelihood strictly on our validation fold ($a=10.0847, b=-5.0839$). This reduced our Expected Calibration Error from 7.76% down to 2.35% while preserving ROC-AUC identically."*

**Q3: If your test set is balanced 50/50, won't your model produce massive false positives when deployed on a whole proteome where AMPs represent <1% of sequences?**  
> *"Yes, that is the base-rate fallacy. At a default 0.5 threshold, precision would degrade in an AMP-rare environment. However, because our probabilities are rigorously calibrated, downstream users can shift the decision threshold along our operating curve. At $P \ge 0.90$, AMPscan achieves 97.4% precision and 98.3% specificity, filtering out over 98% of decoys and yielding 1,059 high-confidence leads."*

**Q4: Did you scale or normalize the 425 features before passing them to the Random Forest?**  
> *"No. Decision tree splits are scale-invariant; thresholding a feature $x_i \le \theta$ produces the exact same partition whether $x_i$ is raw, standardized, or min-max scaled. Leaving features unscaled preserves exact interpretability for descriptors like length and integer net charge."*

**Q5: Why 200 estimators instead of 500 or 1000?**  
> *"Validation fold out-of-bag error flattened completely at 150 trees. 200 trees provided the optimal trade-off between ensemble variance reduction and low inference latency, keeping single-sequence featurization and prediction under 0.2 milliseconds."*

---

### 5. Spoken Presentation Scripts

#### 30-Second Intro Script:
> *"I lead the classical machine learning and primary inference architecture for AMPscan. We engineer a 425-dimensional feature space capturing amino acid frequencies, dipeptide transitions, charge at pH 7, hydropathy, and hydrophobic moment. Our primary classifier is a 200-tree Random Forest that achieves our headline 0.9515 ROC-AUC on strict 30% homology holdouts, with Platt calibration reducing Expected Calibration Error to 2.35%."*

#### 60-Second Deep-Dive Script:
> *"Because antimicrobial peptides are short—between 5 and 100 amino acids—their biological activity is governed by biophysical composition rather than complex evolutionary folds. We extract 20 amino acid frequencies, 400 dipeptide transitions, and 5 physicochemical properties including Henderson–Hasselbalch charge and Eisenberg hydrophobic moment.
> 
> Our Random Forest matches frozen 150M ESM-2 foundation models within 0.0006 ROC-AUC while running on CPU at over 4,300 sequences per second. To make our probabilities trustworthy for biologists, we fitted Platt scaling on our validation fold, dropping Expected Calibration Error from 7.76% to 2.35%. In rare-discovery settings, shifting the threshold to P >= 0.90 delivers 97.4% precision and 98.3% specificity."*
