# EDGAR Anomaly Report (V1)
## Credibility & coverage
### Trustworthiness snapshot
#### Metric coverage (panel)

_No metric coverage summary (run pipeline or provide `metric_coverage_summary.csv`)._

#### Caveat flags (roll-ups)

**Extraction caveat codes** (per metric cell; from tag/unit resolution):

_No extraction caveat rows._

**Panel context caveat codes** (per CIK × period):

_No panel caveat rows._

#### Pipeline effects on interpretation

_No exclusion summary._

#### Manual validation

_Manual validation: no records yet (header-only or empty)._ 

### Data quality summary
_No data quality summary (empty)._ 

### Exclusions (pipeline)
_No exclusion counts recorded for this run._ 

### Peer-relative findings summary
_No peer_signals rows._ 

**Unified anomaly rows by category** (self + peer layer):

- `peer_relative`: 64; `self_relative`: 27; `combined`: 4

_Artifact paths (relative to project root): `data/artifacts/data_quality_summary.csv`, `data/artifacts/exclusions_summary.csv`, `data/artifacts/peer_signals.csv`, `data/artifacts/trend_break_signals.csv`, `data/artifacts/unified_findings.csv`, `data/artifacts/findings_summary_by_company.csv`, `data/artifacts/findings_summary_by_metric.csv`, `data/artifacts/findings_summary_by_period.csv`, `data/artifacts/metric_coverage_summary.csv`, `data/artifacts/metric_coverage_by_company.csv`, `data/artifacts/metric_coverage_by_period.csv`, `data/artifacts/metric_caveats_extraction.csv`, `data/artifacts/metric_caveats_panel.csv`, `validation/manual_validation.csv`._

---

## Normalized quarterly panel (sample)
|    cik | period   |     revenue |   net_income |   total_assets |   total_liabilities |
|-------:|:---------|------------:|-------------:|---------------:|--------------------:|
| 320193 | 2021-Q1  | 9.1819e+10  |   2.2236e+10 |    3.23888e+11 |         2.58549e+11 |
| 320193 | 2021-Q2  | 1.50132e+11 |   3.3485e+10 |    3.23888e+11 |         2.58549e+11 |
| 320193 | 2021-Q3  | 2.09817e+11 |   4.4738e+10 |    3.23888e+11 |         2.58549e+11 |
| 320193 | 2022-Q1  | 1.11439e+11 |   2.8755e+10 |    3.51002e+11 |         2.87912e+11 |
| 320193 | 2022-Q2  | 2.01023e+11 |   5.2385e+10 |    3.51002e+11 |         2.87912e+11 |
| 320193 | 2022-Q3  | 2.82457e+11 |   7.4129e+10 |    3.51002e+11 |         2.87912e+11 |
| 320193 | 2023-Q1  | 1.23945e+11 |   3.463e+10  |    3.52755e+11 |         3.02083e+11 |
| 320193 | 2023-Q2  | 2.21223e+11 |   5.964e+10  |    3.52755e+11 |         3.02083e+11 |
| 320193 | 2023-Q3  | 3.04182e+11 |   7.9082e+10 |    3.52755e+11 |         3.02083e+11 |
| 320193 | 2024-Q1  | 1.17154e+11 |   2.9998e+10 |    3.52583e+11 |         2.90437e+11 |
| 320193 | 2024-Q2  | 2.1199e+11  |   5.4158e+10 |    3.52583e+11 |         2.90437e+11 |
| 320193 | 2024-Q3  | 2.93787e+11 |   7.4039e+10 |    3.52583e+11 |         2.90437e+11 |
| 320193 | 2025-Q1  | 1.19575e+11 |   3.3916e+10 |    3.6498e+11  |         3.0803e+11  |
| 320193 | 2025-Q2  | 2.10328e+11 |   5.7552e+10 |    3.6498e+11  |         3.0803e+11  |
| 320193 | 2025-Q3  | 2.96105e+11 |   7.9e+10    |    3.6498e+11  |         3.0803e+11  |
| 320193 | 2026-Q1  | 1.243e+11   |   3.633e+10  |    3.59241e+11 |         2.85508e+11 |
| 789019 | 2021-Q1  | 3.3055e+10  |   1.0678e+10 |    3.01311e+11 |         1.83007e+11 |
| 789019 | 2021-Q2  | 6.9961e+10  |   2.2327e+10 |    3.01311e+11 |         1.83007e+11 |
| 789019 | 2021-Q3  | 1.04982e+11 |   3.3079e+10 |    3.01311e+11 |         1.83007e+11 |
| 789019 | 2022-Q1  | 3.7154e+10  |   1.3893e+10 |    3.33779e+11 |         1.91791e+11 |
## Feature table (sample)
|    cik | period   |   revenue_growth_qoq |   net_margin |   current_ratio |   debt_to_assets |
|-------:|:---------|---------------------:|-------------:|----------------:|-----------------:|
| 320193 | 2021-Q1  |           nan        |     0.242172 |        1.3636   |         0.798267 |
| 320193 | 2021-Q2  |             0.635086 |     0.223037 |        1.3636   |         0.798267 |
| 320193 | 2021-Q3  |             0.39755  |     0.213224 |        1.3636   |         0.798267 |
| 320193 | 2022-Q1  |            -0.468875 |     0.258034 |        1.07455  |         0.820257 |
| 320193 | 2022-Q2  |             0.803884 |     0.260592 |        1.07455  |         0.820257 |
| 320193 | 2022-Q3  |             0.405098 |     0.262443 |        1.07455  |         0.820257 |
| 320193 | 2023-Q1  |            -0.56119  |     0.279398 |        0.879356 |         0.856354 |
| 320193 | 2023-Q2  |             0.784848 |     0.269592 |        0.879356 |         0.856354 |
| 320193 | 2023-Q3  |             0.375002 |     0.259983 |        0.879356 |         0.856354 |
| 320193 | 2024-Q1  |            -0.614856 |     0.256056 |        0.988012 |         0.823741 |
| 320193 | 2024-Q2  |             0.809499 |     0.255474 |        0.988012 |         0.823741 |
| 320193 | 2024-Q3  |             0.385853 |     0.252016 |        0.988012 |         0.823741 |
| 320193 | 2025-Q1  |            -0.592987 |     0.283638 |        0.867313 |         0.843964 |
| 320193 | 2025-Q2  |             0.758963 |     0.27363  |        0.867313 |         0.843964 |
| 320193 | 2025-Q3  |             0.407825 |     0.266797 |        0.867313 |         0.843964 |
| 320193 | 2026-Q1  |            -0.580216 |     0.292277 |        0.893293 |         0.794753 |
| 789019 | 2021-Q1  |           nan        |     0.323037 |        2.51577  |         0.607369 |
| 789019 | 2021-Q2  |             1.1165   |     0.319135 |        2.51577  |         0.607369 |
| 789019 | 2021-Q3  |             0.500579 |     0.315092 |        2.51577  |         0.607369 |
| 789019 | 2022-Q1  |            -0.646092 |     0.37393  |        2.07999  |         0.574605 |
## Trend-break signals (window shifts)
_Deterministic window comparison on feature trends: prior-window mean/slope vs recent-window mean/slope; includes explicit short-history rows._

_No trend-break rows (run pipeline or provide `trend_break_signals.csv`)._

## Top combined findings
_Highest adjusted findings first; prioritizes rows where self-relative and peer-relative evidence agree._

_No unified findings rows._

## Unified findings (high-level)
_Single machine-friendly table combining anomaly and trend-break findings with caveat-adjusted ranking._

_No unified findings rows (run pipeline or provide `unified_findings.csv`)._

## Company-level summary
_No company-level findings summary rows._

## Peer-set summary
_No metric-level summary rows._

_No period-level summary rows._

## Caveat-aware interpretation notes
_No caveat-aware interpretation rows._

## Anomaly table (unified: self + peer layer)
_Rows: union of (1) |self z| > 2.5 vs trailing up to 4 quarters (current excluded) and (2) peer-signal extremes (``peer_cs_alert`` = extreme_high/low). ``anomaly_category`` = `self_relative` | `peer_relative` | `combined`. `z_score_peer` = LOO cross-section; `peer_cs_*` = full cross-section from peer_signals._ 

|     cik | period   | metric             | anomaly_category   | self_anomaly   | peer_anomaly   | direction   |        value |   zscore |   self_baseline_mean |   self_baseline_std |   self_baseline_n |   window_max_quarters |   z_score_peer |   peer_group_n | peer_deviation_strong   |   peer_cs_pct_rank |   peer_cs_z | peer_cs_coverage   | peer_cs_alert   | comparison_scope   | caveat_codes               |
|--------:|:---------|:-------------------|:-------------------|:---------------|:---------------|:------------|-------------:|---------:|---------------------:|--------------------:|------------------:|----------------------:|---------------:|---------------:|:------------------------|-------------------:|------------:|:-------------------|:----------------|:-------------------|:---------------------------|
|  789019 | 2023-Q1  | net_margin         | combined           | True           | True           | high        |  0.452479    |  4.10747 |          0.355608    |         0.0235841   |                 4 |                     4 |       4.93237  |              3 | True                    |           100      |    1.33433  | full               | extreme_high    | combined           | none                       |
| 1045810 | 2025-Q2  | net_income         | self_relative      | True           | False          | high        |  8.232e+09   | 12.4277  |          2.22225e+09 |         4.83576e+08 |                 4 |                     4 |      -6.36614  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
| 1045810 | 2025-Q2  | net_margin         | combined           | True           | True           | high        |  0.3977      |  3.6336  |          0.193038    |         0.056325    |                 4 |                     4 |       1.50849  |              3 | False                   |           100      |    0.928803 | full               | extreme_high    | combined           | none                       |
|  320193 | 2022-Q1  | revenue_growth_qoq | self_relative      | True           | False          | low         | -0.468875    | -8.2951  |          0.516318    |         0.118768    |                 2 |                     4 |       7.79345  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | sparse_history             |
|  320193 | 2022-Q3  | revenue            | combined           | True           | True           | high        |  2.82457e+11 |  2.86838 |          1.68103e+11 |         3.98671e+10 |                 4 |                     4 |       3.91158  |              3 | True                    |           100      |    1.29311  | full               | extreme_high    | combined           | none                       |
|  320193 | 2021-Q3  | revenue            | combined           | True           | True           | high        |  2.09817e+11 |  3.04706 |          1.20976e+11 |         2.91565e+10 |                 2 |                     4 |       3.15779  |              3 | True                    |           100      |    1.23994  | full               | extreme_high    | combined           | sparse_history             |
| 1045810 | 2025-Q3  | net_income         | self_relative      | True           | False          | high        |  1.7475e+10  |  5.35978 |          3.87575e+09 |         2.53728e+09 |                 4 |                     4 |      -8.53876  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
|  789019 | 2022-Q1  | revenue_growth_qoq | self_relative      | True           | False          | low         | -0.646092    | -4.72342 |          0.808541    |         0.307962    |                 2 |                     4 |      -1.5888   |              3 | False                   |           nan      |  nan        | unavailable        | unavailable     | self_history       | sparse_history             |
| 1045810 | 2025-Q3  | revenue            | self_relative      | True           | False          | high        |  3.8819e+10  |  4.09223 |          1.59515e+10 |         5.58802e+09 |                 4 |                     4 |      -3.44708  |              3 | True                    |            33.3333 |   -1.26366  | full               | none            | self_history       | none                       |
| 1045810 | 2023-Q3  | net_income         | self_relative      | True           | False          | high        |  6.749e+09   |  3.86079 |          2.65275e+09 |         1.06099e+09 |                 4 |                     4 |      -5.26694  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
|  789019 | 2024-Q1  | debt_to_assets     | self_relative      | True           | False          | low         |  0.49943     | -3.85307 |          0.551292    |         0.0134599   |                 4 |                     4 |      -0.799693 |              3 | False                   |            66.6667 |   -0.592812 | full               | none            | self_history       | none                       |
|  320193 | 2022-Q3  | net_income         | self_relative      | True           | False          | high        |  7.4129e+10  |  3.69401 |          3.98408e+10 |         9.28212e+09 |                 4 |                     4 |       2.39806  |              3 | False                   |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
|  789019 | 2026-Q1  | debt_to_assets     | self_relative      | True           | False          | low         |  0.445109    | -3.57635 |          0.481706    |         0.0102329   |                 4 |                     4 |      -0.383189 |              3 | False                   |            66.6667 |   -0.305486 | full               | none            | self_history       | none                       |
| 1045810 | 2023-Q3  | revenue            | self_relative      | True           | False          | high        |  1.9271e+10  |  3.56445 |          9.11175e+09 |         2.85016e+09 |                 4 |                     4 |      -2.61157  |              3 | True                    |            33.3333 |   -1.17857  | full               | none            | self_history       | none                       |
| 1045810 | 2025-Q1  | debt_to_assets     | self_relative      | True           | False          | low         |  0.346123    | -3.54945 |          0.446935    |         0.0284022   |                 4 |                     4 |      -1.70443  |              3 | False                   |            33.3333 |   -0.991931 | full               | none            | self_history       | none                       |
| 1045810 | 2023-Q2  | net_income         | self_relative      | True           | False          | high        |  4.285e+09   |  3.48562 |          1.81075e+09 |         7.09844e+08 |                 4 |                     4 |      -4.43495  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
| 1045810 | 2026-Q3  | revenue            | self_relative      | True           | False          | high        |  9.1166e+10  |  4.0904  |          3.54115e+10 |         1.36306e+10 |                 4 |                     4 |     nan        |              1 | False                   |           nan      |  nan        | insufficient_peers | unavailable     | self_history       | insufficient_peer_coverage |
| 1045810 | 2026-Q3  | net_income         | self_relative      | True           | False          | high        |  5.0789e+10  |  3.86809 |          1.8017e+10  |         8.47241e+09 |                 4 |                     4 |     nan        |              1 | False                   |           nan      |  nan        | unavailable        | unavailable     | self_history       | insufficient_peer_coverage |
| 1045810 | 2022-Q3  | net_income         | self_relative      | True           | False          | high        |  2.875e+09   |  3.73299 |          1.43367e+09 |         3.86106e+08 |                 3 |                     4 |      -3.8611   |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | sparse_history             |
| 1045810 | 2023-Q1  | net_margin         | self_relative      | True           | False          | high        |  0.33775     |  3.04387 |          0.250439    |         0.0286842   |                 4 |                     4 |      -0.325733 |              3 | False                   |            66.6667 |   -0.261378 | full               | none            | self_history       | none                       |
| 1045810 | 2025-Q2  | revenue_growth_qoq | self_relative      | True           | False          | high        |  1.87806     |  3.01004 |         -0.00542397  |         0.625734    |                 4 |                     4 |       5.61393  |              3 | True                    |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
| 1045810 | 2024-Q1  | net_margin         | self_relative      | True           | False          | low         |  0.195222    | -2.88421 |          0.321609    |         0.0438202   |                 4 |                     4 |      -2.29147  |              3 | False                   |            33.3333 |   -1.12818  | full               | none            | self_history       | none                       |
| 1045810 | 2026-Q2  | net_income         | self_relative      | True           | False          | high        |  3.148e+10   |  3.46546 |          1.06578e+10 |         6.00851e+09 |                 4 |                     4 |     nan        |              2 | False                   |           nan      |  nan        | unavailable        | unavailable     | self_history       | insufficient_peer_coverage |
|  789019 | 2023-Q1  | debt_to_assets     | self_relative      | True           | False          | low         |  0.54352     | -2.76833 |          0.582796    |         0.0141874   |                 4 |                     4 |      -0.36426  |              3 | False                   |            66.6667 |   -0.29105  | full               | none            | self_history       | none                       |
|  789019 | 2022-Q3  | net_income         | self_relative      | True           | False          | high        |  4.4813e+10  |  2.7528  |          2.46638e+10 |         7.31955e+09 |                 4 |                     4 |       0.177141 |              3 | False                   |           nan      |  nan        | unavailable        | unavailable     | self_history       | none                       |
## Top 5 anomalies (numeric detail)
|     cik | period   | metric             | anomaly_category   | self_anomaly   | peer_anomaly   | direction   |        value |   zscore |   self_baseline_mean |   self_baseline_std |   self_baseline_n |   window_max_quarters |   z_score_peer |   peer_group_n | peer_deviation_strong   |   peer_cs_pct_rank |   peer_cs_z | peer_cs_coverage   | peer_cs_alert   | comparison_scope   | caveat_codes   |
|--------:|:---------|:-------------------|:-------------------|:---------------|:---------------|:------------|-------------:|---------:|---------------------:|--------------------:|------------------:|----------------------:|---------------:|---------------:|:------------------------|-------------------:|------------:|:-------------------|:----------------|:-------------------|:---------------|
|  789019 | 2023-Q1  | net_margin         | combined           | True           | True           | high        |  0.452479    |  4.10747 |          0.355608    |         0.0235841   |                 4 |                     4 |        4.93237 |              3 | True                    |                100 |    1.33433  | full               | extreme_high    | combined           | none           |
| 1045810 | 2025-Q2  | net_income         | self_relative      | True           | False          | high        |  8.232e+09   | 12.4277  |          2.22225e+09 |         4.83576e+08 |                 4 |                     4 |       -6.36614 |              3 | True                    |                nan |  nan        | unavailable        | unavailable     | self_history       | none           |
| 1045810 | 2025-Q2  | net_margin         | combined           | True           | True           | high        |  0.3977      |  3.6336  |          0.193038    |         0.056325    |                 4 |                     4 |        1.50849 |              3 | False                   |                100 |    0.928803 | full               | extreme_high    | combined           | none           |
|  320193 | 2022-Q1  | revenue_growth_qoq | self_relative      | True           | False          | low         | -0.468875    | -8.2951  |          0.516318    |         0.118768    |                 2 |                     4 |        7.79345 |              3 | True                    |                nan |  nan        | unavailable        | unavailable     | self_history       | sparse_history |
|  320193 | 2022-Q3  | revenue            | combined           | True           | True           | high        |  2.82457e+11 |  2.86838 |          1.68103e+11 |         3.98671e+10 |                 4 |                     4 |        3.91158 |              3 | True                    |                100 |    1.29311  | full               | extreme_high    | combined           | none           |
## Top 5 anomaly explanations (machine-readable)
- `category=combined; self=True; peer_cs=True; dir=high; obs=0.452479; self_z=4.1075; baseline_prior_quarters mean=0.355608 std=0.0235841 n=4/4; peer_LOO_z=4.9324 (period_n=3); |peer_LOO|>threshold; peer_cs_alert=extreme_high; caveats=none`
- `category=self_relative; self=True; peer_cs=False; dir=high; obs=8.2320e+09; self_z=12.4277; baseline_prior_quarters mean=2.2222e+09 std=4.83576e+08 n=4/4; peer_LOO_z=-6.3661 (period_n=3); |peer_LOO|>threshold; caveats=none`
- `category=combined; self=True; peer_cs=True; dir=high; obs=0.3977; self_z=3.6336; baseline_prior_quarters mean=0.193038 std=0.056325 n=4/4; peer_LOO_z=1.5085 (period_n=3); peer_cs_alert=extreme_high; caveats=none`
- `category=self_relative; self=True; peer_cs=False; dir=low; obs=-0.468875; self_z=-8.2951; baseline_prior_quarters mean=0.516318 std=0.118768 n=2/4; peer_LOO_z=7.7934 (period_n=3); |peer_LOO|>threshold; caveats=sparse_history`
- `category=combined; self=True; peer_cs=True; dir=high; obs=2.8246e+11; self_z=2.8684; baseline_prior_quarters mean=1.6810e+11 std=3.9867e+10 n=4/4; peer_LOO_z=3.9116 (period_n=3); |peer_LOO|>threshold; peer_cs_alert=extreme_high; caveats=none`
## Peer-relative detail (cross-section by period)
_Metrics: **revenue, net_margin, current_ratio, debt_to_assets**. Summary counts appear under *Credibility & coverage*. Sample of peer extremes:_ 

_No peer signal rows._
