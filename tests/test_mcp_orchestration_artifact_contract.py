"""Stable exposure of Phase 1 artifact role keys through MCP schemas and executor merge (no I/O)."""

from __future__ import annotations

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_CACHE_COMPANYFACTS,
    ARTIFACT_KEY_CACHE_SUBMISSIONS,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_MANUAL_VALIDATION,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_REPORT,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.executor import _merge_artifact_paths

# Analytical / credibility outputs added alongside core Phase 1 CSVs (explicit registry for drift detection).
PHASE1_ANALYTICAL_ARTIFACT_KEYS = frozenset(
    {
        ARTIFACT_KEY_DATA_QUALITY,
        ARTIFACT_KEY_EXCLUSIONS,
        ARTIFACT_KEY_PEER_SIGNALS,
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
                "extra_role": {"path": "/tmp/extra.csv"},
            },
            "report": {"path": "/tmp/report.md"},
        },
        artifacts={
            ARTIFACT_KEY_PANEL: "/p/panel.csv",
            ARTIFACT_KEY_FEATURES: "/p/features.csv",
            ARTIFACT_KEY_ANOMALIES: "/p/anomalies.csv",
            ARTIFACT_KEY_DATA_QUALITY: "/p/data_quality_summary.csv",
            ARTIFACT_KEY_EXCLUSIONS: "/p/exclusions_summary.csv",
            ARTIFACT_KEY_PEER_SIGNALS: "/p/peer_signals.csv",
            ARTIFACT_KEY_MANUAL_VALIDATION: "/p/manual_validation.csv",
        },
        errors=[],
    )
    accum: dict[str, str] = {}
    _merge_artifact_paths(accum, env)
    assert accum[ARTIFACT_KEY_PANEL] == "/p/panel.csv"
    assert accum[ARTIFACT_KEY_DATA_QUALITY] == "/p/data_quality_summary.csv"
    assert accum[ARTIFACT_KEY_EXCLUSIONS] == "/p/exclusions_summary.csv"
    assert accum[ARTIFACT_KEY_PEER_SIGNALS] == "/p/peer_signals.csv"
    assert accum[ARTIFACT_KEY_MANUAL_VALIDATION] == "/p/manual_validation.csv"
    assert accum["extra_role"] == "/tmp/extra.csv"
    assert accum[ARTIFACT_KEY_REPORT] == "/tmp/report.md"


def test_cache_artifact_keys_remain_available_for_fetch_tools() -> None:
    """Cache keys stay defined alongside pipeline artifacts (contract surface)."""
    assert ARTIFACT_KEY_CACHE_SUBMISSIONS.endswith("_json")
    assert ARTIFACT_KEY_CACHE_COMPANYFACTS.endswith("_json")
