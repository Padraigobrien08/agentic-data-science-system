"""Context budget enforcement (deterministic truncation + metadata)."""

from __future__ import annotations

from backend.agents.context_budget import ContextBudget, clip_critic_for_report_llm, clip_sorted_role_list
from backend.agents.llm_context import build_report_llm_context
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationRunStatus,
)


def test_clip_sorted_role_list_head_stable() -> None:
    roles = ["z", "a", "m"]
    out, meta = clip_sorted_role_list(roles, 2)
    assert out == ["a", "m"]
    assert meta["truncated"] is True
    assert meta["omitted_count"] == 1


def test_clip_sorted_role_list_unlimited() -> None:
    out, meta = clip_sorted_role_list(["b", "a"], 0)
    assert out == ["a", "b"]
    assert meta["truncated"] is False


def test_clip_critic_issues_and_strings() -> None:
    b = ContextBudget(max_critic_issue_items=2, max_critic_text_field_chars=10)
    critic = {
        "issues": ["a", "b", "c"],
        "findings_assessment": "x" * 20,
        "caveat_coverage": "ok",
        "trustworthiness_notes": "ok",
        "overall_confidence": "high",
    }
    clipped, meta = clip_critic_for_report_llm(critic, b)
    assert len(clipped["issues"]) == 2
    assert meta["truncated"] is True
    assert meta["issues_omitted_count"] == 1
    assert str(clipped["findings_assessment"]).endswith("…")


def test_report_llm_context_budget_flags() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="d",
        user_goal_text="g",
    )
    orch = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="m",
        interpreted_goal=ig,
    )
    inp = OrchestrationInput(tickers=["A"], analysis_goal="goal", refresh=False)
    summaries = {
        "contract_version": "artifact_summaries_v1",
        "by_role": {},
        "artifact_index": [],
        "context_budget": {"truncated": False, "artifact_roles_omitted": [], "artifact_index_truncated": False},
    }
    b = ContextBudget(max_coverage_roles=1)
    r = build_report_llm_context(
        orch=orch,
        orch_input=inp,
        critic={"overall_confidence": "high", "issues": ["i"]},
        artifact_summaries=summaries,
        paths_roles=["r1", "r2"],
        summary_roles_loaded=["s1", "s2"],
        budget=b,
    )
    assert len(r["artifact_coverage"]["artifact_paths_roles"]) == 1
    assert r["llm_context_budget"]["artifact_paths_roles_truncated"] is True
