"""Stable exposure of Phase 1 artifact role keys through MCP schemas and executor merge (no I/O)."""

from __future__ import annotations

from unittest.mock import patch

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_CACHE_COMPANYFACTS,
    ARTIFACT_KEY_CACHE_SUBMISSIONS,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_MANUAL_VALIDATION,
    ARTIFACT_KEY_TREND_BREAKS,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
    ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_REPORT,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.constants import TOOL_GENERATE_REPORT
from edgar_project.orchestration.executor import _dispatch_mcp, _merge_artifact_paths
from edgar_project.orchestration.schemas import PlannedStep, RunWorkspacePayload

# Analytical / credibility outputs added alongside core Phase 1 CSVs (explicit registry for drift detection).
PHASE1_ANALYTICAL_ARTIFACT_KEYS = frozenset(
    {
        ARTIFACT_KEY_DATA_QUALITY,
        ARTIFACT_KEY_EXCLUSIONS,
        ARTIFACT_KEY_PEER_SIGNALS,
        ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
        ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
        ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
        ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
        ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
        ARTIFACT_KEY_TREND_BREAKS,
        ARTIFACT_KEY_UNIFIED_FINDINGS,
        ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
        ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
        ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
        ARTIFACT_KEY_MANUAL_VALIDATION,
    }
)


def test_phase1_analytical_artifact_keys_are_distinct_strings() -> None:
    assert len(PHASE1_ANALYTICAL_ARTIFACT_KEYS) == len({str(k) for k in PHASE1_ANALYTICAL_ARTIFACT_KEYS})
    assert all(str(k).endswith("_csv") for k in PHASE1_ANALYTICAL_ARTIFACT_KEYS)


def test_merge_artifact_paths_accumulates_mcp_artifacts_and_optional_data_paths() -> None:
    env = ToolResponseEnvelope(
        status=ToolStatus.success,
        message="ok",
        data={
            "artifacts_detail": {
                "extra_role": {"path": "/runs/run-123/artifacts/extra.csv"},
            },
            "report": {"path": "/runs/run-123/artifacts/report.md"},
        },
        artifacts={
            ARTIFACT_KEY_PANEL: "/runs/run-123/processed/panel.csv",
            ARTIFACT_KEY_FEATURES: "/runs/run-123/processed/features.csv",
            ARTIFACT_KEY_ANOMALIES: "/runs/run-123/artifacts/anomalies.csv",
            ARTIFACT_KEY_DATA_QUALITY: "/runs/run-123/artifacts/data_quality_summary.csv",
            ARTIFACT_KEY_EXCLUSIONS: "/runs/run-123/artifacts/exclusions_summary.csv",
            ARTIFACT_KEY_PEER_SIGNALS: "/runs/run-123/artifacts/peer_signals.csv",
            ARTIFACT_KEY_TREND_BREAKS: "/runs/run-123/artifacts/trend_break_signals.csv",
            ARTIFACT_KEY_UNIFIED_FINDINGS: "/runs/run-123/artifacts/unified_findings.csv",
            ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY: "/runs/run-123/artifacts/findings_summary_by_company.csv",
            ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC: "/runs/run-123/artifacts/findings_summary_by_metric.csv",
            ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD: "/runs/run-123/artifacts/findings_summary_by_period.csv",
            ARTIFACT_KEY_MANUAL_VALIDATION: "/repo/validation/manual_validation.csv",
        },
        errors=[],
    )
    accum: dict[str, str] = {}
    _merge_artifact_paths(accum, env)
    assert accum[ARTIFACT_KEY_PANEL] == "/runs/run-123/processed/panel.csv"
    assert accum[ARTIFACT_KEY_DATA_QUALITY] == "/runs/run-123/artifacts/data_quality_summary.csv"
    assert accum[ARTIFACT_KEY_EXCLUSIONS] == "/runs/run-123/artifacts/exclusions_summary.csv"
    assert accum[ARTIFACT_KEY_PEER_SIGNALS] == "/runs/run-123/artifacts/peer_signals.csv"
    assert accum[ARTIFACT_KEY_TREND_BREAKS] == "/runs/run-123/artifacts/trend_break_signals.csv"
    assert accum[ARTIFACT_KEY_UNIFIED_FINDINGS] == "/runs/run-123/artifacts/unified_findings.csv"
    assert accum[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] == "/runs/run-123/artifacts/findings_summary_by_company.csv"
    assert accum[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] == "/runs/run-123/artifacts/findings_summary_by_metric.csv"
    assert accum[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] == "/runs/run-123/artifacts/findings_summary_by_period.csv"
    assert accum[ARTIFACT_KEY_MANUAL_VALIDATION] == "/repo/validation/manual_validation.csv"
    assert accum["extra_role"] == "/runs/run-123/artifacts/extra.csv"
    assert accum[ARTIFACT_KEY_REPORT] == "/runs/run-123/artifacts/report.md"


def test_cache_artifact_keys_remain_available_for_fetch_tools() -> None:
    """Cache keys stay defined alongside pipeline artifacts (contract surface)."""
    assert ARTIFACT_KEY_CACHE_SUBMISSIONS.endswith("_json")
    assert ARTIFACT_KEY_CACHE_COMPANYFACTS.endswith("_json")


def test_dispatch_mcp_injects_upstream_artifact_paths_and_workspace() -> None:
    workspace = RunWorkspacePayload(
        run_scoped_id="run-123",
        root="/runs/run-123",
        processed_dir="/runs/run-123/processed",
        artifacts_dir="/runs/run-123/artifacts",
        manual_validation_csv="/repo/validation/manual_validation.csv",
        use_legacy_shared_paths=False,
    )
    step = PlannedStep(
        order=5,
        tool_name=TOOL_GENERATE_REPORT,
        tool_input={
            "features_csv_path": None,
            "anomalies_csv_path": None,
            "use_default_artifact_paths": False,
        },
        label="generate_report:explicit_paths",
    )
    env = ToolResponseEnvelope(
        status=ToolStatus.success,
        message="ok",
        data={},
        artifacts={ARTIFACT_KEY_REPORT: "/runs/run-123/artifacts/report.md"},
        errors=[],
    )
    with patch(
        "edgar_project.orchestration.executor.mcp_tools.generate_report_tool",
        return_value=env,
    ) as mock_tool:
        _dispatch_mcp(
            step,
            artifact_paths={
                ARTIFACT_KEY_FEATURES: "/runs/run-123/processed/features.csv",
                ARTIFACT_KEY_ANOMALIES: "/runs/run-123/artifacts/anomalies.csv",
            },
            run_workspace=workspace,
        )

    dispatched_input = mock_tool.call_args.args[0]
    assert dispatched_input.features_csv_path == "/runs/run-123/processed/features.csv"
    assert dispatched_input.anomalies_csv_path == "/runs/run-123/artifacts/anomalies.csv"
    assert dispatched_input.run_workspace.run_scoped_id == "run-123"
    assert dispatched_input.run_workspace.manual_validation_csv == "/repo/validation/manual_validation.csv"
