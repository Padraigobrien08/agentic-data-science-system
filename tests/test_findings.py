"""Unified findings table: compact deterministic merge of anomaly + trend layers."""

from __future__ import annotations

import pandas as pd

from src.findings import (
    FINDINGS_SUMMARY_BY_COMPANY_COLUMNS,
    FINDINGS_SUMMARY_BY_METRIC_COLUMNS,
    FINDINGS_SUMMARY_BY_PERIOD_COLUMNS,
    UNIFIED_FINDINGS_COLUMNS,
    build_findings_summary_by_company,
    build_findings_summary_by_metric,
    build_findings_summary_by_period,
    build_unified_findings,
)


def test_build_unified_findings_schema_and_sort() -> None:
    anomalies = pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "revenue",
                "anomaly_category": "combined",
                "direction": "high",
                "combined_score_raw": 2.8,
                "combined_score_adjusted": 2.4,
                "combined_penalty_total": 0.4,
                "caveat_codes": "sparse_history",
                "combined_explanation": "x",
            }
        ]
    )
    trend = pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "revenue",
                "trend_signal_type": "strong_shift",
                "trend_score": 2.1,
                "consecutive_direction": "improving",
                "explanation": "t",
            }
        ]
    )
    out = build_unified_findings(anomalies, trend_breaks=trend)
    for c in UNIFIED_FINDINGS_COLUMNS:
        assert c in out.columns
    assert out.iloc[0]["finding_source"] == "anomaly"
    assert float(out.iloc[0]["score_adjusted"]) >= float(out.iloc[1]["score_adjusted"])
    # Same (cik, period, metric) appears in both anomaly + trend rows -> explicit overlap metadata.
    assert int(out.iloc[0]["overlap_count"]) == 2
    assert str(out.iloc[0]["overlap_sources"]) == "anomaly;trend_break"


def test_build_unified_findings_omits_low_value_trend_watch_rows() -> None:
    anomalies = pd.DataFrame()
    trend = pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "net_margin",
                "trend_signal_type": "watch",
                "trend_score": 0.6,
                "consecutive_direction": "mixed",
                "explanation": "t",
            }
        ]
    )
    out = build_unified_findings(anomalies, trend_breaks=trend)
    assert out.empty


def test_summary_builders_have_expected_fields_and_aggregates() -> None:
    uf = pd.DataFrame(
        [
            {
                "finding_id": "a1",
                "finding_source": "anomaly",
                "finding_type": "combined",
                "cik": 1,
                "period": "2021-Q1",
                "metric": "revenue",
                "direction": "deteriorating",
                "score_raw": 3.0,
                "score_adjusted": 2.6,
                "score_penalty": 0.4,
                "caveat_codes": "sparse_history",
                "explanation_summary": "",
                "provenance_artifacts": "anomalies_csv",
            },
            {
                "finding_id": "a2",
                "finding_source": "anomaly",
                "finding_type": "peer_relative",
                "cik": 1,
                "period": "2021-Q2",
                "metric": "revenue",
                "direction": "deteriorating",
                "score_raw": 2.5,
                "score_adjusted": 2.1,
                "score_penalty": 0.4,
                "caveat_codes": "none",
                "explanation_summary": "",
                "provenance_artifacts": "anomalies_csv",
            },
            {
                "finding_id": "t1",
                "finding_source": "trend_break",
                "finding_type": "strong_shift",
                "cik": 2,
                "period": "2021-Q2",
                "metric": "net_margin",
                "direction": "improving",
                "score_raw": 2.2,
                "score_adjusted": 2.2,
                "score_penalty": 0.0,
                "caveat_codes": "none",
                "explanation_summary": "",
                "provenance_artifacts": "trend_break_signals_csv",
            },
        ]
    )
    by_c = build_findings_summary_by_company(uf)
    by_m = build_findings_summary_by_metric(uf)
    by_p = build_findings_summary_by_period(uf)
    for c in FINDINGS_SUMMARY_BY_COMPANY_COLUMNS:
        assert c in by_c.columns
    for c in FINDINGS_SUMMARY_BY_METRIC_COLUMNS:
        assert c in by_m.columns
    for c in FINDINGS_SUMMARY_BY_PERIOD_COLUMNS:
        assert c in by_p.columns
    r1 = by_c[by_c["cik"] == 1].iloc[0]
    assert int(r1["finding_count"]) == 2
    assert int(r1["high_severity_count"]) == 2
    assert int(r1["repeated_deterioration_count"]) == 1
