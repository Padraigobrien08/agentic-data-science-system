"""Derive lightweight run progress from persisted ``RunStep`` rows (no extra state tables)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.enums import AnalysisRunStatus, RunStepStatus
from backend.models.run_step import RunStep

# Aligns with frontend ``PIPELINE_PHASES`` ids (``frontend/src/lib/run-pipeline-phases.ts``).
PHASE_IDS: tuple[str, ...] = ("plan", "panels", "signals", "review", "report")

_STEP_TERMINAL: frozenset[RunStepStatus] = frozenset(
    {
        RunStepStatus.success,
        RunStepStatus.skipped,
        RunStepStatus.no_data,
        RunStepStatus.error,
    }
)


def _meta_trace(meta_json: dict | list | None) -> str:
    if not isinstance(meta_json, dict):
        return ""
    t = meta_json.get("trace")
    return t if isinstance(t, str) else ""


def classify_step_to_phase_index(step: RunStep) -> int:
    """Map a step row to a phase index 0–4 (same heuristics as the web client)."""
    raw = _meta_trace(step.meta_json)
    if raw == "report_agent":
        return 4
    if raw == "critic_agent":
        return 3
    if raw == "mcp_executor":
        return 1
    # stepLaneFromMeta maps mcp_executor → executor in TS; handle executor string if stored alone
    if raw == "executor":
        return 1
    lab = f"{step.label or ''} {step.planned_tool_name or ''}".lower()
    if "report" in lab:
        return 4
    if "critic" in lab:
        return 3
    if "mcp" in lab or "tool" in lab or "panel" in lab or "sec" in lab:
        return 1
    return 2


def _sort_steps(steps: list[RunStep]) -> list[RunStep]:
    return sorted(steps, key=lambda s: s.step_index)


def _find_active_step(sorted_steps: list[RunStep]) -> RunStep | None:
    for s in sorted_steps:
        if s.status in (RunStepStatus.running, RunStepStatus.pending):
            return s
    return None


def _find_failed_step(run_status: AnalysisRunStatus, sorted_steps: list[RunStep]) -> RunStep | None:
    if run_status == AnalysisRunStatus.error:
        for s in reversed(sorted_steps):
            if s.status == RunStepStatus.error:
                return s
    if run_status == AnalysisRunStatus.cancelled:
        for s in reversed(sorted_steps):
            if s.status == RunStepStatus.error:
                return s
    return None


def _terminal_success_run(run_status: AnalysisRunStatus) -> bool:
    return run_status in (
        AnalysisRunStatus.success,
        AnalysisRunStatus.partial_success,
        AnalysisRunStatus.no_data,
    )


def derive_current_phase_index(run_status: AnalysisRunStatus, steps: list[RunStep]) -> int:
    """Current pipeline phase index 0–4 (mirrors frontend ``deriveCurrentPhaseIndex``)."""
    sorted_steps = _sort_steps(steps)
    if run_status in (AnalysisRunStatus.pending, AnalysisRunStatus.queued):
        return 0
    if _terminal_success_run(run_status):
        return 4
    active = _find_active_step(sorted_steps)
    if active is not None:
        return classify_step_to_phase_index(active)
    if run_status == AnalysisRunStatus.running:
        if not sorted_steps:
            return 0
        last = sorted_steps[-1]
        if last.status in (
            RunStepStatus.success,
            RunStepStatus.skipped,
            RunStepStatus.no_data,
        ):
            last_phase = classify_step_to_phase_index(last)
            return min(last_phase + 1, 4)
        return classify_step_to_phase_index(last)
    if run_status in (AnalysisRunStatus.error, AnalysisRunStatus.cancelled):
        failed = _find_failed_step(run_status, sorted_steps)
        if failed is not None:
            return classify_step_to_phase_index(failed)
        return 0
    return 0


def derive_current_phase_str(run_status: AnalysisRunStatus, steps: list[RunStep]) -> str:
    """Stable API string for ``current_phase``."""
    sorted_steps = _sort_steps(steps)
    if run_status == AnalysisRunStatus.pending:
        return "not_started"
    if run_status == AnalysisRunStatus.queued:
        return "queued"
    if _terminal_success_run(run_status):
        return "completed"
    if run_status in (AnalysisRunStatus.error, AnalysisRunStatus.cancelled):
        failed = _find_failed_step(run_status, sorted_steps)
        if failed is not None:
            return PHASE_IDS[classify_step_to_phase_index(failed)]
        if run_status == AnalysisRunStatus.cancelled and not any(
            s.status == RunStepStatus.error for s in sorted_steps
        ):
            return "completed"
        return "unknown"
    idx = derive_current_phase_index(run_status, steps)
    if idx < 0 or idx >= len(PHASE_IDS):
        return "unknown"
    return PHASE_IDS[idx]


def count_step_progress(steps: list[RunStep]) -> tuple[int, int]:
    """Return ``(total_steps, completed_steps)`` where completed = terminal step outcomes."""
    total = len(steps)
    completed = sum(1 for s in steps if s.status in _STEP_TERMINAL)
    return total, completed


@dataclass(frozen=True)
class RunProgressPublic:
    """JSON-friendly progress slice attached to run summaries."""

    current_phase: str
    total_steps: int
    completed_steps: int


def derive_run_progress_public(run_status: AnalysisRunStatus, steps: list[RunStep]) -> RunProgressPublic:
    total, completed = count_step_progress(steps)
    phase = derive_current_phase_str(run_status, steps)
    return RunProgressPublic(current_phase=phase, total_steps=total, completed_steps=completed)
