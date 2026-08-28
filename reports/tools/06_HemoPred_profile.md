# Tool Profile: HemoPred (chaninn/HemoPred)

**Published**: *Cheminformatics and Chemical Biology* / *Nano Life* 7(1):1750003 (2017)  
**Authors**: Thanyada San Lwin, Nalini Schaduangrat, Virapong Prachayasittikul, Chanin Nantasenamat (Mahidol University)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: R-based **Random Forest** ({	ext{tree}} = 100$) operating strictly on 20-dimensional standard Amino Acid Composition (AAC).
- **Runtime**: R Shiny web application (, ). Fits the model on-the-fly from  upon initialization.

---

## 2. Strengths vs. AMPscan
1. **Minimalist & Interpretable**: 20 global AAC features allow direct interpretation of residue enrichment (e.g. Lys/Leu/Trp hydrophobic clusters).
2. **Canonical Baseline**: Trained on the benchmark HemoPI-3 dataset, providing a standard reference baseline.

---

## 3. Weaknesses & Pitfalls
1. **Completely Position-Blind**: 20-D AAC discards all amphipathic moments, helical topology, and residue order.
2. **Non-Deterministic Loading**: Refitting  on CSV load without a fixed seed introduces prediction variance across R sessions.
3. **No Probability Output or Calibration**: Emits hard binary  factors with no confidence scores.

---

## 4. Genuine Integration Potential for AMPscan
- Serves as a classical AAC baseline model in the Cohort 5 mammalian safety benchmark.
