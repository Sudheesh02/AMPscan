# Tool Profile: AmpGram (michbur/AmpGram)

**Published**: *Int. J. Mol. Sci.* 21(12):4378 (2020)  
**Authors**: Michał Burdukiewicz, Katarzyna Sidorczuk, Dominik Rafacz, et al. (University of Wrocław)  
**Cloned Path**: 

---

## 1. Model Architecture & Theory
- **Architecture**: 2-Stage Stacked Random Forest (R  + ).
  - **Stage 1 (10-mer RF)**: Splits sequence into overlapping 10-mers via sliding windows (=10, 	ext{step}=1$). Encodes each 10-mer with informative hBcgrams (1-mers, 2-mers, gapped n-grams) selected via permutation tests (QuiPT) and predicts per-window probabilities.
  - **Stage 2 (Whole-Protein RF)**: Aggregates 14 statistical features across window probabilities to classify the full peptide.

---

## 2. Strengths vs. AMPscan
1. **Full-Length Proteome Scanning**: Accepts 00+$ aa polyproteins and scans unbroken proteomes to pinpoint local 10-mer antimicrobial motifs.
2. **Bioactivity Landscape Mapping**: Outputs continuous activity traces along the primary sequence.

---

## 3. Weaknesses & Pitfalls
1. **R Ecosystem Barrier**: Pure R package () requires R runtime bridging.
2. **Uncalibrated Output**: Lacks formal probability calibration (Platt/Isotonic).
3. **Length Floor**: Fails on peptides $<10$ amino acids.

---

## 4. Genuine Integration Potential for AMPscan
- **Proteome Sliding-Window Mode**: Port AmpGram's 10-mer window aggregation logic into Python, allowing AMPscan to accept full proteins and plot a continuous (	ext{AMP})$ bioactivity landscape.
