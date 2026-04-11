"""Traceable EDGAR pipeline: MCP ``RunStep`` / ``ToolCall`` persistence and LLM phases."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.agents.traceable_analysis_pipeline import run_traceable_edgar_pipeline
from backend.db.base import Base
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult
from backend.models.analysis_run import AnalysisRun as AnalysisRunRow
from backend.models.enums import AnalysisRunStatus, RunStepStatus
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.run_step import RunStep
from backend.models.tool_call import ToolCall
from backend.models.user import User
from edgar_project.mcp.schemas import ToolResponseEnvelope, ToolStatus
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationPlan,
    OrchestrationRunStatus,
    PlannedStep,
    StepRecord,
    StepStatusEntry,
    ToolResultSummary,
)
from edgar_project.orchestration.state import OrchestrationRunState


@pytest.fixture
def session_with_run() -> tuple[Session, AnalysisRunRow]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    u = User(email=f"tp-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="TpProj")
    session.add(p)
    session.flush()
    arun = AnalysisRunRow(
        project_id=p.id,
        status=AnalysisRunStatus.pending,
        input_payload_json={"tickers": ["AAPL"], "analysis_goal": "test", "refresh": False},
    )
    session.add(arun)
    session.flush()
    return session, arun


def _minimal_orch_bundle() -> tuple[OrchestrationOutput, OrchestrationRunState]:
    inp = OrchestrationInput(tickers=["AAPL"], analysis_goal="test goal", refresh=False)
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="test",
        user_goal_text="test goal",
    )
    env = ToolResponseEnvelope(status=ToolStatus.success, message="ok")
    rec0 = StepRecord(
        tool_name="resolve_company",
        order=0,
        envelope=env.model_dump(mode="json"),
    )
    plan = OrchestrationPlan(
        steps=[
            PlannedStep(order=0, tool_name="resolve_company", tool_input={"ticker": "AAPL"}, label="r"),
            PlannedStep(order=1, tool_name="run_pipeline", tool_input={"tickers": ["AAPL"]}, label="p"),
        ]
    )
    state = OrchestrationRunState(request=inp, plan=plan, interpreted_goal=ig)
    state.steps_completed.append(rec0)

    out = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="done",
        interpreted_goal=ig,
        step_statuses=[
            StepStatusEntry(order=0, tool_name="resolve_company", mcp_status="success", label="r"),
            StepStatusEntry(order=1, tool_name="run_pipeline", mcp_status="skipped", detail="short-circuit"),
        ],
        tool_results_summary=[
            ToolResultSummary(order=0, tool_name="resolve_company", mcp_status="success"),
        ],
    )
    return out, state


def test_traceable_persists_mcp_skipped_and_llm_run_steps_without_llm(
    session_with_run: tuple[Session, AnalysisRunRow],
) -> None:
    session, arun = session_with_run
    inp = OrchestrationInput(tickers=["AAPL"], analysis_goal="test goal", refresh=False)
    out, state = _minimal_orch_bundle()

    def _coord(_: OrchestrationInput) -> tuple[OrchestrationOutput, OrchestrationRunState | None]:
        return out, state

    from backend.config.settings import Settings

    settings = Settings(
        agent_completion_model="stub",
        agent_critic_prompt_version="1.0.0",
        agent_report_prompt_version="1.0.0",
    )
    traced = run_traceable_edgar_pipeline(
        session,
        arun.id,
        inp,
        llm_provider=None,
        coordinator=_coord,
        settings=settings,
    )
    assert traced.orchestration_output.status == OrchestrationRunStatus.success

    steps = list(
        session.scalars(
            select(RunStep).where(RunStep.analysis_run_id == arun.id).order_by(RunStep.step_index)
        ).all()
    )
    assert len(steps) == 4
    assert steps[0].planned_tool_name == "resolve_company"
    assert steps[0].status == RunStepStatus.success
    assert steps[1].status == RunStepStatus.skipped
    assert steps[2].label == "critic_agent"
    assert steps[2].status == RunStepStatus.skipped
    assert steps[3].label == "report_agent"
    assert steps[3].status == RunStepStatus.skipped

    tcs = list(session.scalars(select(ToolCall).where(ToolCall.analysis_run_id == arun.id)).all())
    assert len(tcs) == 1
    assert tcs[0].tool_name == "resolve_company"

    session.refresh(arun)
    meta = arun.meta_json if isinstance(arun.meta_json, dict) else {}
    ai = meta.get("ai_agents") or {}
    assert ai["critic"]["phase_status"] == "skipped"
    assert ai["critic"]["boundary_failure_class"] == "llm_not_configured"
    assert ai["report"]["boundary_failure_class"] == "llm_not_configured"
    assert steps[2].meta_json.get("boundary_failure_class") == "llm_not_configured"
    assert steps[3].meta_json.get("boundary_failure_class") == "llm_not_configured"
    assert ai["intent"]["phase_output"]["goal_code"] == "full_pipeline"
    tr = ai.get("traceability") or {}
    assert tr.get("contract_version") == "1"
    assert len(tr.get("planning", {}).get("selected_tools", [])) == 2
    assert tr["step_indices"]["critic"] == 2
    assert steps[2].meta_json.get("traceability", {}).get("traceability_doc")
    assert ai["planning"]["phase_output"]["step_count"] == 2
    assert len(ai["planning"]["steps"]) == 2


class _CriticReportStubProvider:
    provider_id = "stub"

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        user = request.messages[-1]["content"]
        if "artifact_excerpts_by_role" in user:
            body: dict[str, Any] = {
                "findings_assessment": "Adequate for the goal.",
                "caveat_coverage": "Caveats visible.",
                "trustworthiness_notes": "No major gaps.",
                "issues": [],
                "overall_confidence": "medium",
            }
        else:
            body = {
                "user_report_markdown": "# Analysis\n\nThis is the user-facing summary.",
                "key_takeaways": ["Takeaway one"],
            }
        text = json.dumps(body)
        return ChatCompletionResult(
            model=request.model,
            assistant_text=text,
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=10,
            latency_ms=1,
            raw_response={"stub": True},
        )


def test_traceable_critic_and_report_with_stub_llm(
    session_with_run: tuple[Session, AnalysisRunRow],
) -> None:
    session, arun = session_with_run
    inp = OrchestrationInput(tickers=["AAPL"], analysis_goal="test goal", refresh=False)
    out, state = _minimal_orch_bundle()

    def _coord(_: OrchestrationInput) -> tuple[OrchestrationOutput, OrchestrationRunState | None]:
        return out, state

    from backend.config.settings import Settings

    settings = Settings(
        agent_completion_model="stub",
        agent_critic_prompt_version="1.0.0",
        agent_report_prompt_version="1.0.0",
    )
    traced = run_traceable_edgar_pipeline(
        session,
        arun.id,
        inp,
        llm_provider=_CriticReportStubProvider(),
        coordinator=_coord,
        settings=settings,
    )
    from backend.services.analysis_run_service import AnalysisRunService

    run_svc = AnalysisRunService(session)
    run_svc.set_output_payload(arun.id, traced.orchestration_output.model_dump(mode="json"))
    if traced.output_payload_patch:
        run_svc.merge_output_payload(arun.id, traced.output_payload_patch)
    session.commit()

    row = session.get(AnalysisRunRow, arun.id)
    assert row is not None
    meta = row.meta_json if isinstance(row.meta_json, dict) else {}
    ai = meta.get("ai_agents") or {}
    assert ai.get("critic", {}).get("skipped") is False
    assert ai.get("report", {}).get("skipped") is False
    assert ai["critic"]["phase_output"]["issue_count"] == 0
    assert "markdown_preview" in ai["report"]["phase_output"]
    tr2 = ai.get("traceability") or {}
    assert ai["critic"]["phase_status"] in ("success", "degraded")
    assert ai["report"]["phase_status"] == "success"
    opl = row.output_payload_json if isinstance(row.output_payload_json, dict) else {}
    assert opl.get("llm_phases_summary", {}).get("critic", {}).get("phase_status") in ("success", "degraded")
    assert tr2["critic"]["ran"] is True
    assert tr2["report"]["ran"] is True
    assert tr2["report"]["key_takeaways_preview"]

    out_json = row.output_payload_json if isinstance(row.output_payload_json, dict) else {}
    ufr = out_json.get("user_facing_report") or {}
    assert "Analysis" in ufr.get("markdown", "")

    steps = list(
        session.scalars(
            select(RunStep).where(RunStep.analysis_run_id == arun.id).order_by(RunStep.step_index)
        ).all()
    )
    assert steps[2].status == RunStepStatus.success
    assert steps[3].status == RunStepStatus.success
    assert steps[2].meta_json and steps[2].meta_json.get("phase_output", {}).get("overall_confidence")
    assert steps[3].meta_json and steps[3].meta_json.get("phase_output", {}).get("artifact_refs") is not None

    mcs = list(session.scalars(select(ModelCall).where(ModelCall.analysis_run_id == arun.id)).all())
    assert len(mcs) == 2
    roles = {m.request_payload_json.get("agent", {}).get("role") for m in mcs}
    assert roles == {"critic", "report"}
    assert {m.prompt_id for m in mcs} == {"edgar.agent.critic", "edgar.agent.report"}
    assert all(m.prompt_version == "1.0.0" for m in mcs)
    assert all(m.provider == "stub" and m.model_name == "stub" for m in mcs)
