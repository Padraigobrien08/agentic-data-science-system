# Fixture Benchmark Cases (v1)

This folder documents fixture-first benchmark intent for deterministic evaluation.

## Case Overview

1. `fixture_simple_deterioration_spike`
   - **What it tests:** obvious single-company deterioration/spike anomaly behavior.
   - **Why it matters:** fast sanity check that core anomaly scoring surfaces clear signals.

2. `fixture_peer_relative_outlier`
   - **What it tests:** peer-relative outlier behavior in a controlled cross-section.
   - **Why it matters:** validates peer layer independently from SEC data variability.

3. `fixture_anomaly_trend_overlap`
   - **What it tests:** overlap handling when anomaly and trend-break happen together.
   - **Why it matters:** protects unified findings logic (`overlap_count`, source preservation).

4. `fixture_sparse_history_caveats`
   - **What it tests:** sparse-history caveat behavior with limited prior periods.
   - **Why it matters:** ensures trustworthiness caveats are surfaced, not hidden.

5. `fixture_partial_data_trustworthiness`
   - **What it tests:** trustworthiness artifact generation under partial/missing data.
   - **Why it matters:** protects data-quality/coverage transparency and regression checks.

## Conventions

- Keep fixtures minimal and human-readable.
- Prefer CSV for tabular inspection in git reviews.
- Avoid timestamp-heavy or environment-dependent generated content.
