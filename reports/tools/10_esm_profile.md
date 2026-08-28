# Tool Profile: ESM (facebookresearch/esm)

**Published**: *Science* 379(6637):1123-1130 (2023)  
**Authors**: Alexander Rives et al. (Meta Fundamental AI Research / FAIR)  
**Cloned Path**: 

---

## 1. Architecture & Capabilities
- **Models Included**:
  - **ESM-2** ( up to ): Bidirectional masked protein language models.
  - **ESMFold** (): Single-sequence 3D atomic structure prediction.
  - **ESM-1v**: Zero-shot variant effect and fitness estimation.

---

## 2. Benchmark Findings in AMPscan Audit
- **Frozen ESM-2 35M Head**: ROC-AUC = **0.9450** (Inferior to AMPscan RF **0.9515**).
- **Frozen ESM-2 150M Head**: ROC-AUC = **0.9521** ($\Delta = +0.0006$ vs RF **0.9515** — statistical tie).
- **Key Takeaway**: A 200-tree Random Forest on 425 physicochemical features matches a 150-million-parameter transformer for peptide classification at a fraction of compute cost.

---

## 3. Genuine Integration Potential for AMPscan
- **Lightweight PLM Embeddings ( or )**: Use compact ESM-2 models on CPU (<25 ms) as auxiliary feature extractors for multi-target and toxicity classification heads.
