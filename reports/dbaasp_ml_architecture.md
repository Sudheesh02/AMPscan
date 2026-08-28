# Machine Learning Architecture Blueprint: DBAASP Integration

**Target**: Multi-Tier ML Engine for AMPscan Pro  
**Hardware Profile**: NVIDIA RTX 5060 Laptop GPU (8GB VRAM), 16GB RAM  
**Date**: August 24, 2026

---

## 1. Multi-Tiered System Architecture

```
                                  ====================================================
                                            AMPSCAN MULTI-TIER ML ARCHITECTURE
                                  ====================================================
                                                            │
                                                  [ Input Peptide FASTA ]
                                                  (Length L: 5 - 100 AA)
                                                            │
                                  ┌─────────────────────────┴─────────────────────────┐
                                  ▼                                                   ▼
                     [ 425-d Tabular Features ]                             [ Frozen ESM-2 150M ]
                   (AAC 20 + DPC 400 + 5 PhysChem)                         (640-d Mean-Pooled)
                                  │                                                   │
                                  ├─────────────────────────┬─────────────────────────┤
                                  ▼                         ▼                         ▼
                     ┌────────────────────────┐┌────────────────────────┐┌────────────────────────┐
                     │   TIER 1: BINARY AMP   ││  TIER 2: MULTI-LABEL   ││    TIER 3: TOXICITY    │
                     │  (Locked Calibrated)   ││   ACTIVITY SPECTRUM    ││  (Hemolysis / Safety)  │
                     └────────────────────────┘└────────────────────────┘└────────────────────────┘
                                  │                         │                         │
                     ┌────────────────────────┐┌────────────────────────┐┌────────────────────────┐
                     │ • Platt RF (Primary)   ││ • Anti-Gram+ (ASL)     ││ • P(Mammalian Cell Tox)│
                     │ • Temp CNN (Secondary) ││ • Anti-Gram- (ASL)     ││ • Calibrated ECE <0.03 │
                     │ • ESM-2 150M (Tie)     ││ • Antifungal (ASL)     ││ • Hydrophobic Moment µH│
                     │                        ││ • Antiviral (ASL)      ││                        │
                     │                        ││ • Anticancer (ASL)     ││                        │
                     └────────────────────────┘└────────────────────────┘└────────────────────────┘
                                  │                         │                         │
                                  └─────────────────────────┼─────────────────────────┘
                                                            ▼
                                           ┌─────────────────────────────────┐
                                           │   THERAPEUTIC SELECTIVITY (SI)  │
                                           │ SI = P(AMP) / (P(Tox) + 1e-4)   │
                                           │ Safety Margin = P(AMP)*(1-P(Tox)│
                                           └─────────────────────────────────┘
```

---

## 2. Mathematical Formulations

### 2.1 Asymmetric Loss (ASL) for Multi-Label Spectrum
To tackle positive-unlabeled imbalance across multi-target heads:
75516\mathcal{L}_{\text{ASL}} = \sum_{k=1}^5 \left( -y_k (1 - p_k)^{\gamma_+} \log(p_k) - (1 - y_k) (p_{k, m})^{\gamma_-} \log(1 - p_{k, m}) \right)75516
- {k, m} = \max(p_k - m, 0)$ with margin  = 0.05$.
- Asymmetric focusing parameters: $\gamma_+ = 0$, $\gamma_- = 4$.

### 2.2 Therapeutic Selectivity Index ($)
75516TSI = \frac{P(\text{AMP})}{P(\text{Mammalian Toxicity}) + 10^{-4}}75516
-  > 5.0$: **High Selectivity Lead** (Potent antimicrobial, non-hemolytic).
- .0 \le TSI \le 5.0$: **Moderate Selectivity** (Therapeutic window requires dosage control).
-  < 1.0$: **Host Toxic / Hemolytic** (Topical-only candidate).
