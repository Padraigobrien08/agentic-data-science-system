"""LLM planning agent — produces :class:`~edgar_project.orchestration.schemas.PlannedStep` list (no tools)."""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import ValidationError

from backend.agents.context_budget import ContextBudget
from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.llm_context import build_planning_llm_context
from backend.agents.llm_plan_handoff import validate_llm_planned_steps_for_handoff
from backend.agents.model_routing import resolve_agent_completion_model
from backend.agents.output_schemas import PlanningAgentLLMOutput
from backend.agents.prompt_registry import load_registered_prompt
from backend.agents.template_render import render_planning_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.types import ChatCompletionRequest
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService
from edgar_project.orchestration.schemas import InterpretedGoal, PlannedStep


class PlanningAgent:
    def __init__(
        self,
        recorder: RecordedChatCompletionService,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._rec = recorder
        self._settings = settings if settings is not None else get_settings()

    def run(
        self,
        *,
        analysis_run_id: UUID,
        interpreted_goal: InterpretedGoal,
        user_request: str,
        tickers: list[str],
        refresh: bool,
    ) -> tuple[list[PlannedStep], ModelCall]:
        reg = load_registered_prompt("planning", self._settings.agent_planning_prompt_version)
        tmpl = reg.template
        system = render_planning_prompt(tmpl.system_body)
        user_payload = build_planning_llm_context(
            interpreted_goal=interpreted_goal,
            user_request=user_request,
            tickers=tickers,
            refresh=refresh,
            budget=ContextBudget.from_settings(self._settings),
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        model_id, routing_src = resolve_agent_completion_model(self._settings, "planning")
        req = ChatCompletionRequest(
            model=model_id,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "planning",
            "phase": "planning",
            "completion_model_routing_source": routing_src,
            "prompt_id": reg.prompt_id,
            "prompt_version": reg.prompt_version,
            "template_path": tmpl.source_uri,
        }
        model_call, result = self._rec.complete_and_persist(
            req,
            analysis_run_id=analysis_run_id,
            request_metadata=meta,
            prompt_id=reg.prompt_id,
            prompt_version=reg.prompt_version,
        )
        text = (result.assistant_text or "").strip()
        if not text:
            raise AgentOutputError(
                "Planning model returned empty content",
                code=AgentFailureCode.MODEL_EMPTY,
            )
        try:
            raw = parse_json_object(text)
        except json.JSONDecodeError as exc:
            raise AgentOutputError(
                f"Planning model output is not valid JSON: {exc}",
                code=AgentFailureCode.MODEL_JSON,
            ) from exc
        try:
            parsed = PlanningAgentLLMOutput.model_validate(raw)
        except ValidationError as exc:
            raise AgentOutputError(
                f"Planning model JSON failed schema validation: {exc}",
                code=AgentFailureCode.MODEL_SCHEMA,
            ) from exc
        steps = parsed.to_planned_steps()
        validate_llm_planned_steps_for_handoff(steps)
        return steps, model_call
