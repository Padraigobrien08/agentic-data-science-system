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
