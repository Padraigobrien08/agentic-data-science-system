"""Metric coverage tables from the normalized wide panel."""

import pandas as pd

from edgar_project.run_workspace import build_run_workspace
from src.metric_coverage import (
    compute_metric_coverage_by_company,
    compute_metric_coverage_by_period,
    compute_metric_coverage_summary,
    compute_metric_coverage_tables,
)
from src.normalization import METRIC_COLUMNS


def _minimal_panel() -> pd.DataFrame:
    """Two companies, two periods; sparse metrics to exercise missing counts."""
    return pd.DataFrame(
        {
            "cik": [1, 1, 2, 2],
            "period": ["2020-Q1", "2020-Q2", "2020-Q1", "2020-Q2"],
            "revenue": [100.0, 110.0, 200.0, pd.NA],
            "net_income": [10.0, pd.NA, 20.0, 22.0],
            "total_assets": [1000.0, 1000.0, pd.NA, 900.0],
            "total_liabilities": [400.0, 400.0, 300.0, 300.0],
            "operating_cash_flow": [5.0, 6.0, 7.0, 8.0],
            "current_assets": [pd.NA, pd.NA, pd.NA, pd.NA],
            "current_liabilities": [100.0, 100.0, 50.0, 50.0],
        }
    )


def test_summary_counts_and_ratio() -> None:
    panel = _minimal_panel()
    s = compute_metric_coverage_summary(panel)
    assert list(s.columns) == [
        "metric_name",
        "n_slots",
        "available_count",
        "missing_count",
        "coverage_ratio",
    ]
    assert (s["n_slots"] == 4).all()
    rev = s[s["metric_name"] == "revenue"].iloc[0]
    assert rev["available_count"] == 3
    assert rev["missing_count"] == 1
    assert rev["coverage_ratio"] == 0.75
    ca = s[s["metric_name"] == "current_assets"].iloc[0]
    assert ca["available_count"] == 0
    assert ca["missing_count"] == 4


def test_by_company_aggregates_to_periods() -> None:
    panel = _minimal_panel()
    bc = compute_metric_coverage_by_company(panel)
    g1 = bc[(bc["cik"] == 1) & (bc["metric_name"] == "revenue")].iloc[0]
    assert g1["n_periods"] == 2
    assert g1["available_count"] == 2
    assert g1["coverage_ratio"] == 1.0


def test_by_period_sorted_and_counts() -> None:
    panel = _minimal_panel()
    bp = compute_metric_coverage_by_period(panel)
    assert bp.iloc[0]["period"] == "2020-Q1"
    r2020q1 = bp[(bp["period"] == "2020-Q1") & (bp["metric_name"] == "revenue")].iloc[0]
    assert r2020q1["n_companies"] == 2
    assert r2020q1["available_count"] == 2


def test_compute_metric_coverage_tables_keys() -> None:
    out = compute_metric_coverage_tables(_minimal_panel())
    assert set(out.keys()) == {"summary", "by_company", "by_period"}
    assert len(out["summary"]) == len(METRIC_COLUMNS)


def test_empty_panel() -> None:
    panel = pd.DataFrame()
    s = compute_metric_coverage_summary(panel)
    assert len(s) == len(METRIC_COLUMNS)
    assert (s["n_slots"] == 0).all()
    assert compute_metric_coverage_by_company(panel).empty
    assert compute_metric_coverage_by_period(panel).empty


def test_write_metric_coverage_artifacts_matches_compute_tables(tmp_path) -> None:
    """Pipeline writer emits the same frames as :func:`compute_metric_coverage_tables` (no SEC)."""
    from src.pipeline_runner import write_metric_coverage_artifacts

    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-coverage",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    ).ensure_directories()
    panel = _minimal_panel()
    expected = compute_metric_coverage_tables(panel)
    paths = write_metric_coverage_artifacts(panel, workspace=workspace)
    pd.testing.assert_frame_equal(pd.read_csv(paths["metric_coverage_summary"]), expected["summary"])
    pd.testing.assert_frame_equal(pd.read_csv(paths["metric_coverage_by_company"]), expected["by_company"])
    pd.testing.assert_frame_equal(pd.read_csv(paths["metric_coverage_by_period"]), expected["by_period"])


def test_write_all_phase1_artifacts_includes_trend_breaks(tmp_path) -> None:
    from src.pipeline_runner import write_all_phase1_artifacts

    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-phase1",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    ).ensure_directories()
    panel = _minimal_panel()
    paths = write_all_phase1_artifacts(
        workspace=workspace,
        panel=panel,
        features=panel.copy(),
        anomalies=pd.DataFrame(),
        report_markdown="# r\n",
    )
    assert "trend_breaks" in paths
    assert paths["trend_breaks"].name == "trend_break_signals.csv"
    assert "unified_findings" in paths
    assert paths["unified_findings"].name == "unified_findings.csv"
    assert paths["deterioration_focus"].name == "deterioration_focus.csv"
    assert paths["findings_summary_by_company"].name == "findings_summary_by_company.csv"
    assert paths["findings_summary_by_metric"].name == "findings_summary_by_metric.csv"
    assert paths["findings_summary_by_period"].name == "findings_summary_by_period.csv"
