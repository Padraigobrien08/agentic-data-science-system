"""Unit tests for ``backend.domain.run_progress`` (no HTTP)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.domain.run_progress import (
    classify_step_to_phase_index,
    count_step_progress,
    derive_current_phase_str,
    derive_run_progress_public,
)
from backend.models.enums import AnalysisRunStatus, RunStepStatus


def _step(
    *,
    idx: int,
    status: RunStepStatus,
    meta: dict | None = None,
    label: str | None = None,
    tool: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        step_index=idx,
        status=status,
        meta_json=meta,
        label=label,
        planned_tool_name=tool,
        analysis_run_id=uuid4(),
    )


def test_classify_mcp_critic_report() -> None:
    mcp = _step(idx=0, status=RunStepStatus.running, meta={"trace": "mcp_executor"})
    assert classify_step_to_phase_index(mcp) == 1
    cr = _step(idx=1, status=RunStepStatus.pending, meta={"trace": "critic_agent", "phase": "llm"})
    assert classify_step_to_phase_index(cr) == 3
    rp = _step(idx=2, status=RunStepStatus.pending, meta={"trace": "report_agent", "phase": "llm"})
    assert classify_step_to_phase_index(rp) == 4


def test_count_step_progress() -> None:
    steps = [
        _step(idx=0, status=RunStepStatus.success, meta={"trace": "mcp_executor"}),
        _step(idx=1, status=RunStepStatus.running, meta={"trace": "mcp_executor"}),
    ]
    total, done = count_step_progress(steps)
    assert total == 2
    assert done == 1


@pytest.mark.parametrize(
    ("run_status", "expected_phase"),
    [
        (AnalysisRunStatus.pending, "not_started"),
        (AnalysisRunStatus.queued, "queued"),
        (AnalysisRunStatus.success, "completed"),
    ],
)
def test_phase_terminal_and_queue(run_status: AnalysisRunStatus, expected_phase: str) -> None:
    assert derive_current_phase_str(run_status, []) == expected_phase


def test_running_mcp_active_is_panels() -> None:
    steps = [
        _step(idx=0, status=RunStepStatus.success, meta={"trace": "mcp_executor"}),
        _step(idx=1, status=RunStepStatus.running, meta={"trace": "mcp_executor"}),
    ]
    assert derive_current_phase_str(AnalysisRunStatus.running, steps) == "panels"


def test_derive_run_progress_public() -> None:
    p = derive_run_progress_public(
        AnalysisRunStatus.running,
        [
            _step(idx=0, status=RunStepStatus.success, meta={"trace": "mcp_executor"}),
            _step(idx=1, status=RunStepStatus.running, meta={"trace": "mcp_executor"}),
        ],
    )
    assert p.total_steps == 2
    assert p.completed_steps == 1
    assert p.current_phase == "panels"
