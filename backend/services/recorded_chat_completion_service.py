"""
Persist :class:`~backend.models.model_call.ModelCall` rows around a :class:`~backend.llm.protocol.ChatCompletionProvider`.

No prompts or EDGAR business rules — only request/response logging and FK context.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.llm.exceptions import ChatCompletionProviderError
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult
from backend.models.enums import ModelCallStatus
from backend.models.model_call import ModelCall
from backend.repositories.model_call_repository import ModelCallRepository


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
    ) -> tuple[ModelCall, ChatCompletionResult]:
        """
        Insert ``ModelCall`` (running), invoke provider, update row with tokens/latency/raw response.

        ``request_metadata`` is merged into the persisted ``request_payload_json`` under ``agent`` (not
        sent to the provider). Use it for template id/version and agent role for audits.

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
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            tool_call_id=tool_call_id,
            status=ModelCallStatus.running,
            request_payload_json=logged_request,
            started_at=started,
        )
        self._calls.add(row)
        self._calls.flush()

        t0 = time.perf_counter()
        try:
            result = self._provider.complete(request)
        except ChatCompletionProviderError as exc:
            row.status = ModelCallStatus.error
            row.error_detail = str(exc)[:8192]
            row.finished_at = datetime.now(timezone.utc)
            row.latency_ms = int((time.perf_counter() - t0) * 1000)
            self._calls.flush()
            raise

        row.status = ModelCallStatus.success
        row.finished_at = datetime.now(timezone.utc)
        row.latency_ms = result.latency_ms
        row.prompt_tokens = result.prompt_tokens
        row.completion_tokens = result.completion_tokens
        row.model_name = result.model
        row.response_payload_json = result.model_dump(mode="json")
        self._calls.flush()
        return row, result
