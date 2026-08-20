# GitHub snapshot report

**Public name:** **AMPscan** (not AMPGuard).

**Status:** local commits on `main`. Push requires a GitHub repo named `AMPscan` under `Sudheesh02`. A fine-grained PAT that cannot create repositories will 403 until you create the empty repo in the browser and grant **Contents: Read and write**.

Intended remote: `https://github.com/Sudheesh02/AMPscan.git`

Nothing was deleted on disk.

## Files that WILL be pushed

Code, licenses, reports, split **IDs** / stats — not FASTAs or weights:

- `.gitignore`, `LICENSE` (MIT for **code**), `README.md` (title AMPscan)
- `app/`, `scripts/`
- `data/LICENSE_NOTES.md`, `data/data_manifest.json`
- `data/processed/*.json`, `labels.tsv`, `cross_class_conflicts.tsv`
- `data/splits/*_ids.txt`, `split_stats.json`, `cluster_assignments.tsv`, `mmseqs/cluster_cluster.tsv`
- `reports/` including study guide PDF

## Files that stay local via `.gitignore`

- `models/`, `data/raw/`, embeddings, features, FASTAs, `*.pt` / `*.joblib` / `*.npz`, `archive/`, `.cache/`

## Confirmation

`reports/`, `models/`, and `data/raw/` remain on the laptop. Phase 1–9 reports were not rewritten except this GitHub note.

## Push commands (after empty public `AMPscan` exists)

```bash
cd "/home/sudheesh02/SIH TEST"
git remote set-url origin https://github.com/Sudheesh02/AMPscan.git
git push -u origin main
```
