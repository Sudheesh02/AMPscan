# DRAMP family-label audit (no training)

Source: official DRAMP General spreadsheet
`https://dramp.cpu-bioinfor.org/downloads/` → `general_amps.xlsx`
saved as `data/raw/general_amps.xlsx` (11687 rows, 29 columns).
Join key: `DRAMP_ID` extracted from cleaned positive IDs (`POS_DRAMP_DRAMP#####`).
Family missing if the cell is empty, `Not found`, NA, or similar.

## Coverage on our cleaned positives

| | n |
| --- | ---: |
| cleaned AMP sequences (dedup, length 5–100) | 10678 |
| joined to a non-empty DRAMP `Family` | **4841** |
| missing family | **5837** (54.7%) |
| distinct Family strings among labeled | 377 |
| xlsx rows with a Family (raw file) | 5097 / 11687 |

All cleaned positives are DRAMP-sourced; join was by ID (no sequence fallback hits).

## What `Family` actually is

The column **mixes two different ontologies**:

1. **AMP peptide families** — e.g. Brevinin, DEFL, beta-defensin, cyclotide, dermaseptin.
2. **Virus taxonomy of the source** — Retroviridae, Flaviviridae, Herpesviridae, Coronaviridae, etc. Those are not AMP structural families; they are where the sequence came from (often viral proteins annotated as antimicrobial in DRAMP General).

A 5–10 class head that treats these strings as one label space would be scientifically incoherent.

## Family frequency (cleaned positives with a label)

Size buckets: 1 seq = 168 families; 2–9 = 146; 10–49 = 50; **≥50 = 13**.

| n | family | ≥50? |
| ---: | --- | --- |
| 613 | Retroviridae | yes |
| 465 | Flaviviridae | yes |
| 392 | Belongs to the frog skin active peptide family (Brevinin subfamily) | yes |
| 358 | Belongs to the DEFL family | yes |
| 263 | Herpesviridae | yes |
| 221 | Belongs to the beta-defensin family | yes |
| 148 | Belongs to the cyclotide family | yes |
| 128 | Coronaviridae | yes |
| 117 | Bunyaviridae | yes |
| 113 | Orthomyxoviridae | yes |
| 92 | Paramyxoviridae | yes |
| 75 | Belongs to the alpha-defensin family | yes |
| 71 | Belongs to the frog skin active peptide family (Dermaseptin subfamily) | yes |
| 49 | Belongs to the bombinin family |  |
| 47 | Belongs to the class IIa bacteriocin |  |
| 46 | Belongs to the class IIb bacteriocin |  |
| 46 | Filoviridae |  |
| 45 | Belongs to the cecropin family |  |
| 43 | Belongs to the plant LTP family |  |
| 43 | Belongs to the CRISPR-associated endoribonuclease Cas2 prote |  |
| 39 | Belongs to the cathelicidin family |  |
| 34 | Belongs to the thionin family |  |
| 32 | Belongs to the class IId bacteriocin |  |
| 28 | Belongs to the frog skin active peptide family (Caerin subfamily) |  |
| 27 | Belongs to the type A lantibiotic family (Class I bacteriocin) |  |
| 24 | Belongs to the lantibiotic family (Class I bacteriocin) |  |
| 24 | Belongs to the lantibiotics family (Class I bacteriocin) |  |
| 23 | Belongs to the snake waprin family |  |
| 23 | Belongs to the invertebrate defensin family (Type 1 subfamily) |  |
| 22 | Belongs to the frog skin active peptide (FSAP) family. Brevinin subfamily. |  |
| 21 | Poxviridae |  |
| 20 | Belongs to the frog skin active peptide family (Tryptophillin subfamily) |  |
| 20 | Belongs to the penaeidin family |  |
| 19 | Belongs to the vicilin-like family |  |
| 19 | Belongs to the class I bacteriocin |  |
| 18 | Belongs to the scorpion NDBP 5 family |  |
| 17 | Belongs to the crotamine-myotoxin family |  |
| 17 | Derived from the peptide CP26, CP29, CEME and CEMA |  |
| 16 | Belongs to the class IIc bacteriocin |  |
| 16 | Belongs to the pleurocidin family |  |
| 16 | Belongs to the beta/delta-agatoxin family |  |
| 16 | Derived from TP4 |  |
| 15 | Belongs to the flavin monoamine oxidase family (FIG1 subfamily) |  |
| 15 | Belongs to the cytoinsectotoxin family |  |
| 15 | Belongs to the lipopeptides family |  |
| 15 | Belongs to the betacoronaviruses spike protein family. |  |
| 14 | Arteriviridae |  |
| 13 | Belongs to the class II bacteriocin |  |
| 13 | Papillomaviridae |  |
| 13 | Flaviviridae, Retroviridae |  |
| 12 | Belongs to the hevein-like family |  |
| 11 | Belongs to the alpha-defensin family (Theta subfamily) |  |
| 11 | Belongs to the transferrin family |  |
| 11 | Spider wap-1 family
 (Contains 1 WAP domain) |  |
| 11 | Belongs to the non-disulfide-bridged peptide (NDBP) superfamily. Short ant |  |
| 11 | Herpesviridae, Picornaviridae |  |
| 10 | Belongs to the BetVI family |  |
| 10 | Belongs to the glycosyl hydrolase 22 family |  |
| 10 | Belongs to the latarcin family |  |
| 10 | Belongs to the beta-defensin family. |  |
| 10 | Derived from the framework peptide V681 |  |
| 10 | Belongs to the frog skin active peptide (FSAP) family. Pleurain subfamily. |  |
| 10 | Picornaviridae |  |
| 725 | *(314 families with n < 10, not listed)* | |

## Families with ≥50 sequences, vs locked homology folds

Counts are sequences in our cleaned set. `n_clusters` = distinct MMseqs2 clusters (30% / cov 0.8).

| family | n | train | val | test | clusters (tr/va/te) | note |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Retroviridae | 613 | 374 | 155 | 84 | 317 (219/42/56) | virus taxon, not AMP family |
| Flaviviridae | 465 | 315 | 50 | 100 | 282 (200/33/49) | virus taxon, not AMP family |
| Belongs to the frog skin active peptide family (Brevinin subfamily) | 392 | 210 | 113 | 69 | 115 (68/22/25) | real AMP family |
| Belongs to the DEFL family | 358 | 274 | 35 | 49 | 145 (106/18/21) | real AMP family (plant defensins) |
| Herpesviridae | 263 | 177 | 43 | 43 | 213 (140/37/36) | virus taxon, not AMP family |
| Belongs to the beta-defensin family | 221 | 170 | 17 | 34 | 54 (44/3/7) | real AMP family |
| Belongs to the cyclotide family | 148 | 68 | 79 | 1 | 12 (6/5/1) | real AMP family; almost no test seqs (1) |
| Coronaviridae | 128 | 87 | 20 | 21 | 75 (46/11/18) | virus taxon, not AMP family |
| Bunyaviridae | 117 | 83 | 13 | 21 | 117 (83/13/21) | virus taxon; 117 seqs / 117 clusters (not a sequence family) |
| Orthomyxoviridae | 113 | 65 | 9 | 39 | 73 (49/9/15) | virus taxon, not AMP family |
| Paramyxoviridae | 92 | 79 | 5 | 8 | 27 (17/4/6) | virus taxon; tiny val/test |
| Belongs to the alpha-defensin family | 75 | 38 | 27 | 10 | 19 (12/4/3) | real AMP family |
| Belongs to the frog skin active peptide family (Dermaseptin subfamily) | 71 | 58 | 2 | 11 | 15 (10/1/4) | real AMP family; val n=2 |

255 / 377 labeled families sit in **only one** homology fold (train or val or test). A class head would have no evaluation for those names.

## Recommendation: **NO-GO** for a 5–10 class family head

Do **not** train a 5–10 class family model on this snapshot.

Reasons:

1. **Missingness.** 5837 / 10678 cleaned AMPs (55%) have no family. Any head would be trained on a biased labeled subset.
2. **Label meaning is mixed.** The largest classes are viral taxa (Retroviridae 613, Flaviviridae 465), not AMP families. A classifier would mostly learn “virus-derived peptide vs frog skin peptide,” which is not AMP family classification.
3. **Too few *real* AMP families at ≥50.** After dropping virus strings: Brevinin (392), DEFL (358), beta-defensin (221), cyclotide (148), alpha-defensin (75), Dermaseptin (71). That is **6** usable names, not a clean 5–10, and two of them fail the split (cyclotide test n=1; Dermaseptin val n=2).
4. **Homology split fights family as a label.** Cyclotides collapse to 12 clusters; 79 of 148 sit in val and 1 in test. A family head would either leak homologs (if you ignore the cluster split) or have empty/unstable test classes (if you keep it).
5. **Hackathon scope.** Phase 1–7 already froze binary AMP vs non-AMP. A family head is a different dataset, different metric, and a week of label cleaning — not a 5-class softmax on this column.

If this were revisited later (not now): keep only AMP-family strings, drop virus taxa, require n≥50 **and** ≥10 sequences in **each** of train/val/test after the locked cluster split. That would likely leave **3–4 classes** (Brevinin, DEFL, beta-defensin, maybe alpha-defensin). That is a small specialized paper, not a 5–10 class head on this dump.

