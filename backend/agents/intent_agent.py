"""LLM intent agent — produces :class:`~edgar_project.orchestration.schemas.InterpretedGoal` (no tools)."""

from __future__ import annotations

import json
from uuid import UUID

from backend.agents.errors import AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.output_schemas import IntentAgentLLMOutput
from backend.agents.prompt_loader import load_agent_prompt
from backend.agents.template_render import render_intent_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService
from edgar_project.orchestration.schemas import InterpretedGoal


class IntentAgent:
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
        user_request: str,
        tickers: list[str],
        refresh: bool,
    ) -> tuple[InterpretedGoal, ModelCall]:
        version = self._settings.agent_intent_prompt_version
        tmpl = load_agent_prompt("intent", version)
        system = render_intent_prompt(tmpl.system_body)
        user_payload = {
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
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "intent",
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
            raise AgentOutputError("Intent model returned empty content")
        try:
            raw = parse_json_object(text)
            parsed = IntentAgentLLMOutput.model_validate(raw)
            ig = parsed.to_interpreted_goal()
        except Exception as exc:
            raise AgentOutputError(f"Invalid intent JSON: {exc}") from exc
        return ig, model_call
