# AMPscan

**AMPscan** is a homology-aware computer program that reads a short protein fragment (a *peptide*) and estimates how much that fragment looks like a known **antimicrobial peptide (AMP)** versus a peptide that is *not* labeled as an AMP. The estimate is a probability **P(AMP)** between 0 and 1, plus a residue-level plot from a small neural network that shows which amino acids pushed that network’s score.

This article is a full walkthrough. It assumes **no** prior knowledge of biological databases, peptide chemistry, or bioinformatics jargon. Every term is defined the first time it appears. Numbers below are **locked** evaluation results. They are not estimates.

> [!IMPORTANT]
> AMPscan is **not** a laboratory assay. A high P(AMP) means “this string of letters resembles DRAMP AMPs more than AMPlify non-AMPs on a homology-held-out test.” It does **not** mean “this peptide will kill bacteria in a dish or in an animal.”

**Official hackathon title:** *AI-Based Protein and Biomolecule Classification Assistant* (NIT Raipur internal SIH-style event, PS20).  
**What we actually shipped:** binary AMP vs non-AMP classification on peptides of length 5–100.

| | |
| --- | --- |
| **Primary score** | Platt-calibrated Random Forest **P(AMP)** |
| **Reported result** | Homology-test ROC-AUC **0.9515** (Random Forest) |
| **Leakage control (not the reported result)** | Random-split RF ROC-AUC **0.9791** — same peptides, clusters ignored, so close homologs can sit in both train and test |
| **Code license** | MIT (`LICENSE`) — code only, not the sequence databases |
| **Data licenses** | DRAMP and AMPlify sequences are **CC BY 4.0** (cite the papers; we do not own them) |

**Related pages in this repository**

- Study pack (same numbers): [`reports/STUDY_GUIDE.md`](reports/STUDY_GUIDE.md) · [`reports/defense/AMPscan_Study_Guide.pdf`](reports/defense/AMPscan_Study_Guide.pdf)
- Honest limits: [`reports/LIMITATIONS.md`](reports/LIMITATIONS.md)
- Mixed AMP / non-AMP clusters: [`reports/mixed_clusters.md`](reports/mixed_clusters.md)
- Data licenses and raw counts: [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md)
- Streamlit demo notes (fallback): [`app/README.md`](app/README.md)
- FastAPI + Next.js UI: [`services/predict_api/README.md`](services/predict_api/README.md) · [`reports/frontend_phase_report.md`](reports/frontend_phase_report.md)

---

## Contents

1. [How to read this page](#how-to-read-this-page)
2. [What the program does in one picture](#what-the-program-does-in-one-picture)
3. [Biology from zero](#biology-from-zero)
4. [How computers store sequences: FASTA](#how-computers-store-sequences-fasta)
5. [What a biological database actually is](#what-a-biological-database-actually-is)
6. [The two databases AMPscan uses](#the-two-databases-ampscan-uses)
7. [The prediction problem, stated carefully](#the-prediction-problem-stated-carefully)
8. [The silent bug: homology leakage](#the-silent-bug-homology-leakage)
9. [Scope: what is in, what is out](#scope-what-is-in-what-is-out)
10. [End-to-end pipeline](#end-to-end-pipeline)
11. [Walkthrough: building the dataset](#walkthrough-building-the-dataset)
12. [Walkthrough: clustering with MMseqs2](#walkthrough-clustering-with-mmseqs2)
13. [Walkthrough: features the Random Forest sees](#walkthrough-features-the-random-forest-sees)
14. [Walkthrough: the four model families](#walkthrough-the-four-model-families)
15. [How to read the scores (metrics)](#how-to-read-the-scores-metrics)
16. [Locked homology-test results](#locked-homology-test-results)
17. [Calibration (making 0.90 mean ~90%)](#calibration-making-090-mean-90)
18. [Explainability: Integrated Gradients and occlusion](#explainability-integrated-gradients-and-occlusion)
19. [The web application and API](#the-web-application--api-v11)
20. [How to run the demo](#how-to-run-the-demo)
21. [Worked example: magainin-2 from letters to P(AMP)](#worked-example-magainin-2-from-letters-to-pamp)
22. [Limitations](#limitations)
23. [Glossary](#glossary)
24. [Repository layout](#repository-layout)
25. [References](#references)

---

## How to read this page

This README is meant to be read **top to bottom the first time**, not as a marketing blurb.

| If you have… | Read |
| --- | --- |
| 10 minutes | [What the program does](#what-the-program-does-in-one-picture), [Scope](#scope-what-is-in-what-is-out), [Locked results](#locked-homology-test-results), [Limitations](#limitations) |
| 30 minutes | Add [Biology from zero](#biology-from-zero), [Biological databases](#what-a-biological-database-actually-is), [Homology leakage](#the-silent-bug-homology-leakage), [MMseqs2](#walkthrough-clustering-with-mmseqs2) |
| A question about FASTA / DRAMP / ROC-AUC | Jump to that heading, or the [Glossary](#glossary) |

> [!NOTE]
> **Convention used here.** Words in *italics* on first use are being defined. **Bold** marks key terms. Code and file names use `monospace`.

---

## What the program does in one picture

A user pastes letters. Those letters are amino acids (the 20 building blocks of proteins). AMPscan checks that the string is a legal peptide, then returns a calibrated probability and an optional heatmap.

```text
  you type (or upload FASTA)

        GIGKFLHSAKKFGKAFVGEIMNS
        │
        ▼
  length 5–100?  letters in the amino-acid alphabet?
        │ yes
        ▼
  ┌─────────────────────────────────────────────┐
  │  PRIMARY: Random Forest on composition       │
  │  (how often each amino acid / pair appears,  │
  │   net charge, hydrophobicity)                │
  │  → Platt calibration → P(AMP)                │
  │  Label = AMP if P ≥ 0.5 else non-AMP         │
  └─────────────────────────────────────────────┘
        │
        ▼
  SECONDARY (same sequence, different model):
  1D convolutional net on a 21×100 one-hot grid
  → divide logit by T = 1.283 → CNN P(AMP)
  → Integrated Gradients heatmap (which positions
     pushed the CNN, not a wet-lab mechanism)
```

Hardware used to train and embed: **NVIDIA RTX 5060 Laptop GPU, 8 GB VRAM**, 16 GB RAM.

---

## Biology from zero

### Cells, proteins, and peptides

Living cells are built and operated by **proteins**: long chains of smaller units called **amino acids**. A typical human protein is a few hundred amino acids. A **peptide** is simply a **short** protein chain. AMPscan only accepts peptides of **5 to 100** amino acids. A 400-amino-acid enzyme is out of spec and the demo **rejects** it.

Think of amino acids as letters and a peptide as a short word. The chemistry of those letters (charge, water-hating vs water-loving) is what AMPs often use to punch holes in bacterial membranes.

### The 20 standard amino acids

Proteins in this project are written with the **IUPAC one-letter code**. There are 20 common amino acids in the genetic code:

| Letter | Name | Rough chemical personality (enough for this project) |
| --- | --- | --- |
| **K**, **R** | lysine, arginine | **Positive** charge at pH 7. Classic AMP residues. |
| **D**, **E** | aspartate, glutamate | **Negative** charge at pH 7. |
| **H** | histidine | Weakly positive; depends on pH. |
| **F**, **W**, **Y**, **I**, **L**, **V**, **M**, **A** | aromatics / hydrophobics | Water-hating. AMPs often put these on one face of a helix. |
| **S**, **T**, **N**, **Q** | polar | Mix with water; not strongly charged. |
| **G**, **P** | glycine, proline | Flexible / helix-breaking. Common in short peptides. |
| **C** | cysteine | Can form disulfide bridges. |

AMPs in textbooks are often **cationic** (net positive, lots of K/R) and **amphipathic** (one face charged, one face oily). That cartoon is why a Random Forest on *composition* (letter frequencies) can already be strong on this task. It is also why an Integrated Gradients plot that lights up K/R is **consistent with the cartoon**, not proof of a killing mechanism.

### Ambiguous letters and X

Real FASTA files sometimes contain non-standard or ambiguous letters. AMPscan does **not** invent a 21st amino acid chemistry for them. It maps:

| Letter in the file | Meaning in biochemistry | What we do |
| --- | --- | --- |
| **B** | D or N (asx) | rewrite as **X** |
| **Z** | E or Q (glx) | rewrite as **X** |
| **J** | I or L | rewrite as **X** |
| **U** | selenocysteine | rewrite as **X** |
| **O** | pyrrolysine | rewrite as **X** |
| **X** | unknown amino acid | **keep** |
| anything else (`*`, digits, gaps, …) | not an amino acid | **drop the whole sequence** |

**X is allowed.** Sequences that still contain junk after that mapping are discarded (48 DRAMP positives in our clean; 0 negatives).

### What an antimicrobial peptide is

An **antimicrobial peptide (AMP)** is a short chain that can damage microbes — bacteria, fungi, sometimes viruses or parasites. Many AMPs bind negatively charged microbial membranes and disrupt them. Some have additional intracellular targets. Famous named examples:

| Name | Typical origin | Sequence (one letter) | In *our* homology **training** set? |
| --- | --- | --- | --- |
| magainin-2 | frog skin | `GIGKFLHSAKKFGKAFVGEIMNS` | **yes** (`POS_DRAMP_DRAMP02271`) |
| LL-37 | human cathelicidin fragment | `LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES` | **yes** (`POS_DRAMP_DRAMP03571`) |
| melittin | honeybee venom | `GIGAVLKVLTTGLPALISWIKRKRQQ` | **yes** (`POS_DRAMP_DRAMP03002`) |

> [!WARNING]
> Those three peptides are **training examples**, not a held-out test of generalization. The demo shows a banner when you paste them.

In **this repository**, “AMP” is a **database label**: the sequence appears in DRAMP General after our filters. It is not a measurement we made in a lab.

---

## How computers store sequences: FASTA

**FASTA** is a plain-text convention invented so sequence databases and tools can share the same files. It is not a program. A record looks like this:

```text
>DRAMP02271 magainin-2
GIGKFLHSAKKFGKAFVGEIMNS
```

Rules that matter here:

1. A header line starts with `>`. Everything after `>` on that line is a name/comment. The classifier **does not use the name** to decide AMP vs non-AMP (that would be cheating).
2. Following lines are the sequence: amino-acid letters, usually uppercase.
3. A file may contain many records, one after another.
4. FASTA for **nucleotides** (DNA: A, C, G, T) exists too. AMPscan expects **protein/peptide** letters, not DNA.

You can also paste the raw letters with no `>` header. The demo accepts both. The HTTP batch API accepts up to **500** peptides per request (`POST /predict-batch`).

**Input rules enforced by the app**

| Check | Result if it fails |
| --- | --- |
| Length **5–100** inclusive | error (not a score) |
| After `B/Z/U/O/J → X`, only 20 AA + X remain | error |
| Empty / whitespace | error |

---

## What a biological database actually is

A **biological sequence database** is a curated catalog: each entry has a sequence, an accession (ID), and metadata (name, organism, literature, sometimes activity). It is closer to a library catalog than to a trained neural network.

Things that confuse first-time readers:

| Misconception | Reality |
| --- | --- |
| “The database measured that this peptide kills bacteria.” | Often it **collected a paper** that measured something, then stored the sequence. Quality varies. |
| “If it is not in the AMP database, it is inactive.” | Absence of annotation is **not** experimental inactivity. This is why our negative class is cautious. |
| “All AMP databases contain the same peptides.” | They overlap but differ in scope (natural vs synthetic, patents, clinical, hemolytic). |
| “Downloading FASTA gives us a model.” | FASTA is **data**. A model is what we train *on* that data after splitting it honestly. |

**Accession.** A stable ID such as `DRAMP02271`. We prefix cleaned positives as `POS_DRAMP_DRAMP02271` so class and source stay visible in our tables.

**License.** Many modern databases are **CC BY 4.0**: you may copy and build on the data if you **give credit**. Code in this repo is MIT. Sequences are **not** re-licensed as MIT. See [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md).

---

## The two databases AMPscan uses

We needed two piles of sequences:

- **Positives (label = 1, “AMP”)** — peptides that a specialist AMP catalog lists as antimicrobial.
- **Negatives (label = 0, “non-AMP”)** — peptides that a published AMP-prediction paper already treated as non-AMP.

We did **not** invent a homemade “download UniProt and delete anything with the word antimicrobial” filter. That is easy to get wrong and hard to audit.

### Positives: DRAMP General

**DRAMP** (*Data Repository of Antimicrobial Peptides*) is an open AMP catalog (China Pharmaceutical University and collaborators). Papers: DRAMP 3.0 (Shi et al., 2022) and DRAMP 4.0 (Ma et al., 2025). Data: **CC BY 4.0**.

DRAMP is split into subsets (general, patent, clinical, hemolytic, …). We used **General AMPs** only — the main “this is listed as an AMP” FASTA:

| | |
| --- | --- |
| File we downloaded | `general_amps.fasta` |
| URL | [DRAMP downloads](https://dramp.cpu-bioinfor.org/downloads/) |
| Raw records | **11,687** |
| License | CC BY 4.0 |

We did **not** use APD (Antimicrobial Peptide Database) or UniProt Swiss-Prot as positives. Those were written down only as fallbacks and were never pulled.

> [!NOTE]
> **DRAMP General mixes natural and synthetic AMPs.** Synthetic peptides are often designed to *look* like the cationic-amphipathic cartoon, which helps composition models. Performance on a purely natural, phylogenetically new set is untested. That is a limitation, not a footnote.

A later audit of DRAMP’s **Family** column found it mixes peptide families (Brevinin, defensin) with virus taxa (Retroviridae), and about **55%** of our cleaned AMPs have no family string. We **did not** train a 5–10 class family head. See [`reports/family_label_audit.md`](reports/family_label_audit.md).

### Negatives: AMPlify published non-AMP FASTAs

**“Non-AMP” is not a natural class.** Almost every peptide in the biosphere is *not* an AMP; databases do not ship a tidy “proven inactive” list.

**AMPlify** is a published deep-learning AMP predictor (Li et al., *BMC Genomics* 2022; data note 2023). The authors released the exact non-AMP FASTA files they used, on Zenodo, **CC BY 4.0**:

| | |
| --- | --- |
| Zenodo | [10.5281/zenodo.7320306](https://doi.org/10.5281/zenodo.7320306) |
| Files | `AMPlify_non_AMP_{train,test}_{balanced,imbalanced}.fa` |
| How they were built | UniProt-derived, length-aware filters documented in the AMPlify papers — **not** random DNA |

We took the **balanced** AMPlify non-AMPs first. After length/alphabet/dedup we still had **fewer** negatives than positives, so we added sequences from their published **imbalanced** FASTAs (**+6,579** after our pipeline). We did **not** scrape a new UniProt sample.

### Why two sources instead of one

| Role | Source | Why this one |
| --- | --- | --- |
| AMP | DRAMP General | Specialist AMP catalog, open FASTA, CC BY 4.0, enough sequences after 5–100 filter |
| non-AMP | AMPlify Zenodo FASTAs | Negatives already built for *this exact ML task*, citable, auditable |

Using AMPlify **negatives** does not mean we claim to beat the AMPlify **paper**. Different positives (they used an APD mix), different split. We claim a homology-controlled DRAMP/AMPlify set and a working demo.

---

## The prediction problem, stated carefully

**Given:** a peptide of length 5–100 written in the 20-letter alphabet (plus X).  
**Predict:** P(this sequence looks like our DRAMP positives rather than our AMPlify negatives), after we stopped close relatives from sitting in both the training pile and the test pile.  
**Show (optional):** which positions a small CNN used, without calling that a biological mechanism.

**Not predicted**

- Minimum inhibitory concentration (MIC) — “how much peptide you need to stop growth”
- Hemolysis — “does it also pop human red blood cells”
- In vivo efficacy — “does it work in a mouse”
- Gene Ontology (GO) — thousands of function labels for proteins
- Pfam / InterPro — domain families, usually searched with HMMER, not a 3-day neural net
- Full-length protein annotation

In one sentence: this is **sequence classification with calibrated confidence**; AMP vs non-AMP is the task we finished on a student laptop (8 GB GPU VRAM class).

---

## The silent bug: homology leakage

This section is the reason the repository exists.

### Homology in plain language

Two peptides are **homologous** (loosely: related) if they share enough sequence that the similarity is unlikely to be chance — often because they come from related genes or the same AMP family (many frog “magainin-like” peptides look alike).

If you **randomly shuffle** 21,000 peptides into train and test, cousins land on **both** sides. The model does not have to learn “what makes an AMP.” It memorizes “I have seen this family.” Test accuracy looks like **98%** and is a **lie** about generalization.

That failure mode is **homology leakage**. It is the default bug in protein machine learning when people skip clustering.

### What we do instead

1. Group similar sequences into **clusters** (households of relatives) with **MMseqs2**.
2. Assign **entire clusters** to train **or** validation **or** test.
3. Never split a household across those three drawers.

Then a high test score means the model handled **unseen families** (at the 30% identity threshold), not unseen copies of the same family.

The **random split** is still computed, on purpose, as a **leakage control**. Same 21,337 peptides, 70/15/15, seed 42, stratified by class, **clusters ignored**. Random-split RF ROC-AUC **0.9791**. Homology-split RF **0.9515**. The extra points are leakage. **The reported result is 0.9515.**

---

## Scope: what is in, what is out

| In | Out |
| --- | --- |
| Peptides **5–100** amino acids | Full-length proteins |
| Binary **AMP vs non-AMP** | GO / Pfam / EC / DeepLoc |
| FASTA paste or upload (batch cap 500) | MIC, hemolysis, in vivo claims |
| Homology cluster split + calibration + CNN explanations | Fine-tuned / LoRA ESM (not run) |
| Frozen ESM-2 35M and 150M as **checks** | “Bigger LM automatically wins” |

---

## End-to-end pipeline

```text
1. Download
      DRAMP General FASTA          AMPlify non-AMP FASTAs (Zenodo)
              │                                  │
              └────────────┬─────────────────────┘
                           ▼
2. Clean (same rules both classes)
      length 5–100
      uppercase; B,Z,U,O,J → X; drop leftover non-AA
      exact-sequence dedup
      same sequence in both classes → keep as AMP (19 cases)
                           │
                           ▼
3. 21,337 peptides (10,678 AMP + 10,659 non-AMP)
                           │
                           ▼
4. MMseqs2 easy-cluster
      --min-seq-id 0.3  -c 0.8  --cov-mode 1
      9,241 clusters (72 mixed AMP+non-AMP)
                           │
                           ▼
5. Whole-cluster assignment  70 / 15 / 15   seed 42
      train 14,904 | val 3,203 | test 3,230
      + a random split of the same peptides (control only)
                           │
                           ▼
6. Train on homology train (val for light selection / calibration)
      Random Forest (425 composition features)     ← PRIMARY
      L2 logistic regression (same features)
      Frozen ESM-2 35M mean-pool + linear head
      1D-CNN on 21-channel one-hot
      Frozen ESM-2 150M mean-pool + linear head    ← tie with RF; no LoRA
                           │
                           ▼
7. Calibrate on homology val, freeze, apply to test
      RF: Platt  sigmoid(a·p + b)
      CNN / ESM-35M: temperature  sigmoid(logit / T)
                           │
                           ▼
8. CNN Integrated Gradients + occlusion on selected sequences
                           │
                           ▼
9. Streamlit demo (offline): RF primary, CNN secondary + heatmap
```

No training happens when you run the demo. Weights are read-only.

---

## Walkthrough: building the dataset

Script: `scripts/build_amp_dataset.py`. Provenance dump: [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md). FASTAs themselves are **not** in the public GitHub snapshot (`.gitignore`); reconstruct from upstream if you clone only GitHub.

### Cleaning rules (locked)

1. Length **5–100** inclusive.
2. Uppercase. Map **B, Z, U, O, J → X**. Drop any sequence that still has non-amino-acid characters. **X is allowed.**
3. Exact-sequence deduplication; keep the first copy.
4. If the **same** sequence appears as both AMP and non-AMP → **keep as AMP** (19 conflicts). The AMP catalog wins over “unannotated.”

Mapped B/Z/U/O/J → X: **418** positives, **0** negatives. Dropped leftover non-AA: **48** positives, **0** negatives.

### Count table (locked)

| Stage | AMP | non-AMP |
| --- | ---: | ---: |
| Raw (DRAMP General / AMPlify **balanced**) | 11,687 | 4,173 |
| After length 5–100 | 11,459 | 4,099 |
| After alphabet filter | 11,411 | 4,099 |
| After exact dedup | 10,678 | 4,099 |
| Plus AMPlify **imbalanced** (because n_neg &lt; n_pos) | — | +6,579 |
| After 19 cross-class conflicts resolved (keep AMP) | **10,678** | **10,659** |

Combined clean set: **21,337** peptides. Almost balanced on purpose so accuracy is readable. Real proteomes are **not** 50/50 AMP (see [Limitations](#limitations)).

### Homology fold sizes

| Fold | n | AMP | non-AMP |
| --- | ---: | ---: | ---: |
| train | 14,904 | 7,444 | 7,460 |
| val | 3,203 | 1,611 | 1,592 |
| test | 3,230 | 1,623 | 1,607 |

Random-split control (clusters ignored): train 14,936 / val 3,201 / test 3,200.

---

## Walkthrough: clustering with MMseqs2

### What MMseqs2 is

**MMseqs2** (*Many-against-Many sequence searching*) is a fast open-source tool that compares protein sequences and can **cluster** them by similarity (Steinegger & Söding, 2017). It is not a classifier. Think: “put close relatives in the same household.”

We used the convenience workflow `easy-cluster` on the combined cleaned FASTA.

### The three flags

```bash
mmseqs easy-cluster combined_clean.fasta cluster cluster_tmp \
  --min-seq-id 0.3 \
  -c 0.8 \
  --cov-mode 1
```

| Flag | Literal meaning | Why we chose it |
| --- | --- | --- |
| `--min-seq-id 0.3` | Two sequences must share about **30%** identity in the alignment to cluster together | **Stricter than the 70% people often use.** Harder test, more honest. 70% still lets close cousins through. |
| `-c 0.8` | **Coverage 80%** | A short match of a few letters is not enough. |
| `--cov-mode 1` | Coverage is measured on the **shorter** sequence | Fair when a 20-aa peptide is compared to a 90-aa peptide. The short one must be 80% covered. Otherwise a tiny peptide can “hit” a long chain on a fragment and look unrelated by coverage. |

### Whole-cluster assignment

A **cluster** is one household. **Every member goes to the same fold** — train or val or test. Targets: **70% / 15% / 15%** of sequences, random seed **42**. Clusters were stratified as AMP-only / non-AMP-only / mixed so class balance does not collapse.

**9,241 clusters**

| Kind | Count | Meaning |
| --- | ---: | --- |
| AMP-only | 4,778 | household of AMPs |
| non-AMP-only | 4,391 | household of non-AMPs |
| **mixed** | **72** | **both** labels in one household |

### Mixed clusters are documented, not hidden

**72** clusters contain both an AMP and a non-AMP (264 AMP members, 445 non-AMP). They still go to **one** fold, so they do **not** leak across train/test.

They **do** mean 30% identity is not a perfect biological wall: a short AMP can sit inside a longer UniProt-like peptide. Mixed-cluster AMPs are shorter on average (**46.6** aa) than mixed-cluster non-AMPs (**62.9** aa). Full table: [`reports/mixed_clusters.md`](reports/mixed_clusters.md).

> [!TIP]
> We clustered at 30% identity, 80% coverage on the shorter sequence, and never split a cluster. 72 mixed clusters exist; they stay in one fold. That is a documented limit of the threshold, not a silent leak.

---

## Walkthrough: features the Random Forest sees

The winning model does **not** read the sequence as language. It reads **425 numbers** computed from the letters.

### Amino-acid composition (AAC) — 20 numbers

For each of the 20 standard amino acids, the **fraction** of the peptide that is that letter. Example: a 23-mer with 4 lysines (K) has AAC_K = 4/23.

X is not given its own AAC slot in the 20-vector; it is a rare unknown and is absorbed by the rest of the pipeline (CNN has an explicit X channel).

### Dipeptide composition (DPC) — 400 numbers

Count of each ordered pair (AA, AA) divided by the number of consecutive pairs (length − 1). “KK” in magainin-2 is a real local pattern; DPC can see it. 20 × 20 = 400.

### Physicochemical descriptors — 5 numbers

Locked in `data/processed/features/feature_names.json`:

| Feature | Meaning |
| --- | --- |
| **length** | Number of amino acids, including X (5–100). |
| **net_charge_pH7** | Henderson–Hasselbalch charge at pH 7: N- and C-termini plus D, E, C, Y, H, K, R. |
| **GRAVY** | Mean Kyte–Doolittle hydropathy over the 20 standard letters (X ignored in the average). Higher → more hydrophobic. |
| **hydrophobic_moment** | Eisenberg amphipathic moment, 100° per residue (α-helix assumption), divided by length. Large when oily and polar residues sit on opposite faces of a helix. |
| **aromatic_fraction** | Fraction of F, W, Y. |

**GRAVY** is a 1982 hydrophobicity scale: each amino acid has a number (I, V, L high; D, E, K, R low/negative). Average them. AMPs that need an oily face often sit in a characteristic GRAVY band, but GRAVY alone is not a classifier.

**Net charge at pH 7.** Lysine and arginine contribute positive charge; aspartate and glutamate negative; cysteine and tyrosine can deprotonate; histidine is a partial positive; termini add roughly +1 (NH₃⁺) and −1 (COO⁻). Many membrane-active AMPs are **net positive**, which is why this one number is so informative.

**Hydrophobic moment** is the cheap computer version of “amphipathic helix”: imagine the chain as a spiral with 100 degrees per amino acid, add up hydrophobicity as a 2-D arrow, and take the arrow’s length. It does **not** prove the peptide really folds as a helix in a membrane.

**X in the counts.** Unknown letters are ignored in AAC, DPC, GRAVY, and moment. They still count toward **length** and the aromatic-fraction denominator.

**Total: 20 + 400 + 5 = 425 features.** Logistic regression sees them after a StandardScaler fit on **train only**. The Random Forest uses the raw 425 numbers (trees do not need scaling), 200 trees, `class_weight=balanced`.

### Why composition is so strong here

ESM-2 was trained on **proteins**, often long, evolutionary. Our items are **5–100 aa**, and the AMP signal is largely “lots of K/R, hydrophobic/aromatic faces, length in peptide range.” Those facts **are** AAC, DPC, charge, and GRAVY. A 200-tree forest on 425 numbers is enough to *match* a frozen 150-million-parameter language model on this split. That is a result.

---

## Walkthrough: the four model families

All trained on **homology train**, light use of **homology val**, reported on **homology test**. Seed 42. The demo’s primary number is the **calibrated Random Forest**, not ESM.

### 1. Random Forest (primary)

A **Random Forest** is many decision trees that vote. Each tree sees random subsets of the 425 features and random subsets of training peptides. It is strong on tabular composition data, runs on CPU, and is what we ship.

- 200 trees in the locked run (Phase 2)
- Homology-test confusion matrix: **TN 1,388 · FP 219 · FN 190 · TP 1,433** (n = 3,230)

### 2. L2 logistic regression (baseline, not shipped)

Same 425 features, linear model with L2 penalty. Weaker (ROC-AUC **0.9016** homology test). Kept so we can say the forest is not “just linear composition.”

### 3. Frozen ESM-2 + linear head

**ESM-2** (*Evolutionary Scale Modeling 2*, Lin et al., *Science* 2023) is a **protein language model**: a transformer trained to reconstruct masked amino acids on huge protein corpora. It produces a vector at every residue.

**Frozen** means we **do not update** ESM-2’s millions of weights. We:

1. Run the peptide through ESM-2.
2. **Mean-pool** residue vectors (average them; skip start/end/pad tokens).
3. Train only a **linear** classifier (plus a scaler) on that vector.

| Checkpoint | Hidden size after mean-pool | Homology-test ROC-AUC |
| --- | ---: | ---: |
| `esm2_t12_35M_UR50D` (35 million parameters) | 480 | **0.9450** |
| `esm2_t30_150M_UR50D` (150 million) | 640 | **0.9521** |

**LoRA** (Low-Rank Adaptation) would cheaply fine-tune extra matrices inside ESM. Protocol: only if 150M **validation** ROC-AUC came within **0.01** of RF val (**0.9513**). It was **0.9372**. **LoRA was not run.** Frozen 150M vs RF on test is **Δ +0.0006** → **tie**.

The Streamlit demo does **not** load ESM-2 (VRAM). 150M appears only as a locked number on the Metrics page.

### 4. 1D convolutional neural network (secondary + explanations)

A **1D-CNN** slides small filters along the sequence, like a motif detector.

**Input encoding: one-hot, 21 channels × 100 positions.**

At each position, a vector of 21 zeros and a single 1 indicating which letter is there (20 amino acids + X). Peptides shorter than 100 are padded. Length &gt; 100 never enters (rejected earlier).

Three convolutional layers, then a linear head to one **logit**. The demo applies temperature **T = 1.2833** (shown as 1.283) before the sigmoid.

We keep the CNN because **Integrated Gradients** on a one-hot grid is straightforward: each residue gets a score. Doing that on a forest of 425 global features would not yield a per-letter heatmap.

---

## How to read the scores (metrics)

None of these is “percent bacteria killed.”

| Metric | What it measures | Coin-flip | Perfect | What we got (RF homology test) |
| --- | --- | ---: | ---: | ---: |
| **Accuracy** | Fraction of labels correct at threshold 0.5 | ~0.50 on a balanced test | 1.0 | **0.8734** |
| **Macro-F1** | F1 for AMP and F1 for non-AMP, averaged | ~0.50 | 1.0 | **0.8734** (test is ~50/50, so it tracks accuracy) |
| **ROC-AUC** | Ranking: if you pick a random AMP and a random non-AMP, P(AMP score &gt; non-AMP score) | 0.50 | 1.0 | **0.9515** ← **headline** |
| **PR-AUC** | Ranking with emphasis on the AMP class | ~ prevalence (here ~0.5) | 1.0 | **0.9542** |

> [!WARNING]
> **ROC-AUC is not accuracy.** 0.9515 does **not** mean “95% of peptides are labeled correctly.” Accuracy at 0.5 is **87%**. ROC-AUC asks whether AMPs are *ranked above* non-AMPs.

**Confusion matrix vocabulary** (RF homology test)

|  | Predicted non-AMP | Predicted AMP |
| --- | ---: | ---: |
| **True non-AMP** | TN = 1,388 | FP = 219 |
| **True AMP** | FN = 190 | TP = 1,433 |

- **FP (false positive):** looks like an AMP to the model, labeled non-AMP in the set.  
- **FN (false negative):** is labeled AMP, model said no.

**Calibration metrics** (next section): **ECE**, **Brier**. They ask “when we say 0.90, are we right about 90% of the time?”, which ROC-AUC does *not* ask.

---

## Locked homology-test results

Cluster split as above. Test **n = 3,230**.

| Model | What it sees | Accuracy | Macro-F1 | ROC-AUC | PR-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| **Random Forest (primary)** | AAC + DPC + physchem (425) | **0.8734** | **0.8734** | **0.9515** | **0.9542** |
| L2 logistic regression | same 425 | 0.8375 | 0.8374 | 0.9016 | 0.9113 |
| Frozen ESM-2 35M + linear | 480-d mean-pool | 0.8622 | 0.8622 | 0.9450 | 0.9424 |
| 1D-CNN (one-hot) | 21 × 100 grid | 0.8650 | 0.8648 | 0.9424 | 0.9465 |
| Frozen ESM-2 150M + linear | 640-d mean-pool | 0.8762 | 0.8761 | 0.9521 | 0.9516 |

ESM-2 150M vs RF: **Δ +0.0006** → **tie**. 150M val ROC-AUC was **0.9372**, so LoRA was **not** run.

---

### External tool comparison (Cohort 1 homology test, n = 3,230)

We evaluated 4 external published AMP tools under independent environments on our locked test set:

| Model / Tool | Architecture | Evaluated n | Skips | Accuracy | Macro-F1 | ROC-AUC | PR-AUC | $\text{ECE}_{15}$ | Throughput (seq/s) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **AMPscan RF (Platt)** | 425-D Tabular RF | 3,230 | **0** | **0.8765** | **0.8765** | **0.9515** | **0.9542** | **0.0235** | 28.6 |
| **AMPscan 1D-CNN (T)** | 21x100 Grid + Temp | 3,230 | **0** | 0.8650 | 0.8648 | **0.9424** | 0.9465 | 0.0403 | 28.6 |
| **Macrel ONNX** | 22-D PhysChem RF | 3,182 | 48 (X) | 0.7854 | 0.7754 | **0.9491** | 0.9503 | 0.2035 | **6,601.7** |
| **AMPlify balanced** | 5-Fold BiLSTM + Attn | 3,182 | 48 (X) | 0.8558 | 0.8534 | **0.9277** | 0.9450 | 0.1183 | 14.9 |
| **AI4AMP PC6** | 1D-CNN-LSTM on PC6 | 3,230 | **0** | 0.7449 | 0.7431 | **0.7905** | 0.8288 | 0.1535 | 572.5 |
| **AmpGram** | 2-Stage RF on n-grams | 3,001 | 229 | 0.7234 | 0.7234 | **0.7898** | 0.8265 | 0.1643 | 0.93 |

**Paired Bootstrap Significance ($N=3,182$ common):**
- **vs. Macrel**: $\Delta\text{ROC} = +0.0014$, 95% CI $[-0.0049, +0.0075]$ (statistical tie on discriminative ranking; AMPscan wins on calibration **ECE 0.023 vs 0.204**).
- **vs. AMPlify**: $\Delta\text{ROC} = +0.0228$, 95% CI $[0.0127, 0.0324]$ (statistically significant win over AMPlify on strict homology clusters).

---

### External OOD Benchmark: Cohort 2b (Length-Matched DBAASP, n = 22,380)

Evaluated on 11,190 novel synthetic DBAASP AMPs vs 11,190 length-matched UniProt fragment windows ($<30\%$ MMseqs2 identity to train; median length 14 aa vs 14 aa):

| Model | Evaluated n | Skips | Accuracy @ 0.5 | MCC | ROC-AUC | PR-AUC | $\text{ECE}_{15}$ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **AMPscan RF (Platt)** | 22,380 | 0 | 0.6449 | 0.3765 | **0.9030** | 0.9205 | 0.2767 |
| **Macrel ONNX** | 20,426 | 1954 (X) | 0.8222 | 0.6554 | **0.8998** | 0.9017 | 0.1058 |
| **AMPlify balanced** | 20,426 | 1954 (X) | 0.8216 | 0.6421 | **0.8991** | 0.9075 | 0.0867 |
| **AI4AMP PC6** | 22,380 | 0 | 0.8081 | 0.6287 | **0.8786** | 0.9031 | 0.0870 |

> [!NOTE]
> **Key Takeaway**: Cross-tool ranking remains a statistical tie at ~0.90 ROC. Platt calibration parameters fit on natural DRAMP sets do not transfer directly to short fragment background distributions ($P \ge 0.5$ accuracy is 0.645); use threshold-invariant ROC ranking. The earlier unconstrained 0.9935 table was length-confounded (14 aa vs 76 aa).

---

### Discovery Triage & Operating Points

In peptide discovery screens where AMPs are rare, raising the classification threshold provides high-precision candidates:

| Model | Threshold $P \ge$ | Candidates Selected | Precision | Recall | Specificity |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **AMPscan RF (Platt)** | 0.50 | 1,632 | 0.875 | 0.880 | 0.873 |
| **AMPscan RF (Platt)** | 0.80 | 1,255 | 0.948 | 0.733 | 0.960 |
| **AMPscan RF (Platt)** | **0.90** | **1,059** | **0.974** | **0.635** | **0.983** |
| **AMPscan RF (Platt)** | 0.95 | 863 | 0.987 | 0.525 | 0.993 |

---

**Random-split test (leakage control only)**

| Model | ROC-AUC |
| :--- | ---: |
| Random Forest | **0.9791** |
| Frozen ESM-2 35M | 0.9657 |
| 1D-CNN | 0.9749 |

> [!IMPORTANT]
> **The reported result is homology-split RF ROC-AUC 0.9515.** Random-split **0.9791** is the leaky control (related peptides can appear in both train and test).

On this task a frozen 150M embedding **ties** a forest on charge and composition. ESM stays as a check; the shipped primary model is the RF.

---

## Calibration (making 0.90 mean ~90%)

A model can **rank** well (high ROC-AUC) and still be **over-confident** (“I’m 99% sure” when it is wrong 20% of the time). **Calibration** is a small extra map from raw scores to probabilities, fit **only on homology validation**, then frozen and applied to test. Ranking barely changes; confidence does.

### Platt scaling (Random Forest)

The forest outputs a probability p_rf. We fit two numbers **a**, **b** on val:

```text
P_calibrated = sigmoid(a × p_rf + b)
```

Locked: **a = 10.0847**, **b = −5.0839**.  
This is **not** temperature scaling (temperature scaling is used only for the CNN and ESM-35M heads).

### Temperature scaling (CNN and ESM-35M)

Neural nets output a **logit** (raw number; sigmoid turns it into a probability). **Temperature scaling** (Guo et al., 2017) divides the logit by T &gt; 0:

```text
P_calibrated = sigmoid(logit / T)
```

T &gt; 1 **cools** over-confidence. T is a single number fit on val.

| Head | T |
| --- | ---: |
| 1D-CNN | **1.2833** (app displays 1.283) |
| ESM-2 35M | **1.2855** |

### Expected Calibration Error (ECE)

Split predictions into **15** equal-width probability bins. In each bin, compare (average predicted P) vs (actual AMP frequency). Take the weighted absolute difference. **Lower is better.**

| Model | Method | Homology-test ECE before | after | ROC-AUC |
| --- | --- | ---: | ---: | ---: |
| RF | Platt | 0.078 | **0.023** | 0.9515 unchanged |
| ESM-2 35M | T = 1.2855 | 0.038 | **0.019** | 0.9450 unchanged |
| 1D-CNN | T = 1.2833 | 0.062 | **0.040** | 0.9424 unchanged |

App **primary** number = Platt-calibrated RF P(AMP). **Secondary** = CNN P(AMP) after T.

> [!NOTE]
> Calibration is for a **~50/50** test. On a real proteome (AMP prevalence tiny), even a calibrated 0.90 can be a poor *decision* unless you raise the threshold. See limitation 2.

---

## Explainability: Integrated Gradients and occlusion

Only the **1D-CNN** was attributed (Phase 6). The forest is the better classifier; the CNN is the one whose input is a per-residue grid, so it can draw a heatmap.

### Integrated Gradients (IG)

**Integrated Gradients** (Captum implementation) asks: if we start from a blank peptide (all zeros) and fade in the real one-hot encoding, how much does each input channel contribute to the AMP **logit**?

Per-residue score = sum of IG over the 21 channels at that position. The heatmap is that vector along the sequence. Red / high |IG| on K or R is **the CNN using cationic letters**, not a crystal structure of membrane insertion.

### Occlusion (sanity check)

Zero out one residue, recompute the logit, take Δ = logit_full − logit_occluded. Cheap, local. Pearson correlation IG vs occlusion on the three canonical peptides: magainin-2 **0.89**, LL-37 **0.35**, melittin **0.91**. LL-37’s lower agreement is a reminder that attribution methods disagree; we still do not call either a mechanism.

### Training-set examples

| Peptide | Sequence | In homology **train**? | ID |
| --- | --- | --- | --- |
| magainin-2 | `GIGKFLHSAKKFGKAFVGEIMNS` | **yes** | `POS_DRAMP_DRAMP02271` |
| LL-37 | `LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES` | **yes** | `POS_DRAMP_DRAMP03571` |
| melittin | `GIGAVLKVLTTGLPALISWIKRKRQQ` | **yes** | `POS_DRAMP_DRAMP03002` |

None of them are in val/test. Showing a pretty heatmap on a training sequence is **illustration**, not validation.

---

## The Web Application & API (v1.1)

AMPscan provides a dual interface: a flagship **Next.js 14 web application** (port 3000) powered by a high-throughput **FastAPI inference service** (port 8000), alongside an offline Streamlit fallback (port 8501).

### Flagship Next.js 14 Workbench (`/predict`)

- **Calibrated Primary Score**: Platt-calibrated Random Forest $P(\text{AMP})$ with secondary Temperature-scaled 1D-CNN.
- **In-Memory Nearest-Neighbor Matching (`TrainIndex`)**: Compares queries against all 14,904 homology-train sequences in $<0.3$ ms, flagging exact matches and computing % identity so users can distinguish generalization from memorization.
- **High-Throughput Batch Scoring (`/predict-batch`)**: Paste up to **500 multi-FASTA sequences** with instant single-roundtrip vectorized scoring.
- **Sliding-window scanner (`/scan`)**: For chains longer than 100 aa (API cap 5,000 aa), scores peptide-sized windows with the locked RF. Window scores are **not** a protein-level AMP call. High P near the C-terminus of hCAP-18 is LL-37 (a **training** peptide), not a newly discovered domain.
- **Interactive Mutation Workbench**: Click any residue on the CNN Integrated Gradients track to test *in silico* point mutations in real time.

### Scientific Evidence Dashboard (`/metrics`)

- **4 Comparative Tabs**:
  1. **Models**: Homology-held-out metrics, paired bootstrap significance vs. Macrel and AMPlify, and multi-tool ROC comparison.
  2. **Homology vs. Random**: Demonstrates the ~0.979 vs 0.9515 leakage gap.
  3. **Calibration**: Pre- and post-calibration reliability diagrams (ECE $0.078 \rightarrow 0.023$).
  4. **External (2b)**: 22,380 length-matched DBAASP synthetic OOD validation and operating point triage ($P \ge 0.90$).

---


## How to run the demo

Weights and FASTAs are **not** in the public GitHub snapshot (`.gitignore`). Inference needs the local `models/` and `data/` trees on the machine that trained them.

Primary UI is **one origin: http://localhost:3000**. Next.js serves the site and proxies `/api/*` to FastAPI on :8000. Streamlit remains as a fallback.

From the project root, `amp-data` env (Python 3.12 + nodejs):

```bash
chmod +x scripts/run_web.sh
./scripts/run_web.sh
```

Then open **http://localhost:3000** only.

Manual two-process equivalent:

```bash
uvicorn main:app --app-dir services/predict_api --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

`frontend/.env.local` sets `NEXT_PUBLIC_API_URL=/api`. Dark mode is the default; a Dark/Light toggle sits in the header.

**CLI (no website; same locked RF):**

```bash
chmod +x scripts/install_ampscan_cli.sh
./scripts/install_ampscan_cli.sh          # drops `ampscan` into amp-data/bin
conda activate amp-data                   # or call the wrapper path directly

ampscan predict peptides.fasta -o scores.tsv
ampscan predict -s GIGKFLHSAKKFGKAFVGEIMNS
ampscan scan protein.fasta --window 25 --step 1 -o windows.tsv
```

`predict` is peptides **5–100 aa**. `scan` slides that window on longer chains and is **not** a protein-level AMP call. The HTTP batch cap of 500 is “how many peptides,” not 500 amino acids.

**Fallback (unchanged):**

```bash
streamlit run app/streamlit_app.py
```

**Quick demo path**

1. Open **http://localhost:3000/predict** (or click Classify).
2. Magainin-2 is prefilled: `GIGKFLHSAKKFGKAFVGEIMNS`. Run it.
3. The number to trust is **calibrated RF P(AMP)**. Magainin-2 is in the homology **train** fold — the UI banners that.
4. The residue bar is CNN Integrated Gradients (attribution), not a wet-lab mechanism.
5. **Metrics** compares homology-test **0.9515** with the random-split leakage control **0.9791**.
6. Optional: paste a chain longer than 100 aa. `predict` rejects it; `scan` scores windows.

---

## Worked example: magainin-2 from letters to P(AMP)

This is the same peptide the demo uses. It is **in train**; the numbers below teach the *path*, not a held-out proof.

**1. Letters.** `GIGKFLHSAKKFGKAFVGEIMNS` — 23 amino acids, all in the standard 20. No mapping to X.

**2. Biology sketch.** Frog-skin AMP. Several **K** (lysine, + charge). Hydrophobic stretch (F, L, I, V, A, M). Textbook cationic amphipathic peptide.

**3. Forest features (conceptual).** AAC_K is high; DPC includes `KK`; length 23; net charge positive at pH 7; GRAVY in a hydrophobic-enough band. 425 numbers go into the locked RF.

**4. RF → Platt.** Raw forest probability is passed through `sigmoid(10.0847 · p − 5.0839)`. Label AMP if calibrated P ≥ 0.5.

**5. CNN path.** 23 one-hot columns, pad to 100. Convolution → logit → divide by 1.2833 → sigmoid. IG heatmap often highlights K and hydrophobic positions.

**6. What this example is not.** Magainin-2 is in the homology **training** set, so this walkthrough teaches the *pipeline*, not held-out performance. Held-out performance is ROC-AUC **0.9515** on **3,230** test peptides whose clusters never appeared in train.

---

## Limitations

Full write-up: [`reports/LIMITATIONS.md`](reports/LIMITATIONS.md).

1. **Pattern matching on a balanced peptide set**, not a measurement of antimicrobial function. High P(AMP) means resemblance to DRAMP-style AMPs vs AMPlify-style non-AMPs.
2. **The test is ~50/50.** Real proteomes and metagenomes are extremely AMP-sparse. Accuracy 0.87 and ROC-AUC 0.95 will **not** translate to usable precision at realistic prevalence without a much higher threshold (and a large recall cost).
3. **Negatives are “not annotated as AMP,”** not experimentally inactive. Some labeled non-AMPs might be active if assayed; some AMPs are weak, condition-specific, or synthetic.
4. **DRAMP General includes synthetic AMPs.** Composition models (the winning RF) are helped by designed amphipathic cations. Untested on a purely natural, phylogenetically new set.
5. **30% identity / 80% shorter-seq coverage is a control, not a biological independence guarantee.** **72 mixed clusters** exist. Folds stay unsplit; the threshold does not fully separate labels.
6. **Random-split metrics are inflated.** RF ROC-AUC 0.98 vs 0.95 on the cluster split. Random-split is a leakage control, not a generalization result.
7. **Frozen ESM-2 35M and the 1D-CNN did not beat the RF** (0.945 and 0.942 vs 0.952). Frozen 150M **tied**. Bigger language models are not implied to help on 5–100 aa AMP vs peptide.
8. **Explainability is model-dependent, not mechanism.** IG on the CNN often highlights K/R and hydrophobics. Magainin-2, LL-37, and melittin are **in train**.
9. **Out of scope:** full-length proteins, GO, Pfam, EC, MIC, hemolysis, in vivo efficacy. This repo does not include those models and does not promise them.

No LoRA, no GO/Pfam/DeepLoc heads, and no further training are part of this snapshot.

---

## Glossary

| Term | Meaning in this project |
| --- | --- |
| **Amino acid** | One of 20 standard protein building blocks, written as a single letter (A, C, D, …). |
| **Peptide** | Short amino-acid chain. Here, length 5–100. |
| **Protein** | Longer chain; usually out of spec for AMPscan. |
| **AMP** | Antimicrobial peptide: database label “listed as AMP in DRAMP General,” not a lab result we ran. |
| **non-AMP** | Sequence from AMPlify’s published negative FASTAs: not annotated as AMP, not proven inactive. |
| **FASTA** | Text format: `>` name, then letters. |
| **Accession** | Stable database ID (e.g. DRAMP02271). |
| **DRAMP** | Open AMP sequence repository (CC BY 4.0). Our positives. |
| **AMPlify** | Published AMP predictor; we used their **negative FASTAs** (Zenodo, CC BY 4.0), not their neural net. |
| **UniProt** | Huge protein catalog. AMPlify’s negatives were derived from UniProt-style filters; we did not re-scrape it. |
| **Homology** | Relatedness by sequence similarity; cousins look alike. |
| **Identity** | Fraction of aligned positions with the same letter. We cluster at **30%**. |
| **Coverage** | Fraction of a sequence that is inside the alignment. We require **80% of the shorter** sequence. |
| **MMseqs2** | Fast sequence clustering/search tool. |
| **Cluster** | A bag of similar sequences. Assigned wholly to train or val or test. |
| **Homology split** | The honest split. Whole bags stay together. |
| **Random split** | Shuffle sequences; cousins can land on both sides. Leakage control only. |
| **Train / val / test** | Learn weights / fit calibration and light choices / report once. Test is not for shopping models. |
| **AAC** | Amino-acid composition: 20 frequencies. |
| **DPC** | Dipeptide composition: 400 pair frequencies. |
| **GRAVY** | Average Kyte–Doolittle hydrophobicity. |
| **Hydrophobic moment** | Eisenberg amphipathicity score assuming a 100°/residue helix. |
| **Aromatic fraction** | (F + W + Y) / length. |
| **Net charge (pH 7)** | Approximate charge including termini. |
| **One-hot** | At each position, a 21-long switch (20 AA + X). |
| **Logit** | Raw model score before sigmoid. |
| **Sigmoid** | Squashes a logit to (0, 1). |
| **Random Forest** | Many decision trees voting on the 425 features. **Primary model.** |
| **ESM-2** | Protein language model. We use it **frozen** (weights not updated). |
| **Mean-pool** | Average residue vectors, skip special tokens. |
| **Frozen** | Encoder weights fixed; only a small head is trained. |
| **LoRA** | Cheap fine-tune. **Not run** (150M val too far from RF). |
| **1D-CNN** | Small convolutional net on the one-hot grid. Secondary score + heatmaps. |
| **ROC-AUC** | Ranking quality. Headline **0.9515**. Not “percent correct.” |
| **PR-AUC** | Ranking with AMP as the positive class. |
| **Accuracy** | Fraction correct at 0.5. Here ~0.87 on a 50/50 test. |
| **Macro-F1** | F1 averaged over both classes. |
| **ECE** | Expected Calibration Error, 15 bins. Are probabilities honest? |
| **Brier** | Mean squared error of P(AMP) vs 0/1. |
| **Platt scaling** | Logistic map on RF probabilities (two numbers a, b). |
| **Temperature scaling** | Divide logits by T. CNN and ESM-35M only. |
| **Integrated Gradients** | Attribution: how each input pulls the CNN AMP logit. |
| **Occlusion** | Hide one residue, see how the logit moves. |
| **GO / Pfam** | Gene Ontology functions; protein domain families. **Not this project.** |
| **MIC / hemolysis** | Lab potency / red-blood-cell toxicity. **Not predicted.** |
| **CC BY 4.0** | Cite the source; reuse allowed. |
| **MIT** | License for **our code** only. |

---

## Repository layout

```text
README.md                     this article
LICENSE                       MIT for code only
frontend/                     Next.js 14 demo (port 3000)
services/predict_api/         FastAPI locked inference (port 8000)
app/streamlit_app.py          Streamlit fallback (Predict + Metrics)
app/README.md                 streamlit command
scripts/                      dataset, training, CLI (`ampscan`)
data/LICENSE_NOTES.md         DRAMP / AMPlify licenses and counts
data/data_manifest.json       checksums / source stamp
data/splits/*_ids.txt         homology + random ID lists (in git)
reports/STUDY_GUIDE.md        condensed version of this material
reports/defense/*.pdf         typeset study guide
reports/LIMITATIONS.md
reports/mixed_clusters.md
reports/family_label_audit.md
reports/phase_*_report.md     locked phase write-ups
```

**On the training laptop only (gitignored):** `models/`, `data/raw/`, processed FASTAs, embeddings, feature matrices, CNN tensors, `archive/` (leftover enzyme/BLAST notes, not the AMP task).

Do **not** expect FASTAs or `.joblib` / `.pt` weights in a GitHub clone. Reconstruct sequences from DRAMP + Zenodo; weights live on the machine that trained the models.

---

## References

These are the **upstream papers and resources we actually used** (data, clustering, encoder, calibration). There is no AMPscan journal article.

1. **Ma T, et al.** DRAMP 4.0: an open-access data repository dedicated to the clinical translation of antimicrobial peptides. *Nucleic Acids Research* 53(D1):D403–D410 (2025). [doi:10.1093/nar/gkae1046](https://doi.org/10.1093/nar/gkae1046) — **AMP sequences (DRAMP General).**

2. **Shi G, et al.** DRAMP 3.0: an enhanced comprehensive data repository of antimicrobial peptides. *Nucleic Acids Research* 50(D1):D488–D496 (2022). [doi:10.1093/nar/gkab651](https://doi.org/10.1093/nar/gkab651)

3. **Li C, Sutherland D, Hammond SA, et al.** AMPlify: attentive deep learning model for discovery of novel antimicrobial peptides effective against WHO priority pathogens. *BMC Genomics* 23:77 (2022). [doi:10.1186/s12864-022-08310-4](https://doi.org/10.1186/s12864-022-08310-4) — **method and negative-class construction.**

4. **Li C, Warren RL, Birol I.** Models and data of AMPlify: a deep learning tool for antimicrobial peptide prediction. *BMC Research Notes* 16:11 (2023). [doi:10.1186/s13104-023-06279-1](https://doi.org/10.1186/s13104-023-06279-1) · data: [10.5281/zenodo.7320306](https://doi.org/10.5281/zenodo.7320306) — **non-AMP FASTAs.**

5. **Lin Z, Akin H, Rao R, et al.** Evolutionary-scale prediction of atomic-level protein structure with a language model. *Science* 379:1123–1130 (2023). [doi:10.1126/science.ade2574](https://doi.org/10.1126/science.ade2574) — **ESM-2** (`esm2_t12_35M_UR50D`, `esm2_t30_150M_UR50D`).

6. **Steinegger M, Söding J.** MMseqs2 enables sensitive protein sequence searching for the analysis of massive data sets. *Nature Biotechnology* 35:1026–1028 (2017). [doi:10.1038/nbt.3988](https://doi.org/10.1038/nbt.3988) — **homology clustering / split.**

7. **Guo C, Pleiss G, Sun Y, Weinberger KQ.** On calibration of modern neural networks. *ICML* (2017). [doi:10.48550/arXiv.1706.04599](https://doi.org/10.48550/arXiv.1706.04599) — **temperature scaling** (CNN / ESM heads).

8. **Kyte J, Doolittle RF.** A simple method for displaying the hydropathic character of a protein. *Journal of Molecular Biology* 157:105–132 (1982). [doi:10.1016/0022-2836(82)90515-0](https://doi.org/10.1016/0022-2836(82)90515-0) — **GRAVY / hydropathy scale** used in the RF features.

9. **Sundararajan M, Taly A, Yan Q.** Axiomatic attribution for deep networks. *ICML* (2017). [doi:10.48550/arXiv.1703.01365](https://doi.org/10.48550/arXiv.1703.01365) — **Integrated Gradients.**

Data licenses (CC BY 4.0 for DRAMP and AMPlify): [`data/LICENSE_NOTES.md`](data/LICENSE_NOTES.md). Code in this repo is MIT (`LICENSE`).

If a figure in a phase report disagrees with a number in this README, the locked files under `reports/phase_*_report.md` and `reports/calibration/SUMMARY.md` win — but they were checked against the tables above when this article was written.
