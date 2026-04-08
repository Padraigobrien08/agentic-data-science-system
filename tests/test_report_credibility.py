"""Report markdown: credibility sections when analytical artifacts are present (no SEC)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.report import _artifact_paths_footer, generate_report

import config


def _minimal_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "total_assets": [1000.0],
            "total_liabilities": [400.0],
            "current_assets": [100.0],
            "current_liabilities": [50.0],
            "revenue_growth_qoq": [0.0],
            "net_margin": [0.1],
            "current_ratio": [2.0],
            "debt_to_assets": [0.4],
        }
    )


def test_report_includes_credibility_blocks_when_inputs_non_empty(tmp_path: Path) -> None:
    dq = pd.DataFrame(
        [
            {
                "category": "stage_count",
                "name": "feature_rows",
                "value": 1,
                "unit": "rows",
                "notes": "",
            },
            {
                "category": "drop_rule",
                "name": "rows_removed_missing_revenue",
                "value": 0,
                "unit": "rows",
                "notes": "test note",
            },
            {
                "category": "missingness_metric",
                "name": "revenue",
                "value": 0.0,
                "unit": "frac_na",
                "notes": "",
            },
        ]
    )
    excl = pd.DataFrame(
        [
            {
                "stage": "normalization",
                "reason_code": "missing_required_metric",
                "count": 2,
                "cik": "",
                "period": "",
                "metric": "",
                "tag": "",
                "detail": "",
            }
        ]
    )
    peer = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [100.0],
            "peer_group_n": [3],
            "peer_coverage": ["full"],
            "peer_pct_rank": [50.0],
            "peer_z": [0.0],
            "peer_rank_signal": ["none"],
            "peer_z_signal": ["none"],
            "peer_alert": ["extreme_high"],
        }
    )
    anomalies = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "anomaly_category": ["peer_relative"],
            "self_anomaly": [False],
            "peer_anomaly": [True],
            "direction": ["high"],
            "value": [100.0],
            "zscore": [float("nan")],
            "explanation": ["category=peer_relative; self=False; ..."],
        }
    )
    mv = tmp_path / "manual_validation.csv"
    mv.write_text("ticker,cik,period,metric,validation_status,checked_date\nX,1,2021-Q1,revenue,ok,2026-01-01\n", encoding="utf-8")

    feats = _minimal_features()
    empty_cov = pd.DataFrame()
    md = generate_report(
        anomalies,
        feats,
        peer_signals=peer,
        data_quality=dq,
        exclusions=excl,
        manual_validation_path=mv,
        metric_coverage_summary=empty_cov,
        extraction_caveats=empty_cov,
        panel_caveats=empty_cov,
        top_n=1,
    )

    assert "# EDGAR Anomaly Report" in md
    assert "## Credibility & coverage" in md
    assert "### Trustworthiness snapshot" in md
    assert "#### Manual validation" in md
    assert "### Data quality summary" in md
    assert "feature_rows" in md
    assert "rows_removed_missing_revenue" in md
    assert "### Exclusions (pipeline)" in md
    assert "normalization" in md
    assert "### Peer-relative findings summary" in md
    assert "Unified anomaly rows by category" in md
    assert "data_quality_summary.csv" in md
    assert "## Peer-relative detail (cross-section by period)" in md
    assert "## Top 1 anomaly explanations (machine-readable)" in md
    assert "## Top combined findings" in md
    assert "## Company-level summary" in md
    assert "## Peer-set summary" in md
    assert "## Caveat-aware interpretation notes" in md


def test_report_normalized_panel_section_tolerates_missing_balance_sheet_columns() -> None:
    """Avoid KeyError when features omit panel columns (e.g. partial CSV from MCP)."""
    feats = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "revenue_growth_qoq": [0.0],
            "net_margin": [0.1],
        }
    )
    md = generate_report(
        pd.DataFrame(),
        feats,
        peer_signals=None,
        data_quality=None,
        exclusions=None,
        metric_coverage_summary=pd.DataFrame(),
        extraction_caveats=pd.DataFrame(),
        panel_caveats=pd.DataFrame(),
    )
    assert "## Normalized quarterly panel (sample)" in md
    assert "100.0" in md or "100" in md


def test_report_loads_trustworthiness_csvs_from_artifacts_dir_when_frames_omitted(
    monkeypatch, tmp_path: Path
) -> None:
    """MCP-style run: ``generate_report`` fills coverage/caveats from ``DATA_ARTIFACTS`` (no SEC)."""
    monkeypatch.setattr(config, "DATA_ARTIFACTS", tmp_path)
    cov = pd.DataFrame(
        [
            {
                "metric_name": "revenue",
                "n_slots": 4,
                "available_count": 4,
                "missing_count": 0,
                "coverage_ratio": 1.0,
            }
        ]
    )
    cov.to_csv(tmp_path / "metric_coverage_summary.csv", index=False)
    pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "source_tag": ["Revenues"],
            "n_candidates": [1],
            "caveat_codes": ["tag_resolution_fallback"],
        }
    ).to_csv(tmp_path / "metric_caveats_extraction.csv", index=False)
    pd.DataFrame(
        {"cik": [1], "period": ["2021-Q1"], "caveat_codes": ["limited_peer_coverage"]}
    ).to_csv(tmp_path / "metric_caveats_panel.csv", index=False)
    mv = tmp_path / "manual_validation.csv"
    mv.write_text(
        "ticker,cik,period,metric,validation_status,checked_date\nX,1,2021-Q1,revenue,ok,2026-01-01\n",
        encoding="utf-8",
    )
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=None,
        exclusions=None,
        manual_validation_path=mv,
        metric_coverage_summary=None,
        extraction_caveats=None,
        panel_caveats=None,
    )
    assert "### Trustworthiness snapshot" in md
    assert "revenue" in md
    assert "tag_resolution_fallback" in md
    assert "limited_peer_coverage" in md


def test_credibility_footer_lists_stable_trust_artifact_paths() -> None:
    foot = _artifact_paths_footer()
    assert "relative to project root" in foot
    for needle in (
        "trend_break_signals.csv",
        "unified_findings.csv",
        "findings_summary_by_company.csv",
        "findings_summary_by_metric.csv",
        "findings_summary_by_period.csv",
        "metric_coverage_summary.csv",
        "metric_coverage_by_company.csv",
        "metric_coverage_by_period.csv",
        "metric_caveats_extraction.csv",
        "metric_caveats_panel.csv",
        "manual_validation.csv",
    ):
        assert needle in foot


def test_trust_metric_coverage_warns_when_metric_name_column_missing(tmp_path: Path) -> None:
    bad = pd.DataFrame([{"wrong_col": 1}])
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=None,
        exclusions=None,
        manual_validation_path=tmp_path / "missing_manual.csv",
        metric_coverage_summary=bad,
        extraction_caveats=pd.DataFrame(),
        panel_caveats=pd.DataFrame(),
    )
    assert "no `metric_name` column" in md


def test_report_includes_trend_break_section_when_artifact_exists(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "DATA_ARTIFACTS", tmp_path)
    pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "net_margin",
                "value": 0.1,
                "history_points": 6,
                "window_prior": 3,
                "window_recent": 2,
                "prior_mean": 0.08,
                "recent_mean": 0.12,
                "mean_shift": 0.04,
                "prior_slope": 0.01,
                "recent_slope": 0.02,
                "slope_shift": 0.01,
                "consecutive_direction": "improving",
                "consecutive_len": 2,
                "short_history_flag": False,
                "trend_score": 2.2,
                "trend_signal_type": "strong_shift",
                "explanation": "metric=net_margin; prior_window=3; recent_window=2; mean_shift=0.04",
            }
        ]
    ).to_csv(tmp_path / "trend_break_signals.csv", index=False)
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=None,
        exclusions=None,
    )
    assert "## Trend-break signals (window shifts)" in md
    assert "strong_shift" in md


def test_report_uses_summary_artifacts_when_present(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "DATA_ARTIFACTS", tmp_path)
    pd.DataFrame(
        [
            {
                "finding_id": "f1",
                "finding_source": "anomaly",
                "finding_type": "combined",
                "cik": 1,
                "period": "2021-Q1",
                "metric": "revenue",
                "direction": "high",
                "score_raw": 3.0,
                "score_adjusted": 2.6,
                "score_penalty": 0.4,
                "caveat_codes": "sparse_history",
                "explanation_summary": "x",
                "provenance_artifacts": "anomalies_csv",
            }
        ]
    ).to_csv(tmp_path / "unified_findings.csv", index=False)
    pd.DataFrame(
        [
            {
                "cik": 1,
                "finding_count": 1,
                "high_severity_count": 1,
                "avg_score_adjusted": 2.6,
                "sum_score_adjusted": 2.6,
                "sum_score_penalty": 0.4,
                "top_finding_category": "combined",
                "repeated_deterioration_count": 0,
            }
        ]
    ).to_csv(tmp_path / "findings_summary_by_company.csv", index=False)
    pd.DataFrame(
        [
            {
                "metric": "revenue",
                "finding_count": 1,
                "high_severity_count": 1,
                "avg_score_adjusted": 2.6,
                "sum_score_adjusted": 2.6,
                "sum_score_penalty": 0.4,
                "top_finding_category": "combined",
            }
        ]
    ).to_csv(tmp_path / "findings_summary_by_metric.csv", index=False)
    pd.DataFrame(
        [
            {
                "period": "2021-Q1",
                "finding_count": 1,
                "high_severity_count": 1,
                "avg_score_adjusted": 2.6,
                "sum_score_adjusted": 2.6,
                "sum_score_penalty": 0.4,
                "top_finding_category": "combined",
            }
        ]
    ).to_csv(tmp_path / "findings_summary_by_period.csv", index=False)
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=None,
        exclusions=None,
    )
    assert "revenue" in md
    assert "combined" in md


def test_trustworthiness_snapshot_includes_metric_coverage_and_caveat_rollups() -> None:
    cov = pd.DataFrame(
        [
            {"metric_name": "revenue", "n_slots": 10, "available_count": 10, "missing_count": 0, "coverage_ratio": 1.0},
            {"metric_name": "net_income", "n_slots": 10, "available_count": 9, "missing_count": 1, "coverage_ratio": 0.9},
        ]
    )
    ext = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "caveat_codes": ["duplicate_candidates_resolved;fallback_tag_used"],
        }
    )
    pan = pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "caveat_codes": ["limited_peer_coverage"],
        }
    )
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=None,
        exclusions=None,
        metric_coverage_summary=cov,
        extraction_caveats=ext,
        panel_caveats=pan,
    )
    assert "`duplicate_candidates_resolved`" in md or "duplicate_candidates_resolved" in md
    assert "limited_peer_coverage" in md
    assert "net_income" in md or "0.9" in md


def test_credibility_section_emits_all_drop_rule_rows() -> None:
    dq = pd.DataFrame(
        [
            {
                "category": "drop_rule",
                "name": "rows_removed_missing_revenue",
                "value": 2,
                "unit": "rows",
                "notes": "note-a",
            },
            {
                "category": "drop_rule",
                "name": "hypothetical_second_rule",
                "value": 1,
                "unit": "rows",
                "notes": "note-b",
            },
        ]
    )
    md = generate_report(
        pd.DataFrame(),
        _minimal_features(),
        peer_signals=None,
        data_quality=dq,
        exclusions=None,
        metric_coverage_summary=pd.DataFrame(),
        extraction_caveats=pd.DataFrame(),
        panel_caveats=pd.DataFrame(),
    )
    assert "hypothetical_second_rule" in md
    assert "note-b" in md
