"""Runtime traceability bundle (decision summaries, tools, critic caveats)."""

from __future__ import annotations

from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
    StepStatusEntry,
)

from backend.agents.traceability_summary import (
    TRACEABILITY_CONTRACT_VERSION,
    _blocking_caveats_from_critic_patch,
    build_runtime_traceability_bundle,
)


def test_blocking_caveats_skipped_critic() -> None:
    caveats, conf = _blocking_caveats_from_critic_patch(
        {"skipped": True, "reason": "llm_provider_unavailable"},
    )
    assert "llm_provider_unavailable" in caveats
    assert conf is None


def test_blocking_caveats_success_low_confidence() -> None:
    caveats, conf = _blocking_caveats_from_critic_patch(
        {
            "skipped": False,
            "result": {
                "findings_assessment": "a",
                "caveat_coverage": "b",
                "trustworthiness_notes": "c",
                "issues": ["gap in data"],
                "overall_confidence": "low",
            },
        },
    )
    assert conf == "low"
    assert any("low" in x for x in caveats)
    assert "gap in data" in caveats


def test_build_runtime_traceability_bundle_shape() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="End-to-end",
        user_goal_text="run all",
    )
    tools = [{"order": 0, "tool_name": "resolve_company", "label": "r"}]
    out = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=ig,
        step_statuses=[
            StepStatusEntry(order=0, tool_name="resolve_company", mcp_status="success", label="r"),
        ],
        artifact_paths={"panel_csv": "/tmp/panel.csv"},
    )
    critic_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "findings_assessment": "f",
            "caveat_coverage": "c",
            "trustworthiness_notes": "t",
            "issues": [],
            "overall_confidence": "high",
        },
    }
    report_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "user_report_markdown": "# Hi",
            "key_takeaways": ["One", "Two"],
        },
    }
    full, c_step, r_step = build_runtime_traceability_bundle(
        interpreted_goal=ig,
        planning_source="deterministic_rules",
        selected_tools=tools,
        orch_out=out,
        mcp_step_count=1,
        base_idx=1,
        critic_patch=critic_patch,
        report_patch=report_patch,
        critic_excerpt_roles=["unified_findings_csv"],
    )
    assert full["contract_version"] == TRACEABILITY_CONTRACT_VERSION
    assert full["planning"]["selected_tools"] == tools
    assert "resolve_company" in full["planning"]["decision_summary"]
    assert full["intent"]["planning_transparency"]["present"] is True
    assert full["planning"]["planning_transparency"]["present"] is True
    assert full["critic"]["plan_alignment_findings"] == []
    assert full["critic"]["plan_alignment_codes"] == []
    assert full["step_indices"]["critic"] == 1
    assert full["evidence_artifact_refs"][0]["role"] == "panel_csv"
    assert c_step["blocking_caveats"] == []
    assert r_step["key_takeaways_preview"]
