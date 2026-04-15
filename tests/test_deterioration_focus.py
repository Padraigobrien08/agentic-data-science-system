"""Deterioration-focused slice of unified findings (planner / trend_deterioration path)."""

from __future__ import annotations

import pandas as pd

from edgar_project.run_workspace import build_run_workspace
from src.findings import (
    DETERIORATION_FOCUS_COLUMNS,
    build_deterioration_focus,
    build_unified_findings,
)


def test_build_deterioration_focus_empty_unified() -> None:
    out = build_deterioration_focus(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == list(DETERIORATION_FOCUS_COLUMNS)


def test_build_deterioration_focus_excludes_strength_spike_and_improving_trend() -> None:
    anomalies = pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "revenue",
                "anomaly_category": "combined",
                "direction": "high",
                "combined_score_raw": 3.0,
                "combined_score_adjusted": 2.8,
                "combined_penalty_total": 0.2,
                "caveat_codes": "none",
                "combined_explanation": "spike",
            }
        ]
    )
    trend = pd.DataFrame(
        [
            {
                "cik": 1,
                "period": "2021-Q1",
                "metric": "net_margin",
                "trend_signal_type": "strong_shift",
                "trend_score": 2.0,
                "consecutive_direction": "improving",
                "explanation": "up",
            }
        ]
    )
    uf = build_unified_findings(anomalies, trend_breaks=trend)
    out = build_deterioration_focus(uf)
    assert out.empty


def test_build_deterioration_focus_prioritizes_multi_period_deterioration() -> None:
    uf = pd.DataFrame(
        [
            {
                "finding_id": "a1",
                "finding_source": "anomaly",
                "finding_type": "combined",
                "cik": 1,
                "period": "2021-Q1",
                "metric": "net_margin",
                "direction": "deteriorating",
                "score_raw": 2.0,
                "score_adjusted": 1.8,
                "score_penalty": 0.2,
                "overlap_count": 1,
                "overlap_sources": "anomaly",
                "caveat_codes": "none",
                "explanation_summary": "",
                "provenance_artifacts": "anomalies_csv",
            },
            {
                "finding_id": "a2",
                "finding_source": "anomaly",
                "finding_type": "combined",
                "cik": 1,
                "period": "2021-Q2",
                "metric": "net_margin",
                "direction": "deteriorating",
                "score_raw": 2.0,
                "score_adjusted": 1.7,
                "score_penalty": 0.3,
                "overlap_count": 1,
                "overlap_sources": "anomaly",
                "caveat_codes": "none",
                "explanation_summary": "",
                "provenance_artifacts": "anomalies_csv",
            },
            {
                "finding_id": "a3",
                "finding_source": "anomaly",
                "finding_type": "peer_relative",
                "cik": 2,
                "period": "2021-Q1",
                "metric": "revenue_growth_qoq",
                "direction": "low",
                "score_raw": 3.0,
                "score_adjusted": 2.9,
                "score_penalty": 0.1,
                "overlap_count": 1,
                "overlap_sources": "anomaly",
                "caveat_codes": "none",
                "explanation_summary": "",
                "provenance_artifacts": "anomalies_csv",
            },
        ]
    )
    out = build_deterioration_focus(uf)
    assert len(out) == 3
    assert bool(out.iloc[0]["multi_period_stress"]) is True
    assert int(out.iloc[0]["deteriorating_period_count"]) == 2
    assert out.iloc[0]["deterioration_kind"] == "repeated_deterioration"
    assert int(out.iloc[0]["deterioration_priority_rank"]) == 1
    one_off = out[out["cik"] == 2].iloc[0]
    assert bool(one_off["one_off_anomaly_only"]) is True
    assert one_off["deterioration_axis"] == "revenue_growth"


def test_write_all_phase1_artifacts_writes_deterioration_focus(tmp_path) -> None:
    from src.pipeline_runner import write_all_phase1_artifacts
    from tests.test_metric_coverage import _minimal_panel

    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-deterioration",
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
    assert "deterioration_focus" in paths
    assert paths["deterioration_focus"].name == "deterioration_focus.csv"
    written = pd.read_csv(paths["deterioration_focus"])
    assert list(written.columns) == list(DETERIORATION_FOCUS_COLUMNS)
