"""OpenAI ``chat.completions`` adapter (SDK v1+)."""

from __future__ import annotations

import time
from typing import Any

from backend.llm.exceptions import ChatCompletionProviderError
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult

OPENAI_PROVIDER_ID = "openai"


def _completion_length_payload(model: str, max_tokens: int) -> dict[str, int]:
    """
    Newer OpenAI chat models reject ``max_tokens`` and require ``max_completion_tokens``.

    See API error: unsupported_parameter max_tokens — use max_completion_tokens instead.
    """
    m = (model or "").strip().lower()
    if (
        m.startswith("gpt-5")
        or m.startswith("o1")
        or m.startswith("o3")
        or m.startswith("o4")
    ):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


class OpenAIChatCompletionProvider:
    """Thin wrapper around ``openai.OpenAI`` — maps request/response only."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise ChatCompletionProviderError(
                "openai package is not installed; pip install openai"
            ) from exc
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    @property
    def provider_id(self) -> str:
        return OPENAI_PROVIDER_ID

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload.update(_completion_length_payload(request.model, request.max_tokens))
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            payload["stop"] = request.stop
        # Do not re-inject ``max_tokens`` from model_dump when we emitted max_completion_tokens.
        handled = frozenset(
            {
                "model",
                "messages",
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "stop",
            }
        )
        for k, v in request.model_dump(mode="python", exclude_none=True).items():
            if k in handled:
                continue
            if k not in payload and v is not None:
                payload[k] = v

        t0 = time.perf_counter()
        try:
            response = self._client.chat.completions.create(**payload)
        except Exception as exc:
            raise ChatCompletionProviderError(str(exc)) from exc
        latency_ms = int((time.perf_counter() - t0) * 1000)

        raw = response.model_dump(mode="json")
        choice0 = (response.choices or [None])[0]
        assistant_text: str | None = None
        finish_reason: str | None = None
        if choice0 is not None:
            finish_reason = choice0.finish_reason
            msg = choice0.message
            if msg is not None and msg.content is not None:
                assistant_text = msg.content

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        resolved_model = response.model or request.model

        return ChatCompletionResult(
            model=resolved_model,
            assistant_text=assistant_text,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            raw_response=raw,
        )
