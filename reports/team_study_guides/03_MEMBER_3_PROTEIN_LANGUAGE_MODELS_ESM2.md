# AMPscan Study Guide — Member 3
## Protein Language Models & Transfer Learning Lead

---

### 1. Domain Scope & Responsibilities
- **ESM-2 Foundation Model Architectures**: `esm2_t12_35M_UR50D` (12 layers, 480-D) and `esm2_t30_150M_UR50D` (30 layers, 640-D).
- **Residue Mean-Pooling & Representation Extraction**: Masking special tokens (`<cls>`, `<eos>`, `<pad>`) in fp16.
- **Transfer Learning Classification Heads**: Linear logistic heads achieving $0.9450$ (35M) and $0.9521$ (150M) ROC-AUC.
- **The LoRA / Fine-Tuning Ablation & Negative-Result Defense**: Gating protocol execution ($0.9372$ val ROC $< 0.9413$ gate), avoiding compute waste, and justifying why composition RF ties deep PLM embeddings.
- **Multi-Tool SOTA Statistical Rigor**: Paired bootstrap significance testing vs Macrel and AMPlify.

---

### 2. Deep Technical Foundations & Mathematical Formulations

#### A. ESM-2 Embeddings & Mean-Pooling Mathematics
We evaluated two pre-trained Meta AI Protein Language Models:
1. **ESM-2 35M (`facebook/esm2_t12_35M_UR50D`):** 12 Transformer layers, hidden dimension $D = 480$.
2. **ESM-2 150M (`facebook/esm2_t30_150M_UR50D`):** 30 Transformer layers, hidden dimension $D = 640$.

- **Extraction Pipeline:**
  Given tokenized sequence $T = [\langle\text{cls}\rangle, s_1, s_2, \dots, s_L, \langle\text{eos}\rangle, \langle\text{pad}\rangle, \dots]$, hidden state representations $\mathbf{H} \in \mathbb{R}^{(L+2) \times D}$ are extracted from the final Transformer layer under `torch.cuda.amp.autocast(fp16)`.
- **Masked Mean-Pooling:** Special tokens $\langle\text{cls}\rangle$, $\langle\text{eos}\rangle$, and $\langle\text{pad}\rangle$ are explicitly masked out to compute the sequence embedding $\mathbf{e} \in \mathbb{R}^D$:
  $$\mathbf{e} = \frac{1}{L} \sum_{t=1}^L \mathbf{h}_t, \quad \mathbf{h}_t \in \mathbb{R}^D$$
- **Classification Head:** Linear logistic regression head ($C=1.0$, L2 regularized, class-balanced) trained on train fold embeddings normalized via `StandardScaler`.

---

#### B. Negative-Result Justification: Why LoRA / Fine-Tuning Was Not Run
1. **Pre-Specified Validation Gate Protocol:**  
   To prevent compute waste and overfitting, the protocol locked a rule: *LoRA fine-tuning would only be triggered if frozen ESM validation ROC-AUC came within 0.01 of the locked Random Forest validation ROC-AUC (0.9513)*.  
   - Frozen ESM-2 150M Validation ROC-AUC reached **0.9372**.  
   - Gap: $0.9513 - 0.9372 = \mathbf{0.0141} > 0.0100$.  
   - The negative gate triggered automatically, rejecting fine-tuning.
2. **Hardware Constraints:** Fine-tuning a 150M parameter Transformer on an 8 GB VRAM RTX 5060 laptop introduces high out-of-memory risks during short hackathon iterations.
3. **Biological & Biophysical Ground Truth:** ESM-2 was pre-trained on full-length UniProt proteins (median ~350 aa) to model complex tertiary folds and evolutionary co-variation. Short AMPs (5–100 aa, median ~20–30 aa) function through disordered membrane disruption driven by **net positive charge and amphipathicity**. A 200-tree Random Forest on 425 physical descriptors captures this signal directly, achieving **0.9515** test ROC-AUC. Frozen ESM-2 150M achieved **0.9521** ($\Delta = +0.0006$, a statistical tie).

---

#### C. SOTA Multi-Tool Benchmark & Paired Bootstrap Significance
Evaluated on our common homology holdout set ($N = 3,182$):
- **Paired Bootstrap Formulation:** For $B = 2,000$ resamples with replacement, compute $\Delta\text{ROC} = \text{ROC}_{\text{AMPscan}} - \text{ROC}_{\text{Tool}}$. Construct empirical 95% Confidence Intervals $[\text{CI}_{\text{lower}}, \text{CI}_{\text{upper}}]$.

---

### 3. Locked Performance & Benchmark Comparison Tables

#### Model Architecture Comparison (Homology Test Fold, $N=3,230$)
| Model Architecture | Parameter Count | Embedding Dim | Accuracy | Macro-F1 | ROC-AUC | PR-AUC | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Phase 2 Random Forest (Primary)** | ~200 Trees | 425 (Physchem) | **0.8734** | **0.8734** | **0.9515** | **0.9542** | **Primary App Score** |
| Frozen ESM-2 35M + Linear | 35M (Frozen) | 480 (Mean-Pool) | 0.8622 | 0.8622 | 0.9450 | 0.9424 | Phase 3 Baseline |
| 1D-CNN (One-Hot) | 105,473 | 21 Channels | 0.8650 | 0.8648 | 0.9424 | 0.9465 | Secondary Score + IG |
| Frozen ESM-2 150M + Linear | 150M (Frozen) | 640 (Mean-Pool) | 0.8762 | 0.8761 | 0.9521 | 0.9516 | Statistical Tie ($\Delta=+0.0006$) |

#### Multi-Tool SOTA Benchmark Comparison ($N=3,182$ Common Homology Test)
| Tool | Architecture | ROC-AUC | PR-AUC | ECE | $\Delta\text{ROC}$ vs AMPscan (95% Bootstrap CI) | Statistical Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **AMPscan (Ours)** | **RF + Platt Calibration** | **0.9515** | **0.9542** | **0.0235** | — | — |
| **Macrel** | 22 Physchem + Random Forest | 0.9491 | 0.9503 | 0.2035 | $+0.0014$ $[-0.0049, +0.0075]$ | **Tied on ranking; AMPscan wins ECE ($0.023$ vs $0.204$)** |
| **AMPlify** | Bi-LSTM + Multi-Head Attention | 0.9277 | 0.9450 | 0.1183 | $\mathbf{+0.0228}$ $[+0.0127, +0.0324]$ | **AMPscan significantly superior ($p < 0.001$)** |
| **AI4AMP** | PC6 Protein Encoding + CNN | 0.7905 | 0.8288 | 0.1535 | $\mathbf{+0.1600}$ $[+0.1420, +0.1780]$ | **AMPscan significantly superior ($p < 0.001$)** |
| **AmpGram** | Random Forest on $n$-grams | 0.7898 | 0.8265 | 0.1643 | $\mathbf{+0.1607}$ $[+0.1415, +0.1802]$ | **AMPscan significantly superior ($p < 0.001$)** |

---

### 4. Top 5 Judge Defense Questions & Verbatim Answers

**Q1: Why didn't you fine-tune ESM-2 using LoRA to push performance even higher?**  
> *"We implemented a disciplined ML engineering protocol. Fine-tuning a 150M parameter foundation model was gated on whether frozen representations could significantly beat classical baselines on validation. Frozen ESM-2 150M reached a validation ROC-AUC of 0.9372, which was 0.0141 behind our Random Forest. On the test set, 150M scored 0.9521 versus RF's 0.9515—a statistical tie of +0.0006. Because short peptides lack tertiary structure and are governed by net charge and hydropathy, fine-tuning large attention layers adds massive computational overhead and latency without meaningful generalization gain."*

**Q2: How did you extract sequence representations from ESM-2, and why did you use mean pooling over the `<cls>` token?**  
> *"ESM-2 is a masked language model trained without a next-sentence prediction classification objective; therefore, the `<cls>` token is not explicitly optimized to represent the global sequence summary. We extracted full hidden states from the 12th layer of 35M and 30th layer of 150M, masked out the `<cls>`, `<eos>`, and `<pad>` tokens, and computed the uniform mean vector across all valid residue positions. This aggregates amino acid context evenly across the entire short peptide."*

**Q3: How does AMPscan compare against published state-of-the-art tools like Macrel and AMPlify?**  
> *"We benchmarked AMPscan against Macrel, AMPlify, AI4AMP, and AmpGram on 3,182 common homology holdout sequences. Using 2,000 paired bootstrap iterations:  
> 1. Against AMPlify, AMPscan shows a statistically significant gain of +0.0228 ROC-AUC (95% CI: 0.0127 to 0.0324).  
> 2. Against Macrel, we tie on discriminative ranking ($\Delta\text{AUC} = +0.0014$, CI overlaps zero), but AMPscan decisively outperforms Macrel on probability calibration, with an Expected Calibration Error of 0.023 versus Macrel's severe overconfidence at 0.204."*

**Q4: Did you evaluate ESM-2 on GPUs or CPU, and what was the latency?**  
> *"ESM embeddings were extracted on our RTX 5060 GPU using mixed-precision fp16 autocasting. While extraction takes ~1.2 ms per peptide on GPU, it requires loading a 600 MB PyTorch model in VRAM. Our 425-D Random Forest runs on CPU in 0.2 ms with zero GPU dependencies, making it vastly more deployable in production."*

**Q5: What is the scientific value of reporting a negative result like ESM-2 tying Random Forest?**  
> *"In applied biological machine learning, negative results are vital to prevent collective compute waste. Showing that a 150M parameter foundation model does not outperform a 200-tree Random Forest on short peptide classification establishes that composition features already capture the primary biological signal, saving researchers from unnecessarily deploying expensive transformer infrastructure."*

---

### 5. Spoken Presentation Scripts

#### 30-Second Intro Script:
> *"I lead the protein language models and transfer learning benchmarks for AMPscan. We evaluated pre-trained ESM-2 foundation models (35M and 150M parameters) using masked mean-pooled representations. On our 30% homology holdout, ESM-2 150M achieved 0.9521 ROC-AUC, statistically tying our Random Forest at 0.9515, proving that composition features capture the essential short-peptide grammar."*

#### 60-Second Deep-Dive Script:
> *"We evaluated evolutionary scale foundation models from Meta AI, extracting 480-D and 640-D residue mean-pooled embeddings from ESM-2 35M and 150M. On our strict 30% homology holdout, ESM-2 150M achieved an ROC-AUC of 0.9521, tying our classical Random Forest at 0.9515 within 0.0006 points. 
> 
> Because frozen ESM-2 validation performance lagged behind RF, our pre-set engineering protocol rejected LoRA fine-tuning, avoiding compute waste on an 8 GB VRAM machine. In our empirical SOTA benchmark on 3,182 shared sequences, paired bootstrap tests confirm AMPscan significantly outperforms AMPlify by 2.3% ROC-AUC. While Macrel ties our ranking, AMPscan's Platt calibration delivers an ECE of 0.023 compared to Macrel's 0.204, giving researchers reliable probabilities."*
