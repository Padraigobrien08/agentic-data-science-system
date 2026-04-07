"""
Stdlib logging for Phase 3 orchestration.

Logger name: ``edgar_project.orchestration``. Enable with e.g.::

    logging.getLogger("edgar_project.orchestration").setLevel(logging.INFO)
"""

from __future__ import annotations

import logging

from edgar_project.orchestration.schemas import OrchestrationError, OrchestrationRunStatus, ToolResultSummary

logger = logging.getLogger("edgar_project.orchestration")


def tool_summary_line(ts: ToolResultSummary) -> str:
    """One-line MCP outcome for logs (no stack traces)."""
    parts = [f"mcp_status={ts.mcp_status}"]
    if ts.panel_row_count is not None:
        parts.append(f"panel_rows={ts.panel_row_count}")
    if ts.feature_row_count is not None:
        parts.append(f"feature_rows={ts.feature_row_count}")
    if ts.anomaly_count is not None:
        parts.append(f"anomaly_count={ts.anomaly_count}")
    if ts.report_character_count is not None:
        parts.append(f"report_chars={ts.report_character_count}")
    if ts.ciks_observed:
        parts.append(f"ciks={ts.ciks_observed}")
    if ts.artifact_paths:
        parts.append(f"artifact_roles={list(ts.artifact_paths.keys())}")
    return " ".join(parts)


def log_run_finished(
    run_id: str,
    *,
    status: OrchestrationRunStatus,
    message: str,
    errors: list[OrchestrationError],
    warnings_count: int,
    artifact_path_count: int,
) -> None:
    """Terminal line for a run; surfaces the first error without a traceback."""
    logger.info(
        "[%s] finished status=%s message=%r errors=%d warnings=%d merged_artifact_keys=%d",
        run_id,
        status.value,
        message,
        len(errors),
        warnings_count,
        artifact_path_count,
    )
    if errors:
        e0 = errors[0]
        logger.warning("[%s] primary_error code=%s message=%r", run_id, e0.code, e0.message)
