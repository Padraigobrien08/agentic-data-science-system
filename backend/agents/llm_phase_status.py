"""
Explicit LLM phase outcomes for runs (distinct from :class:`~backend.models.enums.RunStepStatus`).

* ``skipped`` — phase intentionally not executed (config, dependency).
* ``failed`` — phase attempted and did not yield usable output.
* ``success`` — phase produced validated output.
* ``degraded`` — validated output with low-trust signal (e.g. critic confidence low).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.agents.prompt_registry import AGENT_PROMPT_IDS
from backend.models.model_call import ModelCall

PHASE_SKIPPED = "skipped"
PHASE_FAILED = "failed"
PHASE_SUCCESS = "success"
PHASE_DEGRADED = "degraded"


def latest_model_call_for_agent_prompt(
    session: Session,
    analysis_run_id: UUID,
    *,
    prompt_id: str,
) -> ModelCall | None:
    """Most recent model call row for this run and agent prompt (for failed-phase trace linking)."""
    return session.scalar(
        select(ModelCall)
        .where(
            ModelCall.analysis_run_id == analysis_run_id,
            ModelCall.prompt_id == prompt_id,
        )
        .order_by(ModelCall.created_at.desc())
        .limit(1)
    )


def build_llm_phases_summary_payload(
    critic_patch: dict[str, Any],
    report_patch: dict[str, Any],
) -> dict[str, Any]:
    """Structured summary merged into ``output_payload_json`` for API/UI consumers."""
    return {
        "contract_version": "1",
        "critic": {
            "phase_status": critic_patch.get("phase_status"),
            "skipped": critic_patch.get("skipped"),
            "reason": critic_patch.get("reason"),
            "error_excerpt": _clip(critic_patch.get("error"), 400),
            "model_call_id": critic_patch.get("model_call_id"),
            "degraded": bool(critic_patch.get("degraded")),
            "boundary_failure_class": critic_patch.get("boundary_failure_class"),
        },
        "report": {
            "phase_status": report_patch.get("phase_status"),
            "skipped": report_patch.get("skipped"),
            "reason": report_patch.get("reason"),
            "error_excerpt": _clip(report_patch.get("error"), 400),
            "model_call_id": report_patch.get("model_call_id"),
            "boundary_failure_class": report_patch.get("boundary_failure_class"),
        },
    }


def _clip(text: Any, max_len: int) -> str | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def maybe_llm_error_summary_note(
    orchestration_errors: list[Any],
    llm_summary: dict[str, Any],
) -> str | None:
    """
    One-line note when orchestration produced no errors but an LLM phase failed.

    Does not replace MCP/orchestration error summaries.
    """
    if orchestration_errors:
        return None
    c = llm_summary.get("critic") or {}
    r = llm_summary.get("report") or {}
    if c.get("phase_status") == PHASE_FAILED:
        return _clip(c.get("error_excerpt") or "critic phase failed", 512) or "Critic phase failed."
    if r.get("phase_status") == PHASE_FAILED:
        return _clip(r.get("error_excerpt") or "report phase failed", 512) or "Report phase failed."
    return None
