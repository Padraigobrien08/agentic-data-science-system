"""LLM report writer — produces the final user-facing explanation (no tools)."""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import ValidationError

from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.output_schemas import CriticAgentLLMOutput, ReportAgentLLMOutput
from backend.agents.prompt_registry import load_registered_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.types import ChatCompletionRequest
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService


class ReportAgent:
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
        critic: CriticAgentLLMOutput,
        artifact_excerpts: dict[str, str] | None = None,
    ) -> tuple[ReportAgentLLMOutput, ModelCall]:
        reg = load_registered_prompt("report", self._settings.agent_report_prompt_version)
        tmpl = reg.template
        system = tmpl.system_body
        user_payload = {
            "orchestration_summary": orchestration_summary,
            "critic": critic.model_dump(mode="json"),
            "artifact_excerpts_by_role": artifact_excerpts or {},
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        req = ChatCompletionRequest(
            model=self._settings.agent_completion_model,
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "report",
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
        try:
            text = (result.assistant_text or "").strip()
            if not text:
                raise AgentOutputError(
                    "Report model returned empty content",
                    code=AgentFailureCode.MODEL_EMPTY,
                )
            try:
                raw = parse_json_object(text)
            except json.JSONDecodeError as exc:
                raise AgentOutputError(
                    f"Report model output is not valid JSON: {exc}",
                    code=AgentFailureCode.MODEL_JSON,
                ) from exc
            try:
                parsed = ReportAgentLLMOutput.model_validate(raw)
            except ValidationError as exc:
                raise AgentOutputError(
                    f"Report model JSON failed schema validation: {exc}",
                    code=AgentFailureCode.MODEL_SCHEMA,
                ) from exc
            return parsed, model_call
        except AgentOutputError as exc:
            self._rec.mark_agent_output_failed(
                model_call.id,
                detail=str(exc),
                agent_code=exc.code,
            )
            raise
