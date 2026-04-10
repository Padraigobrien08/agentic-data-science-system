# Data directories

All paths are **under the repository root**. Nothing here is a separate database—just files the pipeline and benchmarks write.

| Directory | Role |
|-----------|------|
| **`raw/`** | Cached SEC JSON (company facts, submissions, ticker map). Populated on **live** fetches. Safe to delete to force re-download (slower next run). |
| **`processed/`** | **Normalized tables** from the analytical pipeline: wide quarterly `panel.csv`, engineered `features.csv`. Inputs to anomaly detection. |
| **`artifacts/`** | **Analysis outputs**: `anomalies.csv`, `unified_findings.csv`, `report.md`, peer/trend/quality/coverage CSVs, etc. This is the usual place to look after a **live** `cli run` / `demo` (non-fixtures). |
| **`evaluation/`** | **Benchmark runs**: `*_results.json`, `*_summary.json`, and per-case folders (e.g. `suite_fixtures_v1/<case_id>/`) with CSVs copied or generated for that case. Not used for normal SEC pipeline output. |

**Confusion guard:** `processed` = intermediate panel/features; `artifacts` = scored outputs and report; `evaluation` = tests/demos/fixtures only.

Constants in `config.py`: `DATA_RAW`, `DATA_PROCESSED`, `DATA_ARTIFACTS`. Evaluation output dir is set per suite (default `data/evaluation` in benchmark JSON).
