# GitHub snapshot report

**Status:** local commit done. **Remote push not completed** (fine-grained PAT can see user `Sudheesh02` but cannot create repositories: API 403 `Resource not accessible by personal access token`). Repo `Sudheesh02/AMPGuard` does not exist yet (GET 404).

Local commit: `7cb6475` on branch `main`  
Intended remote: `https://github.com/Sudheesh02/AMPGuard.git`  
Nothing was deleted on disk.

## Files that WILL be pushed (104 in the initial commit)

Code, licenses, reports, split **IDs** / stats — not FASTAs or weights. Includes:

- `.gitignore`, `LICENSE` (MIT for **code**), `README.md`
- `app/` (`streamlit_app.py`, `README.md`)
- `scripts/*.py`
- `data/LICENSE_NOTES.md`, `data/data_manifest.json`
- `data/processed/alphabet_filter_counts.json`, `preprocess_counts.json`, `labels.tsv`, `cross_class_conflicts.tsv`
- `data/splits/*_ids.txt`, `split_stats.json`, `random_split_stats.json`, `cluster_assignments.tsv`, `mmseqs/cluster_cluster.tsv` (IDs only)
- `reports/` (phase reports, STUDY_GUIDE, PDF, plots, LIMITATIONS, mixed_clusters, family audit)

## Files that stay local via `.gitignore` (still on the laptop)

- `models/` (all `.pt` / `.joblib` weights)
- `data/raw/` (DRAMP/AMPlify FASTA and xlsx)
- `data/processed/embeddings/`, `features/`, `cnn1d/`, `calibration/`
- all `*.fasta` / `*.fa` / `*.npz`
- `archive/`, `.cache/`
- `data/splits/*.fasta`, `data/splits/mmseqs/*.fasta`

## Confirmation

- `reports/` on disk was **not** deleted (phase 1–12 markdown, PDF, plots still present).
- `models/` and `data/raw/` on disk were **not** deleted.
- Phase reports were not rewritten for this snapshot except this new file.

## Remote URL

Push has **not** succeeded yet. After you create an empty **public** repo named `AMPGuard` under https://github.com/Sudheesh02 (no README), grant the PAT **Contents: Read and write** on that repo, then:

```bash
cd "/home/sudheesh02/SIH TEST"
git push -u origin main
```

Or:

```bash
gh repo create AMPGuard --public --source=. --remote=origin --push
```

## Next commands (human)

1. GitHub → New repository → name `AMPGuard` → Public → **do not** add README/license/gitignore.  
2. Edit the fine-grained PAT so it includes repo `Sudheesh02/AMPGuard` with Contents read/write.  
3. `git push -u origin main`

**Security:** the PAT was pasted in chat. **Revoke/rotate it** after the push.
