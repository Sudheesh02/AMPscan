# Phase 6 report — residue-level explainability (1D-CNN)

**Status:** complete  
**Date:** 2026-08-20  
**Scope:** Captum Integrated Gradients + occlusion on the locked homology 1D-CNN.
No new training, no Streamlit, no DeepLoc/GO/Pfam.

## Setup

| Item | Value |
| --- | --- |
| Weights | `models/cnn1d/homology_cnn1d.pt` (read-only) |
| Encoding | 21-channel one-hot, same as Phase 4 |
| IG target | AMP logit |
| Baseline | all-zero one-hot |
| Test compact table | top 5 residues by \|IG\| per sequence |

## Canonical AMP membership

All three peptides are **exact matches in homology train**:

- magainin-2 → `['POS_DRAMP_DRAMP02271']`
- LL-37 → `['POS_DRAMP_DRAMP03571']`
- melittin → `['POS_DRAMP_DRAMP03002']`

None are in val/test. No sequences were added to any split.

## Motif sanity (not a mechanism claim)

- High |IG| sites on these three peptides are often K/R (cationic) or F/L/I/W (hydrophobic/aromatic),
- which matches the textbook cationic-amphipathic sketch of magainin-2, LL-37, and melittin.
- magainin-2 top |IG|: K10(+0.771), K11(+0.770), H7(+0.637), F12(+0.565), A9(+0.408).
- LL-37 top |IG|: K8(+1.007), K10(+0.450), D4(-0.415), F6(+0.254), K12(+0.152).
- melittin top |IG|: W19(+1.028), K21(+0.908), I20(+0.679), K23(+0.561), R22(+0.348). Occlusion Δlogit tracks IG (Pearson {'magainin-2': 0.887, 'LL-37': 0.354, 'melittin': 0.908}).
- This is a model-dependent correlation, not a causal mechanism or wet-lab active-site map.

Pearson IG vs occlusion Δlogit: {'magainin-2': 0.887, 'LL-37': 0.354, 'melittin': 0.908}.

## Files

- `reports/explain/`
- `reports/phase_6_report.md`
