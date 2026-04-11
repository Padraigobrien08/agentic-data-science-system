"""
Persist :class:`~backend.models.model_call.ModelCall` rows around a :class:`~backend.llm.protocol.ChatCompletionProvider`.

No prompts or EDGAR business rules — only request/response logging and FK context.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from backend.llm.exceptions import ChatCompletionProviderError
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult
from backend.models.enums import ModelCallStatus
from backend.models.model_call import ModelCall
from backend.observability.metrics import observe_llm_completion
from backend.observability.tracing import bind_current_trace_for_logs, get_tracer
from backend.repositories.model_call_repository import ModelCallRepository

log = structlog.get_logger(__name__)


class RecordedChatCompletionService:
    def __init__(
        self,
        session: Session,
        provider: ChatCompletionProvider,
        *,
        calls: ModelCallRepository | None = None,
    ) -> None:
        self._session = session
        self._provider = provider
        self._calls = calls if calls is not None else ModelCallRepository(session)

    def complete_and_persist(
        self,
        request: ChatCompletionRequest,
        *,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        tool_call_id: UUID | None = None,
        request_metadata: dict[str, Any] | None = None,
        prompt_id: str | None = None,
        prompt_version: str | None = None,
    ) -> tuple[ModelCall, ChatCompletionResult]:
        """
        Insert ``ModelCall`` (running), invoke provider, update row with tokens/latency/raw response.

        ``request_metadata`` is merged into the persisted ``request_payload_json`` under ``agent`` (not
        sent to the provider). Use it for agent role and optional extra audit fields.

        ``prompt_id`` / ``prompt_version`` are stored as first-class columns when provided (agent
        runtime); generic LLM calls may omit them.

        Commits are the caller's responsibility. On provider error the row is left ``error`` and the
        exception is re-raised.
        """
        started = datetime.now(timezone.utc)
        logged_request: dict[str, Any] = dict(request.to_request_log_dict())
        if request_metadata:
            logged_request["agent"] = request_metadata
        row = ModelCall(
            provider=self._provider.provider_id,
            model_name=request.model,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            tool_call_id=tool_call_id,
            status=ModelCallStatus.running,
            request_payload_json=logged_request,
            started_at=started,
        )
        self._calls.add(row)
        self._calls.flush()

        agent_role = "unknown"
        if request_metadata:
            agent_role = str(request_metadata.get("role") or request_metadata.get("agent_role") or "unknown")

        llm_tracer = get_tracer("backend.llm")
        t0 = time.perf_counter()
        try:
            with llm_tracer.start_as_current_span(
                "llm.chat_completion",
                attributes={
                    "gen_ai.operation.name": "chat",
                    "gen_ai.request.model": request.model,
                    "edgar.agent.role": agent_role,
                    "analysis.run.id": str(analysis_run_id) if analysis_run_id else "",
                },
            ):
                bind_current_trace_for_logs()
                result = self._provider.complete(request)
        except ChatCompletionProviderError as exc:
            row.status = ModelCallStatus.error
            row.error_detail = str(exc)[:8192]
            row.finished_at = datetime.now(timezone.utc)
            row.latency_ms = int((time.perf_counter() - t0) * 1000)
            self._calls.flush()
            dur = time.perf_counter() - t0
            observe_llm_completion(agent_role, "error", dur)
            log.warning(
                "llm_completion_failed",
                agent_role=agent_role,
                analysis_run_id=str(analysis_run_id) if analysis_run_id else None,
                exc_type=type(exc).__name__,
                duration_s=round(dur, 4),
            )
            raise

        row.status = ModelCallStatus.success
        row.finished_at = datetime.now(timezone.utc)
        row.latency_ms = result.latency_ms
        row.prompt_tokens = result.prompt_tokens
        row.completion_tokens = result.completion_tokens
        row.model_name = result.model
        row.response_payload_json = result.model_dump(mode="json")
        self._calls.flush()
        dur = time.perf_counter() - t0
        observe_llm_completion(agent_role, "success", dur)
        log.info(
            "llm_completion_ok",
            agent_role=agent_role,
            analysis_run_id=str(analysis_run_id) if analysis_run_id else None,
            duration_s=round(dur, 4),
            model=result.model,
        )
        return row, result

    def mark_agent_output_failed(
        self,
        model_call_id: UUID,
        *,
        detail: str,
        agent_code: str | None = None,
    ) -> None:
        """
        After a successful HTTP completion, the model response failed agent-side validation.

        Marks the row ``error`` so traces do not show a false success for unusable output.
        """
        row = self._calls.get(model_call_id)
        if row is None:
            return
        row.status = ModelCallStatus.error
        prefix = f"agent_output_invalid[{agent_code}]" if agent_code else "agent_output_invalid"
        row.error_detail = f"{prefix}: {detail}"[:8192]
        if row.finished_at is None:
            row.finished_at = datetime.now(timezone.utc)
        self._calls.flush()
