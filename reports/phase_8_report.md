# Phase 8 report — docs, limitations, mixed clusters, archive

**Status:** complete  
**Scope:** documentation and cleanup only. No new models. No Pfam download. No training.

## Files written

| Path | Purpose |
| --- | --- |
| `README.md` | Project scope, Streamlit command, locked metrics, licenses, layout |
| `reports/LIMITATIONS.md` | 9-point honest list; no LoRA/family-head promises |
| `reports/mixed_clusters.md` | All 72 mixed MMseqs2 clusters: fold, sizes, lengths, sources |
| `reports/phase_8_report.md` | This note |

## Mixed clusters (from locked Phase-1 files)

72 clusters contain both AMP and non-AMP. 47 train / 15 val / 10 test. 264 AMP members, 445 non-AMP members. Size 2–73 (median 5). AMP lengths in mixed clusters mean 46.6 aa; non-AMP mean 62.9 aa. Sources: DRAMP vs AMPlify.

## Archive (moved, not deleted)

Leftover root files from earlier enzyme/BLAST experiments and notes went to `archive/`:

- `analyze_results.py`, `detailed_gap_analysis.py`, `fetch_enzymes.py`
- `blast_results.tsv`, `gap_analysis_summary.json`, `test_enzymes.fasta`, `time_output.txt`
- `claude_review_report.md`, `plan.md`
- `research/` (prior LLM notes, not this AMP pipeline)

Locked `data/`, `models/`, `app/`, `scripts/`, and earlier `reports/phase_*` files were not retrained or rewritten except for the new Phase-8 docs above.
