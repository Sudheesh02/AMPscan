# AMPscan vs other AMP tools — architecture, not marketing

**For judges and teammates.** Locked v1 headline: homology-test RF ROC-AUC **0.9515**, Platt ECE **0.023**. Random-split **0.9791** is leakage. Cohort 2b RF **0.903** is an external check on length-matched DBAASP vs **fragment** non-AMPs, not a replacement metric.

We did **not** lose because we skipped BiLSTM, graphs, or ESM. On peptides 5–100 aa, composition already carries most of the AMP vs non-AMP signal. Other tools optimized *different jobs*. Steal the job, not the logo.

---

## Same test, different objectives

Locked DRAMP vs AMPlify-negatives, MMseqs 30% / 80% shorter coverage, n = 3230 (Macrel/AMPlify skip 48 X).

| Tool | What it was built to do | How it represents a peptide | Cohort 1 ROC | ECE | What we keep / ignore |
| --- | --- | --- | ---: | ---: | --- |
| **AMPscan RF** | Honest peptide AMP vs non-AMP + calibrated P | 425-D AAC+DPC+charge/GRAVY/μH/aromatic | **0.9515** | **0.023** | **v1 backbone** |
| AMPscan CNN | Same labels; residue IG | 21×100 one-hot | 0.942 | 0.040 | Explainer, not primary |
| ESM-2 150M frozen linear | Same labels | 640-D mean pool | 0.9521 | not in 15-bin file | Tie; no LoRA (val missed gate) |
| **Macrel** | Metagenome smORF mining + speed | 22-D groups/physchem/CTDD, ONNX, 101 trees | 0.949 | 0.204 | Speed + optional **foreign** Hemo head |
| **AMPlify** | Attentive AMP call, paper wet-lab | 5× BiLSTM+attention, pad 200 | 0.928 | 0.118 | Attention as extra map, not hybrid 512-D |
| **AI4AMP** | PC6 physics tensor | 200×6 z-scored properties | 0.791 | 0.154 | v2 CNN ablation only |
| **AmpGram** | Scan long proteins with 10-mers | n-gram ranger (R) | 0.790 | 0.164 | Window **our** RF, don’t port R |
| peptidy | Feature calculator | TPSA, instability, … | — | — | Dead on a **frozen** 425-D RF |
| hemopi2 / HemoPred | Hemolysis | RF / ESM / motifs | — | — | Other **task** |
| zswitten | MIC (μM) | CNN, length ≤50 | — | — | Other **label** |
| sAMPpred-GAT | Structure graph | BLAST + trRosetta | — | — | >100 GB; skip |

Cohort 2b (11,190 + 11,190, length median 14 vs 14): RF **0.903**, Macrel **0.900**, AMPlify **0.899**. Ranking **tied**. RF acc@0.5 **0.645** (ECE 0.28): Platt does not travel. Quote ROC, not accuracy.

---

## They optimized X. We optimized Y.

**Macrel — throughput and a second head.** 22 numbers, ONNX, ~6600 seq/s, separate Hemo model. On our test it is **conservative** (FP 22, FN 661), not “high FPR.” We win calibration and DPC detail; they win speed and a hemolysis checkpoint trained on HemoPI, not our labels.

**AMPlify — residue grammar.** Attention is a real extra explainer. Their published ~0.98 is not our 30% split (**0.928**). For 5–100 aa, a forest on AAC/DPC beat the BiLSTM. ESM-150M tied the RF (+0.0006) and failed the LoRA val gate.

**AI4AMP — continuous physics per residue.** Sensible encoding. **0.791** here is domain shift (their corpus ≠ DRAMP/AMPlify), not proof they overfit *our* clusters.

**AmpGram — proteins, not peptides.** 10-mer scan of long chains. We already have `scripts/scan_protein.py` using the **locked** RF. Window scores ≠ “this protein is AMP.” LL-37 lighting up on hCAP-18 is **train-set recall**, not a new domain.

**peptidy — a calculator.** Extra columns do nothing until you **retrain**. Then it is v2 with a new number.

---

## What we already took (v1.1)

- Batch `featurize_many` + one `predict_proba`: **~150×** vs the Python one-seq loop on Cohort 1 (CPU, not GPU). Same P(AMP) (RF Δ = 0).
- Sliding-window scanner, labeled not protein-level AMP.
- Classify copy: 0.5 was fit on DRAMP/AMPlify; short OOD can over-call.

---

## What we refuse

TSI = P(AMP)/(P(Hemo)+ε). Pathogen radar from DBAASP tag strings. Unused extra features on the frozen RF. Retrain on DBAASP and keep 0.9515. Quoting Cohort 2 **0.993** (length confound: 14 aa vs 76 aa). Calling Macrel-Hemo “AMPscan safety.”

---

## Judge one-liners

- **Why not AMPlify’s net?** Same test, RF 0.951 vs 0.928; peptides this short are composition-heavy.
- **Why not Macrel as primary?** ROC tied; **ECE 0.20 vs 0.023**. Their 0.5 cut misses AMPs (FN 661).
- **Why 0.95 not 0.98?** Homology split. Random split is the leaky control.
- **External?** Length-matched DBAASP vs fragments: **0.903**. Fragments are not assayed inactives.
