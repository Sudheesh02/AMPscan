# GitHub snapshot report

**Final public name:** **AMPscan: Binary Antimicrobial Peptide Classifier** (short: **AMPscan**).

**Local git:** `main` at `4f4180d` (plus earlier snapshot commits).  
**Remote configured:** `https://github.com/Sudheesh02/AMPscan.git`  
**Repo on GitHub:** exists (public, https://github.com/Sudheesh02/AMPscan) — currently empty / not yet containing our commits.  
**Push result:** **not uploaded.** `git push` failed: `could not read Username for 'https://github.com': terminal prompts disabled`. No token was embedded in remotes, files, or this report.

Nothing under `models/` or `data/raw/` was deleted. Phase science reports were not rewritten (one title-string fix in `phase_11_report.md` only).

## Tracked (eligible for git / will push)

- `README.md`, `LICENSE` (MIT for **code** only)
- `app/`, `scripts/`
- `reports/**/*.md` plus report plots/PDF already in the snapshot
- `data/LICENSE_NOTES.md`, `data/data_manifest.json`
- `data/splits/*_ids.txt`, `split_stats.json`, `cluster_assignments.tsv`, `mmseqs/cluster_cluster.tsv` (IDs)
- `data/processed/*.json`, `labels.tsv`, `cross_class_conflicts.tsv`
- `.gitignore`

## Gitignored (stay on this laptop)

- `models/`
- `data/raw/`
- `data/processed/embeddings/`, `features/`, `cnn1d/`, `calibration/`
- `data/splits/*.fasta`, `data/splits/mmseqs/*.fasta`
- `archive/`, `research/`
- `*.pt`, `*.joblib`, `*.npz`, `*.ckpt`, `*.pyc`, `__pycache__/`
- `.env`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, `*.Zone.Identifier`

## Next (you run this; do not paste a PAT in chat)

Repo already exists. Authenticate locally, then push:

```bash
cd "/home/sudheesh02/SIH TEST"
gh auth login
git push -u origin main
```

Or SSH:

```bash
cd "/home/sudheesh02/SIH TEST"
git remote set-url origin git@github.com:Sudheesh02/AMPscan.git
git push -u origin main
```

Or GitHub CLI create-if-needed (only if the empty repo were missing):

```bash
gh repo create AMPscan --public --source=. --remote=origin --push
```
