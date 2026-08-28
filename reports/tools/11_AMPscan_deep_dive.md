# Scientific Self-Audit: AMPscan Deep Dive

**Project**: AMPscan v1.0 ()  
**Auditor**: Lead Scientific Auditor  

---

## 1. Core Architecture
- **Primary Model**: 200-Tree Random Forest trained on 425-D AAC (20), DPC (400), and Physicochemical (5: Length, Charge @ pH 7, GRAVY, Eisenberg Hydrophobic Moment, Aromatic Fraction).
- **Calibration Engine**: Platt Scaling fit on homology validation fold (=10.0847, b=-5.0839$), slashing ECE from **0.0776 to 0.0235**.
- **Secondary Model**: 1D-CNN (1 	imes 100$ One-Hot Grid) with Temperature Scaling (=1.2833$, ECE drops to **0.0403**).
- **Explainability**: Captum Integrated Gradients (32–50 Riemann steps) with mandatory training-set disclosures.

---

## 2. Audited Performance Baselines (Locked 30% Homology Test Set, N=3,230)
- **Homology ROC-AUC**: **0.9515** (Honest metric)
- **Random Split ROC-AUC**: **0.9791** (Leaky control metric — +0.0276 leakage gap)
- **Homology PR-AUC**: **0.9542**
- **Balanced Accuracy**: **0.8734** (Macro-F1: **0.8734**, MCC: **0.7529**)
- **Inference Speed**: $<5$ ms per sequence on standard CPU (zero GPU required).

---

## 3. Honest Weaknesses & Blind Spots
1. **Fixed Window**: Strictly rejects sequences $<5$ or $>100$ aa.
2. **Binary Only (v1.0)**: Does not predict MIC concentration or target pathogen spectrum.
3. **No 3D Atomic Coordinates**: Primary sequence modeling only.
4. **DRAMP Synthetic Bias**: Rewards high cationicity and amphipathicity; unvalidated on non-cationic/anionic AMP clades.
5. **Base-Rate Prevalence Shift**: Tested on 1:1 balanced set; screening real metagenomes ($<0.1\%$ prevalence) requires threshold tuning ( \ge 0.95$).

---

## 4. Scientifically Sound Upgrades vs. Dishonest Theater
- **Sound**: DBAASP External OOD Benchmark (<30% ID), Supervised Multi-Label Specificity Heads with Asymmetric Loss, Platt-calibrated Mammalian Toxicity/Hemolysis Filter ($).
- **Dishonest Theater (Prohibited)**: Fake radar charts generated from regex/heuristics without real trained models, claiming sequence probability equals nanomolar MIC, or claiming Integrated Gradients heatmaps prove wet-lab binding mechanisms.
