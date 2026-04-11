"""LLM phase status helpers and run payload summaries."""

from __future__ import annotations

from backend.agents.llm_phase_status import (
    PHASE_FAILED,
    build_llm_phases_summary_payload,
    maybe_llm_error_summary_note,
)


def test_build_llm_phases_summary_payload() -> None:
    p = build_llm_phases_summary_payload(
        {
            "phase_status": PHASE_FAILED,
            "skipped": True,
            "reason": "critic_error",
            "error": "bad output",
            "model_call_id": "mc-1",
            "boundary_failure_class": "model_output_schema_invalid",
        },
        {"phase_status": "skipped", "skipped": True, "reason": "critic_phase_failed"},
    )
    assert p["critic"]["phase_status"] == PHASE_FAILED
    assert p["critic"]["model_call_id"] == "mc-1"
    assert p["report"]["reason"] == "critic_phase_failed"


def test_maybe_llm_error_summary_note_only_when_orch_clean() -> None:
    assert maybe_llm_error_summary_note([object()], {"critic": {"phase_status": PHASE_FAILED}}) is None
    note = maybe_llm_error_summary_note(
        [],
        {"critic": {"phase_status": PHASE_FAILED, "error_excerpt": "x" * 50}},
    )
    assert note and "x" in note
