"""
Run intent then planning agents for an analysis run (LLM only — no MCP execution).

Persists:

* two :class:`~backend.models.model_call.ModelCall` rows (via :class:`~backend.services.recorded_chat_completion_service.RecordedChatCompletionService`)
* structured outputs under ``analysis_run.meta_json["ai_agents"]``
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from edgar_project.orchestration.schemas import InterpretedGoal, PlannedStep
from sqlalchemy.orm import Session

from backend.agents.ai_agents_meta import merge_ai_agents_meta
from backend.agents.intent_agent import IntentAgent
from backend.agents.planning_agent import PlanningAgent
from backend.config.settings import Settings, get_settings
from backend.llm.protocol import ChatCompletionProvider
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService


@dataclass(frozen=True)
class IntentPlanningAgentResult:
    interpreted_goal: InterpretedGoal
    planned_steps: list[PlannedStep]
    intent_model_call_id: UUID
    planning_model_call_id: UUID


def run_intent_planning_agents(
    session: Session,
    provider: ChatCompletionProvider,
    *,
    analysis_run_id: UUID,
    user_request: str,
    tickers: list[str],
    refresh: bool,
    settings: Settings | None = None,
) -> IntentPlanningAgentResult:
    """
    Execute intent agent, persist output, then planning agent, persist output.

    Caller commits the session.
    """
    s = settings if settings is not None else get_settings()
    recorder = RecordedChatCompletionService(session, provider)

    ig, mc_i = IntentAgent(recorder, settings=s).run(
        analysis_run_id=analysis_run_id,
        user_request=user_request,
        tickers=tickers,
        refresh=refresh,
    )
    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "intent",
        {
            "model_call_id": str(mc_i.id),
            "interpreted_goal": ig.model_dump(mode="json"),
        },
    )
    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "prompt_versions",
        {
            "intent": s.agent_intent_prompt_version,
            "planning": s.agent_planning_prompt_version,
        },
    )

    steps, mc_p = PlanningAgent(recorder, settings=s).run(
        analysis_run_id=analysis_run_id,
        interpreted_goal=ig,
        user_request=user_request,
        tickers=tickers,
        refresh=refresh,
    )
    merge_ai_agents_meta(
        session,
        analysis_run_id,
        "planning",
        {
            "model_call_id": str(mc_p.id),
            "steps": [st.model_dump(mode="json") for st in steps],
        },
    )

    return IntentPlanningAgentResult(
        interpreted_goal=ig,
        planned_steps=steps,
        intent_model_call_id=mc_i.id,
        planning_model_call_id=mc_p.id,
    )
