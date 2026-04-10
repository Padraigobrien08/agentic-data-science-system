"""Allowed status transitions for analysis runs and run steps."""

from __future__ import annotations

from backend.models.enums import AnalysisRunStatus, RunStepStatus, ToolCallMcpStatus

_ANALYSIS_RUN_ALLOWED: dict[AnalysisRunStatus, frozenset[AnalysisRunStatus]] = {
    AnalysisRunStatus.pending: frozenset(
        {AnalysisRunStatus.running, AnalysisRunStatus.cancelled}
    ),
    AnalysisRunStatus.running: frozenset(
        {
            AnalysisRunStatus.success,
            AnalysisRunStatus.partial_success,
            AnalysisRunStatus.no_data,
            AnalysisRunStatus.error,
            AnalysisRunStatus.cancelled,
        }
    ),
}

_ANALYSIS_RUN_TERMINAL: frozenset[AnalysisRunStatus] = frozenset(
    {
        AnalysisRunStatus.success,
        AnalysisRunStatus.partial_success,
        AnalysisRunStatus.no_data,
        AnalysisRunStatus.error,
        AnalysisRunStatus.cancelled,
    }
)

_RUN_STEP_ALLOWED: dict[RunStepStatus, frozenset[RunStepStatus]] = {
    RunStepStatus.pending: frozenset({RunStepStatus.running, RunStepStatus.skipped}),
    RunStepStatus.running: frozenset(
        {
            RunStepStatus.success,
            RunStepStatus.no_data,
            RunStepStatus.error,
            RunStepStatus.skipped,
        }
    ),
}

_RUN_STEP_TERMINAL: frozenset[RunStepStatus] = frozenset(
    {
        RunStepStatus.success,
        RunStepStatus.skipped,
        RunStepStatus.no_data,
        RunStepStatus.error,
    }
)


def can_transition_analysis_run(
    current: AnalysisRunStatus,
    target: AnalysisRunStatus,
) -> bool:
    if current == target:
        return True
    if current in _ANALYSIS_RUN_TERMINAL:
        return False
    allowed = _ANALYSIS_RUN_ALLOWED.get(current)
    return allowed is not None and target in allowed


def can_transition_run_step(current: RunStepStatus, target: RunStepStatus) -> bool:
    if current == target:
        return True
    if current in _RUN_STEP_TERMINAL:
        return False
    allowed = _RUN_STEP_ALLOWED.get(current)
    return allowed is not None and target in allowed


def is_terminal_analysis_run(status: AnalysisRunStatus) -> bool:
    return status in _ANALYSIS_RUN_TERMINAL


def is_terminal_run_step(status: RunStepStatus) -> bool:
    return status in _RUN_STEP_TERMINAL


def can_transition_tool_mcp_status(
    current: ToolCallMcpStatus,
    target: ToolCallMcpStatus,
    *,
    finalized: bool,
    allow_rewrite: bool,
) -> bool:
    """
    MCP statuses are all terminal in the wire protocol.

    * finalized — ``response_envelope_json`` is already set (first completion done).
    * allow_rewrite — permit changing status/response when re-ingesting.
    """
    if not finalized:
        return True
    if allow_rewrite:
        return target in frozenset(ToolCallMcpStatus)
    return current == target
