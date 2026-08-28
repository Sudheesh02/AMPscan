# Tool Profile: sAMPpred-GAT (HongWuL/sAMPpred-GAT)

**Published**: *Bioinformatics* 39(8):btad483 (2023)  
**Authors**: Hongwu Li, Xinjiao Wang, Lu Zhang, Bin Liu (Harbin Institute of Technology)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: 3-layer Graph Attention Network ( + ) on spatial residue contact graphs.
- **Node Features (80-D)**: One-Hot (20-d) + Sinusoidal Positional Encoding (20-d) + Evolutionary PSSM from PSI-BLAST (20-d) + Profile HMM from HHblits (20-d).
- **Edge Features**: Predicted 3D inter-residue distance maps from **trRosetta** thresholded at 20 Å with $ dihedral orientation vectors.

---

## 2. Computational Bottlenecks & Practical Assessment
- **Massive Database Dependency**: Requires $>300$ GB external databases (NCBI NR, UniClust30, nrdb90).
- **Software Dependency Hell**: Pinned to legacy Python 3.7, TensorFlow 1.14.0 (trRosetta), and PyG 1.7.2.
- **Prohibitive Latency**: 	ext{--}15$ minutes per sequence (PSI-BLAST + HHblits + trRosetta).

---

## 3. Strengths vs. AMPscan
- Captures explicit 3D tertiary contacts and evolutionary phylogenetic pressure.

---

## 4. Weaknesses vs. AMPscan
- 10,000× slower than AMPscan; requires 300 GB disk space; fails on synthetic de novo peptides lacking natural BLAST homologs.

---

## 5. Conclusion for AMPscan
- **Retain as reference concept only**: Real-time web/API deployment is impossible; AMPscan's millisecond CPU inference matches or exceeds its accuracy without 300 GB overhead.
