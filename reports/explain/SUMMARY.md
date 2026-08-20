# Phase 6 — Integrated Gradients on the 1D-CNN

Built: 2026-08-20T02:52:03Z

Locked Phase 4 weights were **loaded only**. No retraining. No Streamlit.

## Method

- Model: `models/cnn1d/homology_cnn1d.pt`
- Input: 21-channel one-hot (20 AA + X), pad = zeros, max length 100
- Target: AMP-class **logit**
- IG: Captum `IntegratedGradients`, zero baseline, 50 steps (canonical) / 32 (test)
- Per-residue score: sum of IG over the 21 channels at that position
- Occlusion (3 peptides): set that residue's one-hot column to 0; Δ = logit_full − logit_occluded

## Were the 3 peptides in homology train? (exact sequence)

| peptide | sequence | in train | train id | in val | in test |
| --- | --- | --- | --- | --- | --- |
| magainin-2 | GIGKFLHSAKKFGKAFVGEIMNS | **True** | ['POS_DRAMP_DRAMP02271'] | False | False |
| LL-37 | LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES | **True** | ['POS_DRAMP_DRAMP03571'] | False | False |
| melittin | GIGAVLKVLTTGLPALISWIKRKRQQ | **True** | ['POS_DRAMP_DRAMP03002'] | False | False |

All three exact sequences are **already in the homology training set** (DRAMP IDs above).
IG here is therefore an explanation of a **seen** AMP, not a held-out discovery.

## Motif sanity note (qualitative, not causal)

High |IG| sites on these three peptides are often K/R (cationic) or F/L/I/W (hydrophobic/aromatic),
which matches the textbook cationic-amphipathic sketch of magainin-2, LL-37, and melittin.
magainin-2 top |IG|: K10(+0.771), K11(+0.770), H7(+0.637), F12(+0.565), A9(+0.408).
LL-37 top |IG|: K8(+1.007), K10(+0.450), D4(-0.415), F6(+0.254), K12(+0.152).
melittin top |IG|: W19(+1.028), K21(+0.908), I20(+0.679), K23(+0.561), R22(+0.348). Occlusion Δlogit tracks IG (Pearson {'magainin-2': 0.887, 'LL-37': 0.354, 'melittin': 0.908}).
This is a model-dependent correlation, not a causal mechanism or wet-lab active-site map.

## Files

- `reports/explain/homology_test_top5.tsv` — top-5 |IG| residues per homology-test sequence
- `reports/explain/canonical_ig_occlusion.tsv` — full per-residue IG + occlusion for the 3 peptides
- `reports/explain/heatmap_magainin_2.png`, `heatmap_LL_37.png`, `heatmap_melittin.png`
- `reports/phase_6_report.md`
