"""Lightweight contracts for trustworthiness paths (Phase 1 + MCP merge), no network."""

from __future__ import annotations

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
    ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.executor import _merge_artifact_paths


def test_phase1_paths_include_metric_coverage_and_caveat_basenames() -> None:
    from src.pipeline_runner import phase1_paths

    p = phase1_paths()
    assert p["metric_coverage_summary"].name == "metric_coverage_summary.csv"
    assert p["metric_caveats_extraction"].name == "metric_caveats_extraction.csv"
    assert p["metric_caveats_panel"].name == "metric_caveats_panel.csv"
    assert p["deterioration_focus"].name == "deterioration_focus.csv"
    assert "manual_validation" in p


def test_merge_artifact_paths_surfaces_trustworthiness_roles() -> None:
    """Executor merge passes through MCP ``artifacts`` role keys for downstream consumers."""
    env = ToolResponseEnvelope(
        status=ToolStatus.success,
        message="ok",
        data={},
        artifacts={
            ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY: "/a/metric_coverage_summary.csv",
            ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY: "/a/metric_coverage_by_company.csv",
            ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD: "/a/metric_coverage_by_period.csv",
            ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION: "/a/metric_caveats_extraction.csv",
            ARTIFACT_KEY_METRIC_CAVEATS_PANEL: "/a/metric_caveats_panel.csv",
        },
        errors=[],
    )
    accum: dict[str, str] = {}
    _merge_artifact_paths(accum, env)
    assert accum[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY].endswith("metric_coverage_summary.csv")
    assert accum[ARTIFACT_KEY_METRIC_CAVEATS_PANEL].endswith("metric_caveats_panel.csv")
