# AMPGuard — Full Study Guide

Audience: 5th-semester biotech. Goal: understand the project well enough to **say it out loud** and survive judge questions. Numbers below are **locked** from Phases 1–9. Do not invent new ones.

---

## 0. How to use this document (30-min / 2-hour / full-day paths)

**30 minutes (survival).** Read §1, §2, §5 (homology), the table in §6, §10, and the 90-second script in §15. Practice saying: “homology RF ROC-AUC 0.95 is the honest number; random 0.98 is leaky.”

**2 hours (can demo).** Add §3, §4, §7, §8, §9. Run Streamlit once. Paste magainin-2 and **read the training-set banner out loud**. Skim the 20 Q&A in §12.

**Full day (can defend).** Read the whole guide. Open `reports/LIMITATIONS.md` and `reports/mixed_clusters.md`. Walk the file map in §14. Memorize the 4-minute script. Quiz each other with §12 without looking.

Do **not** retrain anything. Do **not** quote random-split AUC as the main result.

---

## 1. Official SIH title vs our scoped title

| | Text |
| --- | --- |
| **Official SIH title** | AI-Based Protein and Biomolecule Classification Assistant |
| **Our title** | **AMPGuard: Homology-Aware Antimicrobial Peptide Classifier** |
| Official ask | FASTA in; classify sequences into functional/biological categories; confidence; some explainability |
| Our scope | **Peptides, length 5–100**, binary **AMP vs non-AMP**, homology-aware split, calibrated scores, CNN residue plots |

**Why we scoped**

- **Finishability.** Gene Ontology (GO) has thousands of labels. Pfam is domain annotation for whole proteins. Doing those *and* AMP well in a short hackathon produces a wide, leaky demo. We finished **one** task end to end.
- **8GB VRAM (RTX 5060 laptop).** Frozen ESM-2 35M and 150M fit. Fine-tuning a large protein LM, or a full GO hierarchy, does not.
- **Scientific validity.** AMP vs non-AMP on short peptides is a real, published problem (AMPlify, DRAMP). We could control **homology leakage**, which is the silent failure mode of sequence ML. GO/Pfam without a cluster split is easy to fake with a high F1.

One sentence for judges: *“The official problem is sequence classification with honest confidence. AMP vs non-AMP is the instance we could do rigorously on this laptop.”*

---

## 2. Problem in plain English

An **antimicrobial peptide (AMP)** is a short protein chain that can damage microbes (often by hitting membranes). Databases list known AMPs. Computers can learn “this string of amino acids looks like those.”

The trap: two peptides that **share ancestry** look alike. If you put cousins in both train and test, the model **memorizes the family**, not a general AMP pattern. Accuracy looks 98% and is a lie.

**AMPGuard** asks: given a peptide of 5–100 amino acids, what is P(AMP), after we stopped close homologs from sitting in both train and test? And can we show **which residues** the CNN used, without claiming that is biology?

It does **not** ask: will this peptide kill MRSA in a mouse?

---

## 3. What we built (and did not build)

**Built (locked)**

| Phase | What |
| --- | --- |
| 1 | Clean AMP vs non-AMP FASTA, MMseqs2 homology split 70/15/15 + random control |
| 2 | Classical RF (primary) and logistic regression on composition features |
| 3 | Frozen ESM-2 **35M** mean-pool + linear head |
| 4 | Small 1D-CNN on 21-channel one-hot |
| 5 | Calibration: Platt on RF, temperature T on ESM-35M and CNN |
| 6 | Integrated Gradients + occlusion on the CNN; train-set warning for 3 famous AMPs |
| 7 | Offline Streamlit demo |
| 8 | README, limitations, mixed-cluster table, archive of leftover files |
| 9 | Frozen ESM-2 **150M** linear; test once; tie with RF; **no LoRA** |

**Did not build**

- GO / Pfam / EC / DeepLoc
- MIC or hemolysis prediction
- Fine-tuning or LoRA of ESM
- Adding magainin-2 to a “held-out showcase” without saying it is in **train**
- Any wet-lab assay

---

## 4. Data

### Sources and licenses

| Role | Source | License | Cite |
| --- | --- | --- | --- |
| Positives | **DRAMP General** FASTA | CC BY 4.0 | Ma et al. NAR 2025; Shi et al. NAR 2022 |
| Negatives | **AMPlify** published non-AMP FASTAs, Zenodo 10.5281/zenodo.7320306 | CC BY 4.0 | Li et al. BMC Genomics 2022; BMC Res Notes 2023 |

Raw DRAMP General: **11,687** sequences. We did **not** use APD or UniProt Swiss-Prot (those were fallbacks only).

### Why negatives came from AMPlify

“Non-AMP” is not a natural class. AMPlify already published FASTA negatives for this exact ML setting (UniProt-derived, length-aware, documented). That is more honest than silently scraping Swiss-Prot with a homemade keyword filter. We used **balanced** AMPlify non-AMPs first; after cleaning we still had fewer negatives than positives, so we added **6,579** sequences from the published **imbalanced** AMPlify files (not a new UniProt sample).

### Cleaning rules (locked)

1. Length **5–100** inclusive.
2. Uppercase. Map **B,Z,U,O,J → X**. Drop any sequence that still has non-amino-acid characters. **X is allowed.**
3. Exact-sequence dedup; keep first.
4. Same sequence in both AMP and non-AMP → **keep as AMP** (19 conflicts).

Mapped B/Z/U/O/J→X: 418 positives, 0 negatives. Dropped leftover non-AA: 48 positives, 0 negatives.

### Final counts

| stage | AMP | non-AMP |
| --- | ---: | ---: |
| raw (DRAMP / AMPlify balanced) | 11687 | 4173 |
| length 5–100 | 11459 | 4099 |
| after alphabet | 11411 | 4099 |
| after exact dedup | 10678 | 4099 |
| + imbalanced AMPlify | — | +6579 |
| after conflict resolve | **10678** | **10659** |

Combined clean set: **21,337** peptides. Details: `data/LICENSE_NOTES.md`.

DRAMP `Family` column was audited later: **4,841** cleaned AMPs have a family string, **5,837** do not. The column mixes AMP families (Brevinin, defensin) with **virus taxa** (Retroviridae). **No family head was trained.** See `reports/family_label_audit.md`.

---

## 5. Homology split (must-know)

This is the part you **must** be able to say without notes.

### What MMseqs2 does in plain language

**MMseqs2** is a fast tool that groups sequences that are similar. Think “put close relatives in the same household.” We used `easy-cluster`.

### The three settings (memorize)

| Flag | Meaning in English |
| --- | --- |
| `--min-seq-id 0.3` | Two sequences must share about **30%** of amino acids (aligned) to cluster together |
| `-c 0.8` | **80% coverage** |
| `--cov-mode 1` | Coverage is on the **shorter** sequence (the short peptide must be 80% covered). Fair when lengths differ |

### Whole-cluster assignment

A **cluster** is one household. **Every member goes to the same fold** — train or val or test. We never put cousins in train and test. Targets: **70% / 15% / 15%** of sequences, seed **42**. Clusters were stratified as pos-only / neg-only / mixed so class balance does not collapse.

**9,241 clusters:** 4,778 AMP-only, 4,391 non-AMP-only, **72 mixed**.

| fold | n | AMP | non-AMP |
| --- | ---: | ---: | ---: |
| train | 14904 | 7444 | 7460 |
| val | 3203 | 1611 | 1592 |
| test | 3230 | 1623 | 1607 |

### Mixed clusters

**72** clusters contain **both** an AMP and a non-AMP (264 AMP members, 445 non-AMP). They still go to **one** fold, so they do not leak across splits. They **do** mean 30% identity is not a perfect biological wall: a short AMP can sit inside a longer UniProt-like peptide. Mixed-cluster AMPs are shorter on average (**46.6** aa) than mixed-cluster non-AMPs (**62.9** aa). Full table: `reports/mixed_clusters.md`.

### Why random-split scores look better

The **random split** uses the **same 21,337 peptides** but ignores clusters (still 70/15/15, seed 42, by class). Homologs can sit in train and test. Models look smarter because they **recognize the family**.

Say this: *“Random-split RF ROC-AUC is 0.979. Homology-split RF is 0.951. We report 0.95. The extra points on random are leakage, not better biology.”*

---

## 6. Models

All trained on **homology train**, light use of **homology val**, reported on **homology test**. Seed 42. Primary app score = **calibrated RF**, not ESM.

| model | What it sees | Homology test acc | macro-F1 | ROC-AUC | PR-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| **RF (Phase 2, primary)** | AAC 20 + DPC 400 + 5 physchem = 425 numbers | **0.8734** | **0.8734** | **0.9515** | **0.9542** |
| Logistic regression (Phase 2) | same features, L2 | 0.8375 | 0.8374 | 0.9016 | 0.9113 |
| Frozen ESM-2 35M + linear (Phase 3) | 480-d mean-pooled residues | 0.8622 | 0.8622 | 0.9450 | 0.9424 |
| 1D-CNN (Phase 4) | 21-channel one-hot (20 AA + X), 3 conv layers | 0.8650 | 0.8648 | 0.9424 | 0.9465 |
| Frozen ESM-2 150M + linear (Phase 9) | 640-d mean-pool | 0.8762 | 0.8761 | 0.9521 | 0.9516 |

Phase 9 vs RF: **0.9521 vs 0.9515** (Δ **+0.0006**) = **tie**. Phase 9 **val** was **0.9372**, so LoRA was **not** run.

**RF homology test confusion:** TN 1388, FP 219, FN 190, TP 1433 (test n = 3230).

**Random-split test (leakage control only):** RF ROC-AUC **0.9791**; ESM-2 35M **0.9657**; CNN **0.9749**. Do not lead with these.

### Why RF can beat frozen protein language models on short peptides

ESM-2 was trained on **proteins**, often long, evolutionary. Our items are **5–100 aa**, and the AMP signal is largely **composition**: lots of K/R (plus charge), hydrophobic/aromatic faces. Amino-acid frequencies, dipeptides, net charge at pH 7, and GRAVY already encode that. A 200-tree RF on those features is enough. Frozen ESM-2 35M **lost** to RF (0.945 vs 0.952). Frozen 150M **tied**. That is a result, not a failure of “not using AI.”

Spoken line: *“On this task the expensive embedding is a tie with a forest on charge and composition. We still keep ESM as a check. We ship the RF.”*

Hardware: RTX 5060 laptop, **8 GB**. Frozen 35M and 150M inference fit in fp16. Full fine-tune of large ESMs does not.

---

## 7. Calibration

A model can **rank** well (high ROC-AUC) and still be **over-confident** (“I’m 99% sure” when it is wrong 20% of the time).

We fit calibration **only on homology val**, then applied it to test. Ranking barely changes; confidence does.

| What | Method | Homology test uncal ECE | cal ECE | ROC-AUC |
| --- | --- | ---: | ---: | ---: |
| RF | **Platt**: `sigmoid(a × p_rf + b)`, a=10.0847, b=−5.0839 | 0.0776 | **0.0235** | 0.9515 unchanged |
| ESM-2 35M | **Temperature** T=1.2855, `sigmoid(logit / T)` | 0.0376 | **0.0185** | 0.9450 unchanged |
| 1D-CNN | Temperature T=**1.2833** (app uses 1.283) | 0.0624 | **0.0403** | 0.9424 unchanged |

**ECE** (15 equal bins): how far average predicted probability is from actual AMP frequency, weighted by bin size. Lower is better.

**Do not say** “we temperature-scaled the RF.” RF used **Platt**, not T.

App **primary** number = Platt-calibrated RF P(AMP). **Secondary** = CNN P(AMP) after T.

---

## 8. Explainability (IG + occlusion + train-set warning)

Only the **1D-CNN** was attributed (Phase 6). Captum **Integrated Gradients** on the 21-channel one-hot, baseline = all zeros, target = AMP **logit**. Per-residue score = sum of IG over the 21 channels at that position.

**Occlusion** (cheap check on 3 peptides): zero one residue, Δ = logit_full − logit_occluded.

**Train-set warning — say this every time you show these three:**

| peptide | sequence | in homology **train**? | ID |
| --- | --- | --- | --- |
| magainin-2 | GIGKFLHSAKKFGKAFVGEIMNS | **yes** | POS_DRAMP_DRAMP02271 |
| LL-37 | LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES | **yes** | POS_DRAMP_DRAMP03571 |
| melittin | GIGAVLKVLTTGLPALISWIKRKRQQ | **yes** | POS_DRAMP_DRAMP03002 |

None of them are in val/test.

High |IG| often on **K/R** (cationic) or hydrophobic/aromatic residues, which matches the textbook AMP cartoon. Pearson IG vs occlusion: magainin-2 0.89, LL-37 0.35, melittin 0.91. **This is not a mechanism and not a wet-lab active site.**

---

## 9. Streamlit demo — what to click and what to say

Command (from project root, `amp-data` env):

```bash
streamlit run app/streamlit_app.py
```

Usually http://localhost:8501.

**Predict page**

1. Paste `GIGKFLHSAKKFGKAFVGEIMNS`.
2. Click **Predict**.
3. Point to **RF P(AMP) calibrated** as the number you trust. CNN T=1.283 is extra.
4. **Read the yellow banner:** “These three examples are in the TRAINING set.”
5. Show the heatmap. Say IG is the CNN’s attention-like residue score, not biology.
6. Optional: paste a garbage string or a 200-aa protein and show the **length / alphabet error**. That is a feature.

**Metrics page**

1. Homology table: RF 0.9515, 35M 0.9450, CNN 0.9424, 150M 0.9521 (tie).
2. Random table: “this is the leaky number; we do not claim it.”
3. ECE table: RF 0.078 → 0.023.
4. Read the limitations paragraph as written.

No training button. No API. ESM-150M is **not** loaded in the demo (too heavy); it appears only as a locked number.

---

## 10. Limitations (honest, spoken version)

Say these as sentences, not as shame.

1. This is **pattern matching**, not a killing assay.
2. Test set is **half AMP, half not**. Nature is not. Precision would crash on a proteome unless we raise the threshold.
3. Non-AMPs are **unannotated**, not proven inactive.
4. DRAMP General includes **synthetics**. Easier for composition models.
5. **72 mixed clusters**: 30% identity is strict, not perfect.
6. **Random 0.98 is leaky.** Quote **0.95**.
7. **RF matched or beat frozen ESM.** Composition is most of the signal on 5–100 aa.
8. **IG ≠ mechanism.** Magainin-2 is in **train**.
9. **Out of scope:** full proteins, GO, Pfam, MIC, hemolysis, mice.

Full list: `reports/LIMITATIONS.md`.

---

## 11. If another team shows GO / Pfam / “all proteins”

**Laptop/VRAM reality.** GO multi-label on long proteins needs different data, hierarchical metrics, and usually more than 8 GB if you fine-tune. Pfam done properly is **HMMER**, a database search, not “our neural net.” A 3-day GO head with a random split will look 90%+ and leak homology worse than AMP.

**Short answers (memorize)**

- “GO is the right *product roadmap*. It is the wrong *3-day* product.”
- “Pfam hits are sequence search. If they HMMER’d it, that is InterPro, not their model. If they trained a net in two days, ask which identity split.”
- “Paste a 400-aa random protein: we **refuse** (length). They may dump 10 GO terms at 0.99 confidence. Which is more honest?”
- “We report a 30% cluster split. If they cannot name CD-HIT or MMseqs, their F1 is not comparable.”
- “AMP vs non-AMP is still ‘functional classification.’ It is one axis we could finish: split, calibration, explanations.”

Do **not** promise we will add GO tonight.

---

## 12. Judge Q&A (20 questions, 20–40 second answers)

**1. What does your model actually predict?**  
P(this 5–100 aa peptide looks like DRAMP AMPs versus AMPlify non-AMPs), after a 30% homology split. Not MIC, not “will kill in vivo.”

**2. Why not classify all proteins?**  
Time, VRAM, and honesty. Full proteins + GO is another dataset and another leak problem. We finished peptides.

**3. What is homology leakage?**  
Train and test share close relatives. The model memorizes the family. We clustered at 30% identity and kept whole clusters in one fold.

**4. Why 30% and not 70%?**  
30% is stricter. Harder numbers, more honest. 70% still lets close cousins through.

**5. What is cov-mode 1?**  
The **shorter** sequence must be 80% covered. Otherwise a tiny peptide can “match” a long protein on a fragment and look unrelated in coverage.

**6. Why is random-split AUC higher?**  
Because leakage is allowed. RF 0.979 random vs 0.951 homology. We quote homology.

**7. Why RF as primary if you have ESM?**  
On homology test RF 0.9515, frozen 35M 0.945, frozen 150M 0.9521 — a tie. RF is fast, CPU, calibrated. We ship RF.

**8. Did the 150M model beat RF?**  
By +0.0006 ROC-AUC on test. That is a tie. Val was 0.937, so we did **not** LoRA.

**9. Why not fine-tune ESM?**  
8 GB laptop, frozen already ties RF, and the protocol was: no LoRA unless val is within 0.01 of RF. It was not.

**10. How did you get negatives?**  
Published AMPlify non-AMP FASTAs, CC BY 4.0. Balanced first, then extra from their imbalanced set because we had fewer negatives than AMPs after cleaning. Not “random junk DNA.”

**11. Are the labels perfect?**  
No. Non-AMP means not annotated AMP. DRAMP mixes natural and synthetic. 19 sequences sat in both classes; we kept AMP.

**12. What is Platt vs temperature?**  
RF: logistic on its probability (two numbers, a and b). CNN/ESM: divide logit by T. T>1 cools overconfidence. Not the same method. ROC-AUC unchanged.

**13. What is ECE?**  
Expected Calibration Error, 15 bins. How wrong the probabilities are, not just the ranking. RF 0.078 uncalibrated, 0.023 after Platt.

**14. Can I trust 0.99 P(AMP) on a new peptide?**  
On this balanced test, better after calibration. On a proteome, no — prevalence is tiny. We would raise the threshold.

**15. What does the heatmap mean?**  
CNN Integrated Gradients on one-hot residues. Red = pushing AMP logit up. Not a binding site. Magainin-2, LL-37, melittin are **in train**.

**16. Did you validate on famous AMPs?**  
We showed them. We also said they are training examples. That is the opposite of fake held-out validation.

**17. 72 mixed clusters — did you leak?**  
No leak across folds: the whole mixed cluster stays in one fold. It means some AMPs and non-AMPs are still 30%-similar. We documented it.

**18. Why 5–100 amino acids?**  
Peptide AMP range used in this literature; AMPlify went to 200. We locked 5–100. Longer proteins are out of spec; the app rejects them.

**19. Is this better than AMPlify the paper?**  
Different split, different positive source (DRAMP vs their APD mix). We do not claim to beat their published AUC. We claim a **homology-controlled DRAMP/AMPlify set** and a working demo.

**20. What would you do with a wet lab?**  
Freeze the model. Screen sequences **far** from train. Synthesize 20–30. Report hit rate and hemolysis. That is a different paper. Not this demo.

---

## 13. Glossary (spoken definitions)

| Term | Say it like this |
| --- | --- |
| **AMP** | Short peptide that can harm microbes; here, a **database label**, not a lab result |
| **FASTA** | Text file: `>` name, then amino-acid letters |
| **Homology** | Relatedness by sequence similarity; cousins look alike |
| **Cluster** | A bag of similar sequences from MMseqs2 |
| **Homology split** | Whole bags go to train or test, never split |
| **Random split** | Shuffle sequences; cousins can land in both sides |
| **ROC-AUC** | Ranking quality, 0.5 = coin, 1 = perfect order; **not** “percent correct” |
| **PR-AUC** | Ranking when you care about the AMP class; useful if classes were imbalanced (ours are almost balanced) |
| **Accuracy** | Fraction of labels right at threshold 0.5; here ~0.87 on a 50/50 test |
| **Macro-F1** | F1 averaged over AMP and non-AMP; here almost equal to accuracy because the test is balanced |
| **ECE** | How calibrated the probabilities are |
| **Brier** | Mean squared error of P(AMP) vs 0/1 |
| **Platt scaling** | Fit a small logistic on RF probabilities (val only) |
| **Temperature scaling** | Divide logits by T>0 (val only) |
| **Logit** | Raw score before sigmoid |
| **GRAVY** | Average hydrophobicity (Kyte–Doolittle) |
| **Net charge (pH 7)** | Approximate charge including termini, Henderson–Hasselbalch |
| **One-hot** | Each position is a 21-long switch (20 amino acids + X) |
| **Frozen ESM** | Protein language model weights not updated; we only train a linear layer on embeddings |
| **Mean-pool** | Average residue vectors, skip start/end/pad tokens |
| **Integrated Gradients** | Attribution method: how each input channel pulls the AMP logit |
| **Occlusion** | Hide one residue, see how the logit moves |
| **GO / Pfam** | Gene Ontology functions; protein domain families — **not this project** |
| **LoRA** | Cheap fine-tune of a big model — **not run** (val too far from RF) |
| **CC BY 4.0** | Cite the source, reuse allowed |

---

## 14. File map of the repo

```
README.md                     AMPGuard title + how to run
app/streamlit_app.py          demo (Predict + Metrics)
app/README.md                 streamlit command
scripts/                      reproduction scripts (do not retrain for the pitch)
data/raw/                     DRAMP FASTA/xlsx, AMPlify FASTAs
data/processed/               cleaned FASTA, labels, features, embeddings, cnn encodings
data/splits/                  homology + random FASTAs, cluster files
data/LICENSE_NOTES.md
models/baseline/              RF + scaler (locked)
models/esm2_35M/              frozen 35M linear (locked)
models/esm2_150M/             frozen 150M linear (locked)
models/cnn1d/                 CNN weights (locked)
models/calibration/           Platt + T (locked)
reports/STUDY_GUIDE.md        this file
reports/LIMITATIONS.md
reports/mixed_clusters.md
reports/phase_1_report.md … phase_9_report.md
reports/baseline, esm2_35M, cnn1d, calibration, explain/
archive/                      leftover enzyme/BLAST notes, not the AMP task
```

---

## 15. 90-second and 4-minute oral scripts

### 90 seconds

“Official SIH title is an AI protein classifier. We scoped it to **AMPGuard**: antimicrobial peptide versus not, length 5 to 100, because that we could finish honestly on an 8 GB laptop.

The silent bug in this field is **homology leakage**. We clustered with MMseqs2 at 30% identity, coverage 0.8 on the shorter sequence, and put **whole clusters** in train or test. 21,337 peptides, about 10.7k AMPs from DRAMP, 10.7k non-AMPs from AMPlify. 72 clusters still mix AMP and non-AMP; they stay in one fold.

On that **hard** split, a random forest on composition and charge gets **ROC-AUC 0.95**, accuracy 0.87. Frozen ESM-2 35M is 0.945. A small CNN is 0.942. Frozen ESM-2 150M is 0.952 — a **tie**. We did not LoRA; validation was 0.937. Random-split RF is 0.98; that extra is leakage. We quote 0.95.

The demo’s main number is **Platt-calibrated RF**. CNN heatmaps are explanations, not mechanisms. Magainin-2 is **in training**. This is not a wet-lab AMP test.”

### 4 minutes

Use the 90-second core, then add:

- Cleaning: 5–100, B/Z/U/O/J to X, 19 conflicts kept as AMP, extra AMPlify imbalanced negatives because balanced set was short.
- Calibration: RF ECE 0.078 to 0.023; CNN T about 1.28.
- Demo live: paste magainin, point at banner, point at RF probability, open Metrics, contrast homology vs random.
- Other teams with GO/Pfam: “different problem, usually no cluster split, our VRAM cannot fine-tune a proteome GO model this week.”
- Close: “We chose one functional axis, controlled the leak, calibrated confidence, and labeled our explanations. That is the assistant we could defend.”

If they ask “Nature-level?”: “No. That needs synthesized novel peptides and assays. This is a homology-aware filter with a working demo.”

---

*Locked numbers only. If a figure disagrees with `reports/phase_*_report.md` or `reports/calibration/SUMMARY.md`, those reports win.*
