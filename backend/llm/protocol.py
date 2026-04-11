"""Protocol for chat completion providers (no persistence, no agent logic)."""

from __future__ import annotations

from typing import Protocol

from backend.llm.types import ChatCompletionRequest, ChatCompletionResult


class ChatCompletionProvider(Protocol):
    """Transport-only adapter to a vendor chat completions API."""

    @property
    def provider_id(self) -> str:
        """Short id persisted on ``ModelCall.provider`` (e.g. ``openai``)."""
        ...

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        """Perform one non-streaming chat completion."""
        ...
