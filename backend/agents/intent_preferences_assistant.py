"""
Optional LLM layer: refine :class:`~edgar_project.orchestration.schemas.GoalPreferences` only.

* Does **not** emit tools, steps, or plans.
* Merges validated JSON patches over the rule-based :func:`~edgar_project.orchestration.goal_preferences.parse_goal_preferences` baseline.
* On schema/JSON/network failure, returns the original :class:`~edgar_project.orchestration.schemas.OrchestrationInput` unchanged and records audit metadata.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.agents.ai_agents_meta import merge_ai_agents_meta, merge_completion_models_entries
from backend.agents.context_budget import ContextBudget
from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.agents.json_extract import parse_json_object
from backend.agents.llm_context import build_intent_preferences_assistant_context
from backend.agents.model_routing import completion_model_audit_dict, resolve_agent_completion_model
from backend.agents.output_schemas import LLMGoalPreferencesPatch
from backend.agents.prompt_registry import load_registered_prompt
from backend.config.settings import Settings, get_settings
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService
from edgar_project.orchestration.goal_preferences import parse_goal_preferences
from edgar_project.orchestration.schemas import (
    GoalPreferences,
    IntentAssistancePayload,
    OrchestrationInput,
)


def merge_goal_preferences(base: GoalPreferences, patch: LLMGoalPreferencesPatch) -> GoalPreferences:
    d = base.model_dump()
    p = patch.model_dump(exclude_none=True)
    if "priority_metrics" in p and p["priority_metrics"] is not None:
        p["priority_metrics"] = list(p["priority_metrics"])[:5]
    d.update(p)
    rules = list(d.get("preference_rules_matched") or [])
    tag = "llm_goal_preferences_patch"
    if tag not in rules:
        rules.append(tag)
    d["preference_rules_matched"] = rules
    return GoalPreferences.model_validate(d)


def maybe_apply_llm_intent_preferences(
    session: Session,
    analysis_run_id: UUID,
    request: OrchestrationInput,
    *,
    llm_provider: ChatCompletionProvider | None,
    settings: Settings | None = None,
) -> OrchestrationInput:
    """
    When enabled and provider present, run intent-preferences assistant and attach
    :class:`~edgar_project.orchestration.schemas.IntentAssistancePayload` on success.

    Always merges audit payload under ``meta_json['ai_agents']['intent_preferences_assistant']``.
    """
    s = settings if settings is not None else get_settings()
    if not s.orchestration_llm_intent_assistance:
        return request
    if llm_provider is None:
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "intent_preferences_assistant",
            {"skipped": True, "reason": "llm_provider_unavailable"},
        )
        return request

    rules_prefs = parse_goal_preferences(request.analysis_goal)
    recorder = RecordedChatCompletionService(session, llm_provider)
    try:
        reg = load_registered_prompt(
            "intent_preferences_assistant",
            s.agent_intent_preferences_prompt_version,
        )
        tmpl = reg.template
        system = tmpl.system_body
        user_payload = build_intent_preferences_assistant_context(
            analysis_goal=request.analysis_goal,
            tickers=list(request.tickers),
            rule_based_goal_preferences=rules_prefs,
            budget=ContextBudget.from_settings(s),
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        model_id, routing_src = resolve_agent_completion_model(s, "intent_preferences")
        req = ChatCompletionRequest(
            model=model_id,
            messages=messages,
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        meta = {
            "role": "intent_preferences_assistant",
            "phase": "intent_preferences",
            "completion_model_routing_source": routing_src,
            "prompt_id": reg.prompt_id,
            "prompt_version": reg.prompt_version,
            "template_path": tmpl.source_uri,
        }
    except Exception as exc:
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "intent_preferences_assistant",
            {"validation_status": "llm_error_fallback", "error": f"prompt_load:{exc}"[:800]},
        )
        return request

    try:
        model_call, result = recorder.complete_and_persist(
            req,
            analysis_run_id=analysis_run_id,
            request_metadata=meta,
            prompt_id=reg.prompt_id,
            prompt_version=reg.prompt_version,
        )
        text = (result.assistant_text or "").strip()
        if not text:
            raise AgentOutputError("Empty model output", code=AgentFailureCode.MODEL_EMPTY)
        raw = parse_json_object(text)
        patch = LLMGoalPreferencesPatch.model_validate(raw)
        merged = merge_goal_preferences(rules_prefs, patch)
        payload = IntentAssistancePayload(
            goal_preferences=merged,
            validation_status="llm_validated",
            model_call_id=str(model_call.id),
            prompt_id=reg.prompt_id,
            prompt_version=reg.prompt_version,
        )
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "intent_preferences_assistant",
            {
                "validation_status": "llm_validated",
                "model_call_id": str(model_call.id),
                "prompt_id": reg.prompt_id,
                "prompt_version": reg.prompt_version,
                "parsed_goal_preferences": merged.model_dump(mode="json"),
            },
        )
        merge_completion_models_entries(
            session,
            analysis_run_id,
            {
                "intent_preferences": completion_model_audit_dict(
                    model_call_model_name=model_call.model_name,
                    routing_source=resolve_agent_completion_model(s, "intent_preferences")[1],
                    phase="intent_preferences",
                ),
            },
        )
        return request.model_copy(
            update={"intent_assistance": payload},
        )
    except (json.JSONDecodeError, ValidationError, AgentOutputError, ValueError) as exc:
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "intent_preferences_assistant",
            {
                "validation_status": "llm_invalid_fallback",
                "error": str(exc)[:800],
                "prompt_id": reg.prompt_id,
                "prompt_version": reg.prompt_version,
            },
        )
        return request
    except Exception as exc:
        merge_ai_agents_meta(
            session,
            analysis_run_id,
            "intent_preferences_assistant",
            {
                "validation_status": "llm_error_fallback",
                "error": str(exc)[:800],
                "prompt_id": reg.prompt_id,
                "prompt_version": reg.prompt_version,
            },
        )
        return request
