"""LLM critic — reviews findings / caveats / trustworthiness-related artifacts (no tools)."""

from __future__ import annotations

import json
from uuid import UUID

from backend.agents.errors import AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.output_schemas import CriticAgentLLMOutput
from backend.agents.prompt_loader import load_agent_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.types import ChatCompletionRequest
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService


class CriticAgent:
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
        orchestration_summary: dict,
        artifact_excerpts: dict[str, str],
    ) -> tuple[CriticAgentLLMOutput, ModelCall]:
        version = self._settings.agent_critic_prompt_version
        tmpl = load_agent_prompt("critic", version)
        system = tmpl.system_body
        user_payload = {
            "orchestration_summary": orchestration_summary,
            "artifact_excerpts_by_role": artifact_excerpts,
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        req = ChatCompletionRequest(
            model=self._settings.agent_completion_model,
            messages=messages,
            temperature=0.2,
            max_tokens=3072,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "critic",
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
            raise AgentOutputError("Critic model returned empty content")
        try:
            raw = parse_json_object(text)
            parsed = CriticAgentLLMOutput.model_validate(raw)
        except Exception as exc:
            raise AgentOutputError(f"Invalid critic JSON: {exc}") from exc
        return parsed, model_call
