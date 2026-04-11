"""Provider-agnostic chat completion types (serializable for ``ModelCall`` JSON columns)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatCompletionRequest(BaseModel):
    """
    Chat/completions-style invocation parameters.

    ``messages`` follow the common chat schema: ``role`` (system | user | assistant | tool) and
    ``content`` (string or structured content blocks per provider capabilities).
    """

    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: str | list[str] | None = None

    def to_request_log_dict(self) -> dict[str, Any]:
        """Payload safe to persist (excludes secrets — caller must not put keys in ``messages``)."""
        return self.model_dump(mode="json", exclude_none=True)


class ChatCompletionResult(BaseModel):
    """Normalized outcome of one completion call (plus raw provider body for auditing)."""

    model_config = ConfigDict(extra="forbid")

    model: str
    assistant_text: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = Field(ge=0)
    raw_response: dict[str, Any] = Field(default_factory=dict)
