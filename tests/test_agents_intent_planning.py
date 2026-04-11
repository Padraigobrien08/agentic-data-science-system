"""Intent + planning agents (stub LLM; no tool execution)."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.agents.prompt_loader import list_prompt_versions, load_agent_prompt
from backend.agents.runner import run_intent_planning_agents
from backend.config.settings import Settings
from backend.db.base import Base
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult
from backend.models.analysis_run import AnalysisRun as AnalysisRunRow
from backend.models.enums import AnalysisRunStatus
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.user import User


class _RoutingStubProvider:
    provider_id = "stub"

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        user = request.messages[-1]["content"]
        if "interpreted_goal" in user:
            body = {
                "steps": [
                    {
                        "order": 0,
                        "tool_name": "run_pipeline",
                        "tool_input": {"tickers": ["AAPL"], "refresh": False},
                        "label": "run_pipeline:0",
                    }
                ]
            }
        else:
            body = {
                "code": "full_pipeline",
                "intent": "full_pipeline_run",
                "description": "Full EDGAR pipeline",
                "user_goal_text": "run full analysis",
                "intent_rules_matched": ["test:stub"],
            }
        text = json.dumps(body)
        return ChatCompletionResult(
            model=request.model,
            assistant_text=text,
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=1,
            raw_response={"stub": True},
        )


@pytest.fixture
def session_with_run() -> tuple[Session, Settings, AnalysisRunRow]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    u = User(email=f"ag-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="AgProj")
    session.add(p)
    session.flush()
    arun = AnalysisRunRow(project_id=p.id, status=AnalysisRunStatus.pending)
    session.add(arun)
    session.flush()
    settings = Settings(
        agent_completion_model="stub-model",
        agent_intent_prompt_version="1.0.0",
        agent_planning_prompt_version="1.0.0",
    )
    return session, settings, arun


def test_load_versioned_prompts() -> None:
    assert "1.0.0" in list_prompt_versions("intent")
    t = load_agent_prompt("intent", "1.0.0")
    assert t.template_id == "intent"
    assert t.version == "1.0.0"
    rendered = render_check_intent(t.system_body)
    assert "{{ALLOWED_GOAL_CODES}}" not in rendered
    assert "full_pipeline" in rendered


def render_check_intent(body: str) -> str:
    from backend.agents.template_render import render_intent_prompt

    return render_intent_prompt(body)


def test_run_intent_planning_persists_calls_and_meta(session_with_run: tuple[Session, Settings, AnalysisRunRow]) -> None:
    session, settings, arun = session_with_run
    provider = _RoutingStubProvider()
    out = run_intent_planning_agents(
        session,
        provider,
        analysis_run_id=arun.id,
        user_request="run full analysis",
        tickers=["AAPL"],
        refresh=False,
        settings=settings,
    )
    session.commit()

    assert out.interpreted_goal.code.value == "full_pipeline"
    assert len(out.planned_steps) == 1
    assert out.planned_steps[0].tool_name == "run_pipeline"

    mcs = list(session.scalars(select(ModelCall).where(ModelCall.analysis_run_id == arun.id)).all())
    assert len(mcs) == 2
    roles = {m.request_payload_json.get("agent", {}).get("role") for m in mcs if m.request_payload_json}
    assert roles == {"intent", "planning"}

    session.refresh(arun)
    meta = arun.meta_json or {}
    ai = meta.get("ai_agents") or {}
    assert "intent" in ai and "planning" in ai
    assert ai["intent"]["interpreted_goal"]["code"] == "full_pipeline"
    assert len(ai["planning"]["steps"]) == 1
