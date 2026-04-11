# EDGAR Anomaly Report (V1)
## Credibility & coverage
### Trustworthiness snapshot
#### Metric coverage (panel)

| metric              |   coverage |   slots |   present |   missing |
|:--------------------|-----------:|--------:|----------:|----------:|
| revenue             |          1 |      15 |        15 |         0 |
| net_income          |          1 |      15 |        15 |         0 |
| total_assets        |          1 |      15 |        15 |         0 |
| total_liabilities   |          1 |      15 |        15 |         0 |
| operating_cash_flow |          1 |      15 |        15 |         0 |
| current_assets      |          1 |      15 |        15 |         0 |
| current_liabilities |          1 |      15 |        15 |         0 |
#### Caveat flags (roll-ups)

**Extraction caveat codes** (per metric cell; from tag/unit resolution):

- `duplicate_candidates_resolved`: **105** caveat row(s)
- `fallback_tag_used`: **15** caveat row(s)

**Panel context caveat codes** (per CIK × period):

- `limited_peer_coverage`: **15** caveat row(s)
- `missing_prior_period`: **6** caveat row(s)
- `sparse_history`: **4** caveat row(s)

#### Pipeline effects on interpretation

- **metric_extraction** / `duplicate_resolved`: **145**

#### Manual validation

_Manual validation: no records yet (header-only or empty)._ 

### Data quality summary
| metric                                  |   value | unit      |
|:----------------------------------------|--------:|:----------|
| long_metric_rows                        |     105 | rows      |
| distinct_cik_long                       |       1 | companies |
| wide_panel_rows_before_revenue_required |      15 | rows      |
| panel_rows_after_revenue_required       |      15 | rows      |
| feature_rows                            |      15 | rows      |
| anomaly_rows                            |       6 | rows      |
- **rows_removed_missing_revenue**: 0.0 rows (wide_panel_before_revenue_filter minus panel (revenue required))

_Missingness (panel, sample; see CSV for full)._ 

| metric              |   frac_na |
|:--------------------|----------:|
| revenue             |         0 |
| net_income          |         0 |
| total_assets        |         0 |
| total_liabilities   |         0 |
| operating_cash_flow |         0 |
| current_assets      |         0 |
| current_liabilities |         0 |

### Exclusions (pipeline)
| stage             | reason_code        |   count | cik   | period   | metric   | tag   | detail                  |
|:------------------|:-------------------|--------:|:------|:---------|:---------|:------|:------------------------|
| metric_extraction | year_out_of_range  |     558 |       |          |          |       | SEC companyfacts → long |
| metric_extraction | invalid_period     |     308 |       |          |          |       | SEC companyfacts → long |
| metric_extraction | invalid_form       |     161 |       |          |          |       | SEC companyfacts → long |
| metric_extraction | duplicate_resolved |     145 |       |          |          |       | SEC companyfacts → long |
### Peer-relative findings summary
| peer_coverage      |   row_count |
|:-------------------|------------:|
| insufficient_peers |          60 |
- **Peer signal rows with extreme_high / extreme_low**: 0 (of 60)

**Unified anomaly rows by category** (self + peer layer):

- `self_relative`: 6

_Artifact paths (relative to project root): `data/artifacts/data_quality_summary.csv`, `data/artifacts/exclusions_summary.csv`, `data/artifacts/peer_signals.csv`, `data/artifacts/trend_break_signals.csv`, `data/artifacts/unified_findings.csv`, `data/artifacts/findings_summary_by_company.csv`, `data/artifacts/findings_summary_by_metric.csv`, `data/artifacts/findings_summary_by_period.csv`, `data/artifacts/metric_coverage_summary.csv`, `data/artifacts/metric_coverage_by_company.csv`, `data/artifacts/metric_coverage_by_period.csv`, `data/artifacts/metric_caveats_extraction.csv`, `data/artifacts/metric_caveats_panel.csv`, `validation/manual_validation.csv`._

---

## Normalized quarterly panel (sample)
|     cik | period   |   revenue |   net_income |   total_assets |   total_liabilities |
|--------:|:---------|----------:|-------------:|---------------:|--------------------:|
| 1090872 | 2021-Q2  | 2.595e+09 |     2.98e+08 |     9.627e+09  |           4.754e+09 |
| 1090872 | 2021-Q3  | 3.856e+09 |     4.97e+08 |     9.627e+09  |           4.754e+09 |
| 1090872 | 2022-Q1  | 1.548e+09 |     2.88e+08 |     1.0705e+10 |           5.316e+09 |
| 1090872 | 2022-Q2  | 3.073e+09 |     5.04e+08 |     1.0705e+10 |           5.316e+09 |
| 1090872 | 2022-Q3  | 4.659e+09 |     7.68e+08 |     1.0705e+10 |           5.316e+09 |
| 1090872 | 2023-Q1  | 1.674e+09 |     2.83e+08 |     1.0532e+10 |           5.227e+09 |
| 1090872 | 2023-Q2  | 3.281e+09 |     5.57e+08 |     1.0532e+10 |           5.227e+09 |
| 1090872 | 2023-Q3  | 4.999e+09 |     8.86e+08 |     1.0532e+10 |           5.227e+09 |
| 1090872 | 2024-Q1  | 1.756e+09 |     3.52e+08 |     1.0763e+10 |           4.918e+09 |
| 1090872 | 2024-Q2  | 3.473e+09 |     6.54e+08 |     1.0763e+10 |           4.918e+09 |
| 1090872 | 2024-Q3  | 5.145e+09 |     7.65e+08 |     1.0763e+10 |           4.918e+09 |
| 1090872 | 2025-Q1  | 1.658e+09 |     3.48e+08 |     1.1846e+10 |           5.948e+09 |
| 1090872 | 2025-Q2  | 3.231e+09 |     6.56e+08 |     1.1846e+10 |           5.948e+09 |
| 1090872 | 2025-Q3  | 4.809e+09 |     9.38e+08 |     1.1846e+10 |           5.948e+09 |
| 1090872 | 2026-Q1  | 1.681e+09 |     3.18e+08 |     1.2727e+10 |           5.986e+09 |
## Feature table (sample)
|     cik | period   |   revenue_growth_qoq |   net_margin |   current_ratio |   debt_to_assets |
|--------:|:---------|---------------------:|-------------:|----------------:|-----------------:|
| 1090872 | 2021-Q2  |           nan        |     0.114836 |         2.32788 |         0.493819 |
| 1090872 | 2021-Q3  |             0.485934 |     0.12889  |         2.32788 |         0.493819 |
| 1090872 | 2022-Q1  |            -0.598548 |     0.186047 |         2.22424 |         0.49659  |
| 1090872 | 2022-Q2  |             0.985142 |     0.164009 |         2.22424 |         0.49659  |
| 1090872 | 2022-Q3  |             0.516108 |     0.164842 |         2.22424 |         0.49659  |
| 1090872 | 2023-Q1  |            -0.640695 |     0.169056 |         2.03009 |         0.496297 |
| 1090872 | 2023-Q2  |             0.959976 |     0.169765 |         2.03009 |         0.496297 |
| 1090872 | 2023-Q3  |             0.523621 |     0.177235 |         2.03009 |         0.496297 |
| 1090872 | 2024-Q1  |            -0.64873  |     0.200456 |         2.61135 |         0.456936 |
| 1090872 | 2024-Q2  |             0.97779  |     0.18831  |         2.61135 |         0.456936 |
| 1090872 | 2024-Q3  |             0.481428 |     0.148688 |         2.61135 |         0.456936 |
| 1090872 | 2025-Q1  |            -0.677745 |     0.209891 |         2.08918 |         0.50211  |
| 1090872 | 2025-Q2  |             0.948733 |     0.203033 |         2.08918 |         0.50211  |
| 1090872 | 2025-Q3  |             0.488394 |     0.195051 |         2.08918 |         0.50211  |
| 1090872 | 2026-Q1  |            -0.650447 |     0.189173 |         1.95739 |         0.470339 |
## Trend-break signals (window shifts)
_Deterministic window comparison on feature trends: prior-window mean/slope vs recent-window mean/slope; includes explicit short-history rows._

- **Short-history rows**: 17 of 60

|     cik | period   | metric         | trend_signal_type   |   trend_score |   mean_shift |   slope_shift | consecutive_direction   |   history_points |   window_prior |   window_recent |
|--------:|:---------|:---------------|:--------------------|--------------:|-------------:|--------------:|:------------------------|-----------------:|---------------:|----------------:|
| 1090872 | 2024-Q1  | net_margin     | strong_shift        |       3.52076 |  0.0209576   |   0.0207586   | improving               |                9 |              3 |               2 |
| 1090872 | 2023-Q3  | net_margin     | strong_shift        |       3.50495 |  0.00753121  |   0.00494661  | improving               |                8 |              3 |               2 |
| 1090872 | 2024-Q1  | current_ratio  | strong_shift        |       3.14676 |  0.225915    |   0.678336    | mixed                   |                9 |              3 |               2 |
| 1090872 | 2024-Q1  | debt_to_assets | strong_shift        |       3.03921 | -0.0197784   |  -0.0392145   | mixed                   |                9 |              3 |               2 |
| 1090872 | 2024-Q2  | net_margin     | strong_shift        |       3.01624 |  0.0223637   |  -0.0162354   | mixed                   |               10 |              3 |               2 |
| 1090872 | 2023-Q2  | current_ratio  | strong_shift        |       3       | -0.194148    |  -6.68068e-16 | mixed                   |                7 |              3 |               2 |
| 1090872 | 2024-Q2  | current_ratio  | strong_shift        |       3       |  0.581262    |  -4.50872e-16 | mixed                   |               10 |              3 |               2 |
| 1090872 | 2025-Q2  | current_ratio  | strong_shift        |       3       | -0.522172    |   8.54731e-17 | mixed                   |               13 |              3 |               2 |
| 1090872 | 2025-Q2  | debt_to_assets | strong_shift        |       3       |  0.0451746   |  -1.57274e-17 | mixed                   |               13 |              3 |               2 |
| 1090872 | 2024-Q2  | debt_to_assets | strong_shift        |       3       | -0.0393612   |  -3.74871e-17 | mixed                   |               10 |              3 |               2 |
| 1090872 | 2023-Q2  | debt_to_assets | strong_shift        |       3       | -0.000293379 |  -1.48863e-16 | mixed                   |                7 |              3 |               2 |
| 1090872 | 2023-Q1  | current_ratio  | strong_shift        |       2.83633 | -0.131621    |  -0.142327    | mixed                   |                6 |              3 |               2 |
## Top combined findings
_Highest adjusted findings first; prioritizes rows where self-relative and peer-relative evidence agree._

| finding_source   | finding_type   |     cik | period   | metric         | direction   |   score_adjusted |   score_raw |   score_penalty |   overlap_count | overlap_sources     | caveat_codes   |
|:-----------------|:---------------|--------:|:---------|:---------------|:------------|-----------------:|------------:|----------------:|----------------:|:--------------------|:---------------|
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | net_margin     | improving   |          3.52076 |     3.52076 |               0 |               2 | anomaly;trend_break | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q3  | net_margin     | improving   |          3.50495 |     3.50495 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | current_ratio  | mixed       |          3.14676 |     3.14676 |               0 |               2 | anomaly;trend_break | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | debt_to_assets | mixed       |          3.03921 |     3.03921 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q2  | net_margin     | mixed       |          3.01624 |     3.01624 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q2  | current_ratio  | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q2  | current_ratio  | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q2  | debt_to_assets | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
## Unified findings (high-level)
_Single machine-friendly table combining anomaly and trend-break findings with caveat-adjusted ranking._

| finding_source   | finding_type   |     cik | period   | metric         | direction   |   score_adjusted |   score_raw |   score_penalty |   overlap_count | overlap_sources     | caveat_codes   |
|:-----------------|:---------------|--------:|:---------|:---------------|:------------|-----------------:|------------:|----------------:|----------------:|:--------------------|:---------------|
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | net_margin     | improving   |          3.52076 |     3.52076 |               0 |               2 | anomaly;trend_break | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q3  | net_margin     | improving   |          3.50495 |     3.50495 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | current_ratio  | mixed       |          3.14676 |     3.14676 |               0 |               2 | anomaly;trend_break | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q1  | debt_to_assets | mixed       |          3.03921 |     3.03921 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q2  | net_margin     | mixed       |          3.01624 |     3.01624 |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q2  | current_ratio  | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q2  | current_ratio  | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2025-Q2  | current_ratio  | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2025-Q2  | debt_to_assets | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2024-Q2  | debt_to_assets | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q2  | debt_to_assets | mixed       |          3       |     3       |               0 |               1 | trend_break         | none           |
| trend_break      | strong_shift   | 1090872 | 2023-Q1  | current_ratio  | mixed       |          2.83633 |     2.83633 |               0 |               1 | trend_break         | none           |
## Company-level summary
|     cik |   finding_count |   high_severity_count |   avg_score_adjusted |   sum_score_adjusted |   sum_score_penalty | top_finding_category   |   repeated_deterioration_count |
|--------:|----------------:|----------------------:|---------------------:|---------------------:|--------------------:|:-----------------------|-------------------------------:|
| 1090872 |              41 |                    18 |              1.94848 |              79.8877 |                 3.9 | moderate_shift         |                              2 |
## Peer-set summary
**Metrics with highest adjusted severity**

| metric             |   finding_count |   high_severity_count |   avg_score_adjusted |   sum_score_adjusted |   sum_score_penalty | top_finding_category   |
|:-------------------|----------------:|----------------------:|---------------------:|---------------------:|--------------------:|:-----------------------|
| current_ratio      |              12 |                     5 |             2.11983  |            25.4379   |                 0.6 | moderate_shift         |
| net_margin         |              10 |                     5 |             2.01711  |            20.1711   |                 1.9 | moderate_shift         |
| debt_to_assets     |               8 |                     4 |             2.21748  |            17.7399   |                 0   | moderate_shift         |
| revenue_growth_qoq |               9 |                     4 |             1.71606  |            15.4445   |                 0   | moderate_shift         |
| net_income         |               1 |                     0 |             0.930089 |             0.930089 |                 0.5 | self_relative          |
| revenue            |               1 |                     0 |             0.164235 |             0.164235 |                 0.9 | self_relative          |

**Periods with broad finding concentration**

| period   |   finding_count |   high_severity_count |   avg_score_adjusted |   sum_score_adjusted |   sum_score_penalty | top_finding_category   |
|:---------|----------------:|----------------------:|---------------------:|---------------------:|--------------------:|:-----------------------|
| 2024-Q1  |               6 |                     5 |              2.6917  |             16.1502  |                 1.2 | strong_shift           |
| 2024-Q2  |               4 |                     3 |              2.55823 |             10.2329  |                 0   | strong_shift           |
| 2025-Q2  |               4 |                     2 |              2.12847 |              8.51386 |                 0   | moderate_shift         |
| 2023-Q3  |               4 |                     1 |              1.86825 |              7.47301 |                 0   | moderate_shift         |
| 2023-Q2  |               3 |                     2 |              2.41867 |              7.25602 |                 0   | strong_shift           |
| 2024-Q3  |               4 |                     0 |              1.37006 |              5.48023 |                 0.5 | moderate_shift         |
| 2025-Q3  |               4 |                     0 |              1.32983 |              5.31934 |                 0   | moderate_shift         |
| 2023-Q1  |               2 |                     2 |              2.63846 |              5.27691 |                 0   | strong_shift           |
## Caveat-aware interpretation notes
- **Findings with caveats**: 6 of 41
- **Total caveat penalty applied**: 3.900
- **Average penalty per finding**: 0.095
- **Most frequent caveat codes**: `insufficient_peer_coverage`=6; `limited_peer_coverage`=6; `missing_prior_period`=4; `sparse_history`=2; `duplicate_candidates_resolved`=2; `fallback_tag_used`=1

## Anomaly table (unified: self + peer layer)
_Rows: union of (1) |self z| > 2.5 vs trailing up to 4 quarters (current excluded) and (2) peer-signal extremes (``peer_cs_alert`` = extreme_high/low). ``anomaly_category`` = `self_relative` | `peer_relative` | `combined`. `z_score_peer` = LOO cross-section; `peer_cs_*` = full cross-section from peer_signals._ 

|     cik | period   | metric        | anomaly_category   | self_anomaly   | peer_anomaly   | direction   |     value |   zscore |   self_baseline_mean |   self_baseline_std |   self_baseline_n |   window_max_quarters |   z_score_peer |   peer_group_n | peer_deviation_strong   |   peer_cs_pct_rank |   peer_cs_z | peer_cs_coverage   | peer_cs_alert   | comparison_scope   | caveat_codes                                                                                                                         |
|--------:|:---------|:--------------|:-------------------|:---------------|:---------------|:------------|----------:|---------:|---------------------:|--------------------:|------------------:|----------------------:|---------------:|---------------:|:------------------------|-------------------:|------------:|:-------------------|:----------------|:-------------------|:-------------------------------------------------------------------------------------------------------------------------------------|
| 1090872 | 2022-Q1  | net_margin    | self_relative      | True           | False          | high        | 0.186047  |  9.13394 |           0.121863   |          0.00702691 |                 2 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period;sparse_history                                                 |
| 1090872 | 2024-Q1  | net_margin    | self_relative      | True           | False          | high        | 0.200456  |  6.77261 |           0.170225   |          0.00446369 |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period                                                                |
| 1090872 | 2024-Q1  | current_ratio | self_relative      | True           | False          | high        | 2.61135   |  6.33681 |           2.07863    |          0.0840683  |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period                                                                |
| 1090872 | 2022-Q3  | net_income    | self_relative      | True           | False          | high        | 7.68e+08  |  3.57522 |           3.9675e+08 |          1.0384e+08 |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | unavailable        | unavailable     | self_history       | duplicate_candidates_resolved;insufficient_peer_coverage;limited_peer_coverage                                                       |
| 1090872 | 2024-Q3  | net_margin    | self_relative      | True           | False          | low         | 0.148688  | -3.04053 |           0.183942   |          0.0115945  |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage                                                                                     |
| 1090872 | 2022-Q1  | revenue       | self_relative      | True           | False          | low         | 1.548e+09 | -2.66059 |           3.2255e+09 |          6.305e+08  |                 2 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | duplicate_candidates_resolved;fallback_tag_used;insufficient_peer_coverage;limited_peer_coverage;missing_prior_period;sparse_history |
## Top 5 anomalies (numeric detail)
|     cik | period   | metric        | anomaly_category   | self_anomaly   | peer_anomaly   | direction   |    value |   zscore |   self_baseline_mean |   self_baseline_std |   self_baseline_n |   window_max_quarters |   z_score_peer |   peer_group_n | peer_deviation_strong   |   peer_cs_pct_rank |   peer_cs_z | peer_cs_coverage   | peer_cs_alert   | comparison_scope   | caveat_codes                                                                         |
|--------:|:---------|:--------------|:-------------------|:---------------|:---------------|:------------|---------:|---------:|---------------------:|--------------------:|------------------:|----------------------:|---------------:|---------------:|:------------------------|-------------------:|------------:|:-------------------|:----------------|:-------------------|:-------------------------------------------------------------------------------------|
| 1090872 | 2022-Q1  | net_margin    | self_relative      | True           | False          | high        | 0.186047 |  9.13394 |           0.121863   |          0.00702691 |                 2 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period;sparse_history |
| 1090872 | 2024-Q1  | net_margin    | self_relative      | True           | False          | high        | 0.200456 |  6.77261 |           0.170225   |          0.00446369 |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period                |
| 1090872 | 2024-Q1  | current_ratio | self_relative      | True           | False          | high        | 2.61135  |  6.33681 |           2.07863    |          0.0840683  |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage;missing_prior_period                |
| 1090872 | 2022-Q3  | net_income    | self_relative      | True           | False          | high        | 7.68e+08 |  3.57522 |           3.9675e+08 |          1.0384e+08 |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | unavailable        | unavailable     | self_history       | duplicate_candidates_resolved;insufficient_peer_coverage;limited_peer_coverage       |
| 1090872 | 2024-Q3  | net_margin    | self_relative      | True           | False          | low         | 0.148688 | -3.04053 |           0.183942   |          0.0115945  |                 4 |                     4 |            nan |              1 | False                   |                nan |         nan | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage;limited_peer_coverage                                     |
## Top 5 anomaly explanations (machine-readable)
- `category=self_relative; self=True; peer_cs=False; dir=high; obs=0.186047; self_z=9.1339; baseline_prior_quarters mean=0.121863 std=0.00702691 n=2/4; peer_LOO_z=n/a; caveats=insufficient_peer_coverage;limited_peer_coverage;missing_prior_period;sparse_history`
- `category=self_relative; self=True; peer_cs=False; dir=high; obs=0.200456; self_z=6.7726; baseline_prior_quarters mean=0.170225 std=0.00446369 n=4/4; peer_LOO_z=n/a; caveats=insufficient_peer_coverage;limited_peer_coverage;missing_prior_period`
- `category=self_relative; self=True; peer_cs=False; dir=high; obs=2.61135; self_z=6.3368; baseline_prior_quarters mean=2.07863 std=0.0840683 n=4/4; peer_LOO_z=n/a; caveats=insufficient_peer_coverage;limited_peer_coverage;missing_prior_period`
- `category=self_relative; self=True; peer_cs=False; dir=high; obs=7.68e+08; self_z=3.5752; baseline_prior_quarters mean=3.9675e+08 std=1.0384e+08 n=4/4; peer_LOO_z=n/a; caveats=duplicate_candidates_resolved;insufficient_peer_coverage;limited_peer_coverage`
- `category=self_relative; self=True; peer_cs=False; dir=low; obs=0.148688; self_z=-3.0405; baseline_prior_quarters mean=0.183942 std=0.0115945 n=4/4; peer_LOO_z=n/a; caveats=insufficient_peer_coverage;limited_peer_coverage`
## Peer-relative detail (cross-section by period)
_Metrics: **revenue, net_margin, current_ratio, debt_to_assets**. Summary counts appear under *Credibility & coverage*. Sample of peer extremes:_ 

_No peer extremes at current thresholds (see `peer_signals.csv`)._
