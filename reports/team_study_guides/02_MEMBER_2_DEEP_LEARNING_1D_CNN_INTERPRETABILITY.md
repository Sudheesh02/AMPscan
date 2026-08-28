# AMPscan Study Guide — Member 2
## Deep Learning & Interpretability Lead

---

### 1. Domain Scope & Responsibilities
- **1D Convolutional Neural Network (1D-CNN) Architecture**: $21 \times 100$ one-hot grid processing standard residues plus 'X'.
- **Post-Hoc Temperature Scaling Calibration**: Continuous logit scaling reducing ECE from $0.0624 \rightarrow 0.0403$ ($T = 1.2833$).
- **Integrated Gradients (Captum) Math & Implementation**: Path-integral residue attribution targeting the AMP logit against a blank zero baseline.
- **Occlusion Sensitivity Sanity Checks**: Pearson correlation verification ($r = 0.89$ on Magainin-2, $0.91$ on Melittin).
- **Training-Set Disclosure & Biological Caveats**: Transparently communicating that canonical peptides are training examples and that attribution $\ne$ biological mechanism.

---

### 2. Deep Technical Foundations & Mathematical Formulations

#### A. 1D-CNN Architecture Specification
- **Input Tensor:** One-hot encoded matrix $X \in \{0, 1\}^{B \times 21 \times 100}$, length-padded with zero vectors up to $L_{\max} = 100$. Channels 0–19 represent standard amino acids; Channel 20 represents non-standard/unknown residue 'X'.
- **Network Topology:**
  1. `Conv1D(in=21, out=64, kernel=5, padding=2)` $\rightarrow$ `ReLU` $\rightarrow$ `Dropout(p=0.20)`
  2. `Conv1D(in=64, out=128, kernel=5, padding=2)` $\rightarrow$ `ReLU` $\rightarrow$ `Dropout(p=0.20)`
  3. `Conv1D(in=128, out=128, kernel=3, padding=1)` $\rightarrow$ `ReLU`
  4. **Global Max Pooling:** $h_{\text{pool}} = \max_{1 \le t \le 100} h_3(t) \in \mathbb{R}^{128}$ (extracts the strongest local motif activation regardless of position).
  5. **Dense Classification Head:**
     `Dropout(p=0.20)` $\rightarrow$ `Linear(128, 64)` $\rightarrow$ `ReLU` $\rightarrow$ `Dropout(p=0.20)` $\rightarrow$ `Linear(64, 1)` $\rightarrow$ scalar logit $z \in \mathbb{R}$.
- **Total Trainable Parameters:** $\mathbf{105,473}$.
- **Training Protocol:** Adam optimizer ($lr = 10^{-3}$, weight decay $= 10^{-4}$), `BCEWithLogitsLoss` with positive class weighting, batch size 64, early stopping on validation ROC-AUC (patience 8, max 40 epochs; stopped at epoch 16 with val ROC-AUC $= 0.9542$).

---

#### B. Temperature Scaling Calibration Mathematics
Deep networks trained with cross-entropy frequently suffer from logit overconfidence.
- **Formulation:**
  $$P(\text{AMP} \mid z) = \sigma\left(\frac{z}{T}\right) = \frac{1}{1 + \exp(-z / T)}$$
- **Optimization:** Optimize the single continuous scalar temperature parameter $T > 0$ by minimizing Negative Log-Likelihood (NLL) over the validation fold logits $\{z_j\}_{j=1}^{N_{\text{val}}}$:
  $$\min_{T > 0} -\frac{1}{N_{\text{val}}} \sum_{j=1}^{N_{\text{val}}} \left[ y_j \ln \sigma\left(\frac{z_j}{T}\right) + (1 - y_j) \ln \left(1 - \sigma\left(\frac{z_j}{T}\right)\right) \right]$$
- **Locked Fitted Parameter:** $T = 1.283258$ (UI displays $T = 1.283$).
- **Impact:** Since $T = 1.283 > 1.0$, it softens extreme logits towards the center, reducing uncalibrated test ECE from $0.0624 \rightarrow \mathbf{0.0403}$.

---

#### C. Integrated Gradients & Occlusion Attribution Mathematics
To explain individual residue contributions to the scalar AMP logit $F(x) = z$:

1. **Integrated Gradients (Sundararajan et al., 2017):**
   Path integral from a reference baseline $x' = \mathbf{0}^{21 \times 100}$ (all-zeros one-hot matrix) to input $x$:
   $$\text{IG}_{c, t}(x) = (x_{c, t} - x'_{c, t}) \times \int_{0}^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_{c, t}} \, d\alpha$$
   - **Numerical Gauss-Legendre / Riemann Approximation (50 steps):**
     $$\text{IG}_{c, t}(x) \approx x_{c, t} \times \frac{1}{m} \sum_{k=1}^m \frac{\partial F\left(\frac{k}{m} x\right)}{\partial x_{c, t}}, \quad m = 50$$
   - **Residue Attribution Score ($S_t$):** Sum across all 21 one-hot channels at position $t \in [1, L]$:
     $$S_t = \sum_{c=1}^{21} \text{IG}_{c, t}(x)$$

2. **Occlusion Sensitivity Check:**
   Systematically zero out the $t$-th residue column ($x_{:, t} \leftarrow \mathbf{0}$):
   $$\Delta \text{logit}_t = F(x) - F(x_{\setminus t})$$

---

### 3. Locked Performance & Attribution Benchmarks

#### 1D-CNN Evaluation (Homology Test Fold, $N=3,230$)
| Split | Model | Accuracy | Macro-F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Homology (Honest)** | **1D-CNN (Phase 4)** | **0.8650** | **0.8648** | **0.9424** | **0.9465** | **1334** | **273** | **163** | **1460** |
| *Random Split (Leaky)* | *1D-CNN Control* | *0.9203* | *0.9203* | *0.9749* | *0.9772* | — | — | — | — |

- **Calibration Shift:** Uncalibrated ECE $0.0624 \rightarrow \mathbf{0.0403}$; Brier Score $0.0991 \rightarrow 0.0957$.

#### Attribution Correlation & Canonical Peptides Audit
| Peptide Name | Sequence ($L$) | In Homology Train? | Training DRAMP ID | Top-3 Attributed Residues (Signed IG) | Pearson $r(\text{IG}, \Delta\text{logit})$ |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **Magainin-2** | `GIGKFLHSAKKFGKAFVGEIMNS` (23) | **YES** | `POS_DRAMP_DRAMP02271` | K10 (+0.771), K11 (+0.770), H7 (+0.637) | $\mathbf{0.887}$ |
| **Melittin** | `GIGAVLKVLTTGLPALISWIKRKRQQ` (27) | **YES** | `POS_DRAMP_DRAMP03002` | W19 (+1.028), K21 (+0.908), I20 (+0.679) | $\mathbf{0.908}$ |
| **LL-37** | `LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES` (38) | **YES** | `POS_DRAMP_DRAMP03571` | K8 (+1.007), K10 (+0.450), D4 (-0.415) | $\mathbf{0.354}$ |

---

### 4. Top 5 Judge Defense Questions & Verbatim Answers

**Q1: How do you interpret the positive and negative peaks in your Integrated Gradients heatmaps?**  
> *"Integrated Gradients computes the exact path integral of the output logit's gradient with respect to the one-hot input tensor relative to a zero baseline. A positive attribution—such as +0.77 on Lysine-10 in Magainin-2—indicates that this residue's presence shifts the CNN logit strongly towards the AMP class. A negative attribution—such as -0.415 on Aspartate-4 in LL-37—shows that an acidic, negatively charged residue pushes the prediction towards non-AMP. This strongly aligns with the known biophysical requirement for cationic amphipathicity."*

**Q2: You show heatmaps for famous AMPs like Magainin-2 and LL-37. Did you validate your model by predicting them as held-out discoveries?**  
> *"No, and doing so would be dishonest. Magainin-2, Melittin, and LL-37 are all present in our DRAMP training fold under IDs DRAMP02271, DRAMP03002, and DRAMP03571. In our UI, we display an explicit warning banner stating that these canonical peptides are training examples. The heatmaps serve to verify that the CNN has learned genuine cationic-hydrophobic motifs rather than memorizing noise; they are not held-out benchmark claims."*

**Q3: Can your Integrated Gradients heatmap be interpreted as an experimental active site or binding mechanism?**  
> *"Absolutely not. Neural network attribution reflects the model's internal feature importance over a 21-channel one-hot embedding. It shows mathematical sensitivity, not biological causality or free energy of binding. A high IG score on a lysine indicates the model relies on positive charge to classify the sequence, but wet-lab mutagenesis is required to confirm biological mechanism."*

**Q4: Why did you use Global Max Pooling instead of Flattening or Global Average Pooling in the CNN?**  
> *"Global Max Pooling makes the network translation-invariant. Antimicrobial motifs—like a cationic Lysine-Lysine pair or amphipathic patch—can occur at the N-terminus, middle, or C-terminus of a peptide. Max pooling extracts the strongest filter activation anywhere in the sequence, allowing the model to detect motifs regardless of peptide length."*

**Q5: Why did LL-37 have a lower correlation ($r = 0.354$) between Integrated Gradients and Occlusion?**  
> *"LL-37 is a longer peptide (38 aa) with multiple redundant cationic residues (K8, K10, K12, K15, R19, R23). Occlusion zeros out one residue at a time; because other basic residues compensate, the single-residue logit drop is dampened. Integrated Gradients integrates across the continuous scaling path, attributing importance to all collaborating residues. This divergence highlights why multiple interpretability methods must be audited together."*

---

### 5. Spoken Presentation Scripts

#### 30-Second Intro Script:
> *"I lead the deep learning and interpretability architecture for AMPscan. We built a 1D Convolutional Neural Network on 21-channel one-hot sequence matrices that achieves 0.9424 ROC-AUC on homology holdouts. We calibrated its logits using Temperature Scaling ($T=1.283$) and implemented 50-step Integrated Gradients to visualize residue-level antimicrobial drivers."*

#### 60-Second Deep-Dive Script:
> *"Our 1D-CNN processes peptides up to 100 residues using 3 convolutional layers and global max pooling, packing 105,473 parameters. It achieves an ROC-AUC of 0.9424 on our homology test fold. Because raw deep networks can be overconfident, we optimized Temperature Scaling on our validation fold ($T=1.283$), cutting Expected Calibration Error from 6.24% down to 4.03%.
> 
> For interpretability, we implemented Captum Integrated Gradients against an all-zeros baseline and verified attributions against residue occlusion. On canonical peptides like Magainin-2 and Melittin, attributions strongly correlate with occlusion at r=0.89 and r=0.91, identifying key Lysine and Tryptophan drivers. In our Next.js UI, researchers can interactively mutate any residue on the heatmap to see how substitutions alter predicted potency in real time."*
