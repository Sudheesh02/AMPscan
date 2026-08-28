# Cohort 2 — DBAASP external OOD (not the locked 0.9515)

DBAASP peptides with **MMseqs2 <30% identity / 80% shorter-seq coverage** to AMPscan **train**, plus length-aware non-AMPs from the AMPlify UniProt-style pool (also <30% to train and to these DBAASP peptides). **Frozen models. No retraining.**

- Novel DBAASP positives: **11190** (of which 1353 had D-aa, case-folded).
- Homologs dropped vs train: **2997**.
- Exact overlaps with AMPscan train/val/test dropped: **5045**.
- Matched non-AMPs: **6962** (could not 1:1 match; pool ran out after the homology walls).
- Total n = **18152** (imbalanced ~1.61:1). Quote ROC-AUC and PR-AUC, not accuracy as if it were 50/50.

**Do not quote 0.993 as beating locked 0.9515.** The full table is **length-confounded**. After the homology walls, leftover AMPlify-pool negatives are long UniProt-like peptides; DBAASP novels are short synthetics:

| class | n | length median (IQR) |
| --- | ---: | --- |
| DBAASP novel AMP | 11,190 | **14** (10–19) |
| Matched non-AMP | 6,962 | **76** (61–90) |

A 14-aa cation vs a 76-aa UniProt fragment is an easy composition/length problem. Only **302** negatives have length ≤30 vs **10,520** positives. Length-matching in the builder could not fill short bins.

**Length-restricted check (same frozen RF scores):**

| slice | n (pos/neg) | RF ROC-AUC | RF acc@0.5 |
| --- | --- | ---: | ---: |
| Full Cohort 2 | 11190 / 6962 | 0.9935 | 0.9608 |
| Both length ≤40 | 10968 / 604 | 0.9649 | 0.9561 |
| Balanced length ≤40 (seed 42) | 604 / 604 | **0.9555** | 0.8113 |
| Balanced length ≤30 (seed 42) | 302 / 302 | **0.9420** | 0.7086 |

On a short, balanced slice the RF is ~**0.94–0.96**, in the same band as Cohort 1, not 0.99. Accuracy at 0.5 falls because we barely have short non-AMPs. Treat the full 0.993 table as “can we tell DBAASP-like shorts from long UniProt leftovers,” not as a harder OOD ROC.

| model | n | skip | acc | MCC | ROC-AUC | PR-AUC | ECE-15 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AMPscan RF (Platt) | 18152 | 0 | 0.9608 | 0.9173 | **0.9935** | 0.9960 | 0.0249 |
| AMPscan 1D-CNN (T) | 18152 | 0 | 0.9461 | 0.8857 | **0.9857** | 0.9916 | 0.0183 |
| Macrel | 16198 | 1954 | 0.8063 | 0.6733 | **0.9902** | 0.9917 | 0.2308 |
| AI4AMP PC6 | 18152 | 0 | 0.7388 | 0.4822 | **0.8254** | 0.8904 | 0.1518 |
| AMPlify balanced | 16198 | 1954 | 0.8773 | 0.7631 | **0.9547** | 0.9670 | 0.0849 |

ROC: `02_cohort2_roc.png`.

AMPlify/Macrel skip sequences with X / non-20 AA (D-aa case-fold can still leave X).

Locked AMPscan v1 metric remains Cohort 1 **RF ROC-AUC 0.9515**.
