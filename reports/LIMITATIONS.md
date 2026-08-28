# Limitations (honest)

1. **This is a sequence-pattern classifier on a balanced peptide set**, not a measurement of antimicrobial function. A high P(AMP) means “looks like DRAMP-style AMPs vs AMPlify-style non-AMPs,” not “will kill bacteria.”

2. **The test is ~50/50 AMP vs non-AMP.** Real proteomes and metagenomes are extremely AMP-sparse. Accuracy 0.87 and ROC-AUC 0.95 will not translate to usable precision at realistic prevalence without a much higher threshold and a large recall cost.

3. **Negatives are “not annotated as AMP,” not experimentally inactive.** AMPlify non-AMPs come from UniProt-style filters. Some labeled non-AMPs might be active if assayed; some AMPs are weak, condition-specific, or synthetic.

4. **DRAMP General mixes natural and synthetic AMPs.** Composition models (the winning RF) are helped by designed amphipathic cations. Performance on a purely natural, phylogenetically new set is untested.

5. **Homology control is 30% identity / 80% shorter-seq coverage, not a biological independence guarantee.** There are **72 mixed clusters** (AMP and non-AMP in the same cluster). Those folds stay unsplit, but the threshold does not fully separate the labels. See `reports/mixed_clusters.md`.

6. **Random-split metrics are inflated.** RF ROC-AUC 0.98 vs 0.95 on the cluster split. Do not quote the random-split number as generalization.

7. **ESM-2 35M frozen and the 1D-CNN did not beat the RF** on the homology test (0.945 and 0.942 vs 0.952 ROC-AUC). For 5–100 aa AMP vs other peptide, amino-acid composition, charge, and hydrophobicity already carry most of the signal. Bigger language models are not implied to help.

8. **Explainability is model-dependent, not mechanism.** Integrated Gradients on the CNN often highlights K/R and hydrophobic residues, which matches the cationic-amphipathic cartoon. Magainin-2, LL-37, and melittin are **in the homology training set**. IG is not a wet-lab active-site map.

9. **Platt calibration does not transfer automatically to external fragment backgrounds.** On the Cohort 2b length-matched DBAASP validation ($N=22,380$), the Platt scaling parameters fit on Cohort 1 over-call AMP at $P \ge 0.5$ (ECE 0.277, accuracy 0.645). In discovery pipelines, users should rely on threshold-invariant ROC ranking or apply operating point triage ($P \ge 0.90$).

10. **Naive external evaluations are easily length-confounded.** Evaluating short synthetic AMPs against unconstrained UniProt leftovers yields a deceptively inflated 0.9935 ROC. In fair length-matched benchmarks (Cohort 2b), AMPscan and competitors perform at ~0.90 ROC.

11. **Windowed proteome scanning is not a whole-protein structural call.** The `/scan` endpoint slides a 5–100 aa window to score local sequence motifs. It does not account for 3D protein folding, tertiary stability, or in vivo enzymatic cleavage sites.

12. **Scope is peptides of length 5–100 with a 20-letter (+X) alphabet.** Pfam domains, EC numbers, MIC regression, and in vivo animal efficacy are **out of scope**.

No LoRA, no GO/Pfam/DeepLoc heads, and no further training are part of this snapshot.

