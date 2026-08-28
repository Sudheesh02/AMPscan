# Tool Profile: peptidy (molML/peptidy)

**Published**: *Bioinformatics Advances* (2025)  
**Authors**: Machine Learning for Molecular Discovery Lab (molML)  
**Cloned Path**: 

---

## 1. Architecture & Capabilities
- **Architecture**: Pure Python (>=3.6), zero-dependency featurization and vectorization toolkit.
- **Descriptors Extracted**:
  - 16 physicochemical properties: TPSA, rotatable bonds, aliphatic index, charge at variable pH, charge density, pI (bisection search), H-bond donors/acceptors, xlogP, instability index.
  - Native support for Post-Translational Modifications (PTMs): phosphorylated (, , ), methylated (), acetylated (), D-stereoisomers ().

---

## 2. Strengths vs. AMPscan
1. **Lightweight & Sub-Millisecond**: Pure Python stdlib execution in $<0.5$ ms per sequence.
2. **Rich Physicochemical Coverage**: Adds TPSA, rotatable bonds, and instability indices.
3. **Explicit PTM Modeling**: Vectorizes non-canonical and modified residues natively.

---

## 3. Genuine Integration Potential for AMPscan
- **Instant Feature Engine Drop-in**: Integrate  descriptors directly into AMPscan's feature pipeline to expand the 425-D vector to ~435-D, improving stability and membrane penetration profiling.
