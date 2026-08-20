# Mixed homology clusters (AMP and non-AMP in the same MMseqs2 cluster)

These **72** clusters were produced by `mmseqs easy-cluster --min-seq-id 0.3 -c 0.8 --cov-mode 1` on the combined cleaned set.
A cluster is **mixed** when it contains at least one AMP (DRAMP) and one non-AMP (AMPlify).
Whole clusters were assigned to one fold, so mixed clusters never leak a homolog across train/val/test — but they do mean the 30% threshold does not fully separate the two labels.

## Summary

| | |
| --- | ---: |
| mixed clusters | 72 |
| in train / val / test | 47 / 15 / 10 |
| AMP members in mixed clusters | 264 |
| non-AMP members in mixed clusters | 445 |
| cluster size min / median / max | 2 / 5 / 73 |
| AMP lengths in mixed clusters | min 11, mean 46.6, max 99 |
| non-AMP lengths in mixed clusters | min 11, mean 62.9, max 100 |
| AMP source | DRAMP |
| non-AMP source | AMPlify |

Non-AMPs in mixed clusters tend to be **longer** than the AMPs they cluster with (mean 63 vs 47). That is consistent with MMseqs coverage mode 1 (shorter sequence ≥80% covered): a short AMP can sit inside a longer UniProt-derived peptide at ≥30% identity.

## All 72 clusters

| rep | fold | n | n_pos | n_neg | AMP len min–max (mean) | non-AMP len min–max (mean) | AMP src | non-AMP src |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `NEG_AMPLIFY_teNEGATIVE0767` | train | 73 | 3 | 70 | 20–60 (33.3) | 15–93 (71.3) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP04072` | test | 48 | 47 | 1 | 13–51 (35.3) | 13–13 (13.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP00358` | train | 48 | 43 | 5 | 30–99 (88.5) | 20–91 (66.6) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE12753` | test | 36 | 1 | 35 | 60–60 (60.0) | 15–100 (71.9) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE20005` | train | 31 | 23 | 8 | 15–27 (16.9) | 60–95 (70.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE04231` | train | 25 | 2 | 23 | 18–18 (18.0) | 92–97 (96.7) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE10421` | train | 25 | 16 | 9 | 36–38 (37.0) | 35–74 (58.4) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE06154` | val | 24 | 1 | 23 | 33–33 (33.0) | 32–87 (77.8) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE03577` | train | 23 | 3 | 20 | 38–39 (38.7) | 49–99 (85.3) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE06640` | train | 21 | 2 | 19 | 37–37 (37.0) | 23–68 (44.1) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE11231` | train | 18 | 5 | 13 | 23–36 (33.4) | 36–99 (59.8) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE15387` | train | 16 | 2 | 14 | 33–34 (33.5) | 32–79 (37.8) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE16153` | train | 15 | 5 | 10 | 60–74 (68.0) | 90–99 (95.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE22580` | train | 15 | 1 | 14 | 63–63 (63.0) | 20–97 (58.9) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE11664` | test | 13 | 1 | 12 | 50–50 (50.0) | 23–61 (32.3) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE19979` | train | 13 | 1 | 12 | 55–55 (55.0) | 30–92 (80.2) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP31960` | val | 13 | 11 | 2 | 32–34 (33.7) | 30–30 (30.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE18184` | test | 11 | 1 | 10 | 37–37 (37.0) | 32–92 (51.4) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE0974` | train | 11 | 1 | 10 | 32–32 (32.0) | 27–34 (32.2) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE16091` | train | 11 | 1 | 10 | 29–29 (29.0) | 26–81 (39.6) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE04454` | val | 10 | 9 | 1 | 40–45 (42.1) | 49–49 (49.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE08888` | val | 10 | 8 | 2 | 63–67 (65.8) | 87–89 (88.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE09623` | train | 9 | 1 | 8 | 74–74 (74.0) | 77–84 (78.5) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP32144` | train | 8 | 2 | 6 | 28–38 (33.0) | 25–28 (27.3) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE25561` | train | 7 | 5 | 2 | 16–56 (42.6) | 86–87 (86.5) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE2974` | train | 7 | 1 | 6 | 31–31 (31.0) | 30–33 (31.5) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP03699` | train | 7 | 3 | 4 | 64–66 (65.3) | 20–29 (26.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE09071` | val | 7 | 2 | 5 | 22–25 (23.5) | 28–91 (74.2) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE21572` | val | 7 | 1 | 6 | 71–71 (71.0) | 30–83 (60.7) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE20405` | train | 6 | 1 | 5 | 28–28 (28.0) | 64–74 (68.4) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP03489` | train | 6 | 1 | 5 | 43–43 (43.0) | 23–33 (30.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE20526` | val | 6 | 1 | 5 | 98–98 (98.0) | 38–99 (86.4) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP03633` | val | 6 | 4 | 2 | 88–93 (89.5) | 79–79 (79.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE11370` | test | 5 | 2 | 3 | 76–77 (76.5) | 100–100 (100.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE1919` | test | 5 | 1 | 4 | 63–63 (63.0) | 20–68 (46.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE3217` | test | 5 | 4 | 1 | 14–14 (14.0) | 14–14 (14.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE12991` | train | 5 | 2 | 3 | 58–59 (58.5) | 47–89 (73.7) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE24866` | train | 5 | 4 | 1 | 15–36 (21.8) | 77–77 (77.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP04701` | train | 5 | 1 | 4 | 33–33 (33.0) | 23–28 (24.2) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE08419` | val | 5 | 1 | 4 | 21–21 (21.0) | 24–78 (60.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE0652` | test | 4 | 1 | 3 | 15–15 (15.0) | 16–16 (16.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE12531` | test | 4 | 2 | 2 | 40–41 (40.5) | 41–60 (50.5) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE08951` | train | 4 | 1 | 3 | 32–32 (32.0) | 60–73 (66.7) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE10718` | train | 4 | 2 | 2 | 40–42 (41.0) | 40–58 (49.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE14616` | train | 4 | 1 | 3 | 34–34 (34.0) | 90–100 (96.7) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP00280` | train | 4 | 1 | 3 | 86–86 (86.0) | 68–71 (69.7) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE2096` | val | 4 | 2 | 2 | 18–46 (32.0) | 46–46 (46.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE0460` | train | 3 | 1 | 2 | 25–25 (25.0) | 26–26 (26.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE06163` | train | 3 | 1 | 2 | 65–65 (65.0) | 56–77 (66.5) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE0967` | train | 3 | 1 | 2 | 25–25 (25.0) | 25–25 (25.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE26499` | train | 3 | 2 | 1 | 51–51 (51.0) | 74–74 (74.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP00345` | train | 3 | 2 | 1 | 67–67 (67.0) | 28–28 (28.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP20835` | train | 3 | 1 | 2 | 30–30 (30.0) | 20–22 (21.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_teNEGATIVE0713` | val | 3 | 2 | 1 | 19–20 (19.5) | 29–29 (29.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE18081` | val | 3 | 2 | 1 | 33–34 (33.5) | 94–94 (94.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE18209` | val | 3 | 1 | 2 | 41–41 (41.0) | 41–43 (42.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE2902` | val | 3 | 2 | 1 | 48–48 (48.0) | 54–54 (54.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP02469` | test | 2 | 1 | 1 | 62–62 (62.0) | 25–25 (25.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE0331` | train | 2 | 1 | 1 | 22–22 (22.0) | 40–40 (40.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE04379` | train | 2 | 1 | 1 | 26–26 (26.0) | 64–64 (64.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE05776` | train | 2 | 1 | 1 | 26–26 (26.0) | 82–82 (82.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE10436` | train | 2 | 1 | 1 | 47–47 (47.0) | 55–55 (55.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE1334` | train | 2 | 1 | 1 | 22–22 (22.0) | 41–41 (41.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE1370` | train | 2 | 1 | 1 | 11–11 (11.0) | 11–11 (11.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE19929` | train | 2 | 1 | 1 | 28–28 (28.0) | 76–76 (76.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE20445` | train | 2 | 1 | 1 | 59–59 (59.0) | 60–60 (60.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP00295` | train | 2 | 1 | 1 | 25–25 (25.0) | 17–17 (17.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP00303` | train | 2 | 1 | 1 | 35–35 (35.0) | 25–25 (25.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP18097` | train | 2 | 1 | 1 | 80–80 (80.0) | 57–57 (57.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP18111` | train | 2 | 1 | 1 | 46–46 (46.0) | 44–44 (44.0) | DRAMP | AMPLIFY |
| `POS_DRAMP_DRAMP18659` | train | 2 | 1 | 1 | 32–32 (32.0) | 23–23 (23.0) | DRAMP | AMPLIFY |
| `NEG_AMPLIFY_trNEGATIVE05004` | val | 2 | 1 | 1 | 29–29 (29.0) | 44–44 (44.0) | DRAMP | AMPLIFY |

IDs and sequences: `data/splits/cluster_assignments.tsv`, `data/splits/mmseqs/cluster_cluster.tsv`, `data/processed/labels.tsv`.
