# Experiment Tool Catalog

Sixteen deterministic tools registered by `build_default_registry()`
(`agentic/experiments/`): twelve general analytical tools plus four first-party
EDGAR wrappers. Every tool declares the full descriptor contract
([`experiment-contract.md`](./experiment-contract.md)) and emits structured
observations, evidence, and reproducible artifacts. None call an LLM.

## General analytical tools

| # | Tool | Purpose | Key params | Statistical outputs | Artifacts |
|---|---|---|---|---|---|
| 1 | `profile_dataset` | Per-column dtype, role, missingness, distinct, numeric stats | — | sample size, coverage | table, json |
| 2 | `summarize_distribution` | Descriptive stats + shape of a numeric column | `column` | sample size, skew, coverage, assumptions | json, chart |
| 3 | `analyze_missingness` | Per-column & overall missing values | `columns?` | coverage, warnings | table |
| 4 | `detect_outliers` | Z-score / IQR outlier flags | `column`, `method`, `threshold` | effect size (outlier fraction), coverage, assumptions | table, chart |
| 5 | `analyze_correlation` | Pairwise Pearson correlations | `columns?`, `strong_threshold` | effect size (r), CI (Fisher), p (approx), sample size | table, chart |
| 6 | `compare_groups` | Compare a value across groups | `value_column`, `group_column` | effect size (Cohen's d), t/p (approx), sample size | table, chart |
| 7 | `analyze_time_series_trend` | OLS trend over ordered time (per entity) | `value_column`, `time_column?`, `entity_column?` | effect size (R²), slope CI, sample size | table, chart |
| 8 | `detect_change_points` | Single mean-shift via one-split segmentation | `value_column`, `time_column?`, `min_segment` | effect size (std. shift), coverage | chart |
| 9 | `fit_simple_regression` | OLS y ~ x with diagnostics | `x_column`, `y_column` | effect size (R²), slope CI/SE, p (approx), residual diagnostics | table, chart |
| 10 | `test_association` | Chi-square / Cramér's V for two categoricals | `column_a`, `column_b`, `max_levels` | effect size (Cramér's V), sample size, assumptions | table |
| 11 | `rank_entities` | Rank entities by an aggregated metric | `metric_column`, `entity_column?`, `aggregation`, `top_n`, `ascending` | sample size, coverage | table, chart |
| 12 | `generate_deterministic_chart` | Emit a deterministic chart **spec** (no render) | `chart_type`, `x_column`, `y_column?`, `series_column?`, `max_points` | point count | chart |

Notes:
- p-values (tools 5, 6, 7, 9) use a **normal / large-sample approximation** —
  declared in each result's `assumptions` — so the system needs no scipy. Effect
  sizes are the primary evidence-strength input.
- All numeric params are typed and validated; column params are checked against
  the dataset manifest before running.

## EDGAR domain tools (wrappers, not reimplementations)

These call the existing deterministic EDGAR computations and translate their
outputs into structured evidence/artifacts. Input is an EDGAR **features** frame
(`cik`, `period` + metric columns); build the manifest with `EDGARAdapter` so
`period` is the time index.

| Tool | Wraps | Purpose |
|---|---|---|
| `edgar_peer_comparison` | `src.peer_signals.compute_peer_signals` | Cross-sectional peer extremes per (cik, period, metric). |
| `edgar_trend_break_analysis` | `src.trend_breaks.compute_trend_break_signals` | Windowed moderate/strong trend-break signals. |
| `edgar_revenue_growth_analysis` | `edgar_project.mcp.adapters.detect_anomalies_dataframe` (→ `src.anomaly`) | Anomalous quarter-over-quarter revenue growth. |
| `edgar_margin_quality_analysis` | `edgar_project.mcp.adapters.detect_anomalies_dataframe` (→ `src.anomaly`) | Anomalous net-margin behavior (margin quality proxy). |

### `edgar_segment_analysis` — intentionally omitted

The EDGAR panel produced by the deterministic pipeline has **no segment-level
data** (only entity × period financial metrics). There is no existing computation
to wrap, so `edgar_segment_analysis` is not implemented, per the "if existing
support permits" guidance. It can be added when segment extraction lands in the
`src` layer.

## Modalities

General tools accept `tabular` and `time_series` manifests; the trend and
change-point tools additionally require a temporal capability. EDGAR tools require
`time_series`/`tabular` with the EDGAR feature columns present. Document and
relational inputs are represented via the adapter layer and can be added as tools
without changing the contract.

## Determinism guarantee

Given identical dataset + params, every tool yields the same `output_fingerprint`
and byte-identical artifacts across runs and processes (excluding volatile
ids/timestamps). See `tests/agentic/test_experiments.py`
(`test_deterministic_repeatability`, `test_edgar_tool_deterministic`,
`test_artifacts_generated_and_addressed`).
