# Data directories

All paths are **under the repository root**. Nothing here is a separate database—just files the pipeline and benchmarks write.

| Directory | Role |
|-----------|------|
| **`raw/`** | Cached SEC JSON (company facts, submissions, ticker map). Populated on **live** fetches. Safe to delete to force re-download (slower next run). |
| **`runs/`** | **Durable per-run workspaces**. Normal live execution writes to `data/runs/<run_scoped_id>/processed/` and `data/runs/<run_scoped_id>/artifacts/` so concurrent runs do not collide. |
| **`processed/`** | Legacy shared **normalized tables** path (`panel.csv`, `features.csv`). Kept only for explicit legacy/dev opt-in after Phase 1 run isolation. |
| **`artifacts/`** | Legacy shared **analysis outputs** path (`anomalies.csv`, `report.md`, coverage/findings CSVs). Kept only for explicit legacy/dev opt-in after Phase 1 run isolation. |
| **`evaluation/`** | **Benchmark runs**: `*_results.json`, `*_summary.json`, and per-case folders (e.g. `suite_fixtures_v1/<case_id>/`) with CSVs copied or generated for that case. Operator or benchmark traffic only; not normal user-run histories or live pipeline output. |

**Confusion guard:** normal live runs now write under `runs/<run_scoped_id>/processed` and `runs/<run_scoped_id>/artifacts`; `processed` / `artifacts` are legacy shared paths; `evaluation` is tests/demos/fixtures only.

Constants in `config.py`: `DATA_RAW`, `DATA_RUNS`, `DATA_PROCESSED`, `DATA_ARTIFACTS`. Evaluation output dir is set per suite (default `data/evaluation` in benchmark JSON).
