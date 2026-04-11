"""LLM planning agent — produces :class:`~edgar_project.orchestration.schemas.PlannedStep` list (no tools)."""

from __future__ import annotations

import json
from uuid import UUID

from edgar_project.orchestration.schemas import InterpretedGoal, PlannedStep

from backend.agents.errors import AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.output_schemas import PlanningAgentLLMOutput
from backend.agents.prompt_loader import load_agent_prompt
from backend.agents.template_render import render_planning_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.types import ChatCompletionRequest
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService


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
        version = self._settings.agent_planning_prompt_version
        tmpl = load_agent_prompt("planning", version)
        system = render_planning_prompt(tmpl.system_body)
        user_payload = {
            "interpreted_goal": interpreted_goal.model_dump(mode="json"),
            "user_request": user_request,
            "tickers": tickers,
            "refresh": refresh,
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        req = ChatCompletionRequest(
            model=self._settings.agent_completion_model,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "planning",
            "template_id": tmpl.template_id,
            "template_version": tmpl.version,
            "template_path": tmpl.source_uri,
        }
        model_call, result = self._rec.complete_and_persist(
            req,
            analysis_run_id=analysis_run_id,
            request_metadata=meta,
        )
        text = (result.assistant_text or "").strip()
        if not text:
            raise AgentOutputError("Planning model returned empty content")
        try:
            raw = parse_json_object(text)
            parsed = PlanningAgentLLMOutput.model_validate(raw)
            steps = parsed.to_planned_steps()
        except Exception as exc:
            raise AgentOutputError(f"Invalid planning JSON: {exc}") from exc
        return steps, model_call
