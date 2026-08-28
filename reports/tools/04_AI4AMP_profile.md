# Tool Profile: AI4AMP (LinTzuTang/AI4AMP_predictor)

**Published**: *mSystems* 6(6):e00299-21 (2021)  
**Authors**: Tzu-Tang Lin, Ling-Yen Yang, I-Hsuan Lu, Tsung-Ching Huang, Chih-Wei Lin (National Yang Ming Chiao Tung University)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: 1D-CNN + LSTM Neural Network operating on a **PC6 Physicochemical Matrix**.
- **Pipeline**:
  -  accepting hBcscore normalized physicochemical property trajectories.
  -  extracting local 16-residue physicochemical spatial motifs.
  -  aggregating long-range sequence context $	o$ .
- **PC6 Physicochemical Scales**:
  1. $: Eisenberg consensus hydrophobicity.
  2. $: Fauchere Van der Waals volume.
  3. $: Grantham polarity.
  4. $: Zimmerman isoelectric point.
  5. $	ext{p}K_a$: $lpha	ext{-COOH}$ dissociation constant.
  6. $	ext{NCI}$: Klein net charge index.

---

## 2. Benchmark Performance on Locked 30% Homology Test Set (Cohort 1, N=3,230)
- **ROC-AUC**: **0.7905** (Substantial drop from published CD-HIT 40% scores ~0.90)
- **PR-AUC**: **0.8288**
- **Accuracy**: **0.7449** (MCC: **0.4978**)
- **Calibration Error ($	ext{ECE}_{15}$)**: **0.1535**
- **Throughput**: **572.5 seq/s** on CPU.
- **Skipped Sequences**: **0** (Native handling of  mapped to 0$).

---

## 3. Strengths vs. AMPscan
1. **Compact 6-Channel Physical Input**: Encodes continuous biophysical trajectories rather than sparse one-hot orthogonal vectors.
2. **Robust Handling of Unknowns**: Seamlessly handles ambiguous residues ().
3. **Solid Throughput**: 570+ seq/s on standard CPU.

---

## 4. Weaknesses & Pitfalls
1. **Poor Homology Generalization**: Fails to generalize on strictly novel sequence scaffolds at $<30\%$ identity (ROC-AUC drops to 0.791).
2. **Oversized Convolution Kernel (=16$)**: 16-residue kernel over-smooths short peptides ( < 15$) and cannot isolate compact 3–5 residue cationic motifs.
3. **No Explainability or Calibration**: Outputs uncalibrated sigmoid scores with no residue attribution.

---

## 5. Genuine Integration Potential for AMPscan
- **Multi-Channel PC6 Grid for AMPscan 1D-CNN**: Concatenate PC6 channels with AMPscan's $ one-hot tensor to create a $ feature matrix. This injects physical properties into AMPscan's 1D-CNN while preserving temperature calibration and Integrated Gradients heatmaps.
