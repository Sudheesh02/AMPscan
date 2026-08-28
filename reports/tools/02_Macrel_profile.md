# Tool Profile: Macrel (BigDataBiology/macrel)

**Published**: *PeerJ* 8:e10555 (2020)  
**Authors**: Célio Dias Santos-Júnior, Shaojun Pan, Xing-Ming Zhao, Luis Pedro Coelho (Fudan University & EMBL)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: Dual 101-tree Random Forest Classifiers compiled into **ONNX runtime graphs** ( and ).
- **Feature Space (22-D Descriptors)**:
  - 9 Grouped Composition Features (Tiny, Small, Aliphatic, Aromatic, Nonpolar, Polar, Charged, Basic, Acidic).
  - 7 Global Physicochemical Descriptors: Net Charge at pH 7.0, Isoelectric Point (pI), Aliphatic Index (Ikai), Instability Index (Guruprasad), Boman Index, Eisenberg Hydrophobicity, $lphahBcHelical Hydrophobic Moment (, window=11).
  - 6 CTDD Descriptors (Distribution of solvent accessibility and secondary structure classes).
- **Scope**: End-to-end metagenomic/genomic pipeline (contigs/reads via Pyrodigal gene prediction), binary AMP prediction, and hemolytic toxicity prediction.

---

## 2. Benchmark Performance on Locked 30% Homology Test Set (Cohort 1, N=3,230)
- **ROC-AUC**: **0.9491** (Statistically near-tied with AMPscan RF **0.9515**)
- **PR-AUC**: **0.9503**
- **Accuracy @ Default 0.5 Threshold**: **0.7854** (MCC: **0.6217**) — suffers high false positive rate at default threshold due to probability skew.
- **Calibration Error ($	ext{ECE}_{15}$)**: **0.2035** (Severe probability miscalibration; 9× worse than AMPscan Platt RF).
- **Throughput**: **6,601.7 seq/s** on CPU (Blazing fast C++ ONNX engine).
- **Skipped Sequences**: 48 sequences containing .

---

## 3. Strengths vs. AMPscan
1. **Ultra-High Throughput**: 6,600+ seq/s enables million-sequence metagenomic screening in minutes.
2. **Built-in Hemolysis Predictor**: Ships with  trained on HemoPI-1 data.
3. **Full Metagenomic SmORF Pipeline**: Ingests raw FASTA/FASTQ reads directly.

---

## 4. Weaknesses & Pitfalls
1. **Severe Calibration Failure ($	ext{ECE} = 0.204$)**: Output numbers cannot be interpreted as true posterior probabilities without recalibration.
2. **No Residue-Level Explainability**: 22 global scalar features cannot produce per-residue heatmaps.
3. **Coarse Dipeptide Representation**: Lacks explicit 0 	imes 20$ dipeptide transition frequencies.

---

## 5. Genuine Integration Potential for AMPscan
- **Drop-in Hemolysis Module ()**: Import Macrel's compressed ONNX hemolysis engine directly into AMPscan for zero-cost safety screening and Therapeutic Selectivity Index ($) computation.
- **Feature Augmentation**: Port Macrel's radial hydrophobic moment (), aliphatic index, and CTDD descriptors into AMPscan's feature extractor.
- **Two-Stage Metagenomic Pre-Filter**: Use Macrel to scan millions of contigs at 6,600 seq/s, routing top hits to AMPscan for calibrated (	ext{AMP})$ and Integrated Gradients residue heatmaps.
