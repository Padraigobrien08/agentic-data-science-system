"""Construct a :class:`~backend.llm.protocol.ChatCompletionProvider` from settings."""

from __future__ import annotations

from backend.config.settings import Settings, get_settings
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.openai_provider import OpenAIChatCompletionProvider
from backend.llm.protocol import ChatCompletionProvider


def get_chat_completion_provider(settings: Settings | None = None) -> ChatCompletionProvider:
    """
    Build the configured provider.

    * ``llm_provider`` ``openai`` — requires ``openai_api_key``.
    * ``llm_provider`` ``off`` — raises (no provider); tests should inject a stub.
    """
    s = settings if settings is not None else get_settings()
    kind = (s.llm_provider or "off").strip().lower()
    if kind == "off":
        raise LLMProviderConfigurationError(
            "LLM provider is disabled (EDGAR_BACKEND_LLM_PROVIDER=off). "
            "Set EDGAR_BACKEND_LLM_PROVIDER=openai and EDGAR_BACKEND_OPENAI_API_KEY for live calls."
        )
    if kind == "openai":
        key = s.openai_api_key.get_secret_value() if s.openai_api_key else None
        if not key:
            raise LLMProviderConfigurationError(
                "OpenAI is selected but EDGAR_BACKEND_OPENAI_API_KEY is not set."
            )
        return OpenAIChatCompletionProvider(
            api_key=key,
            base_url=s.openai_base_url,
            timeout=s.openai_timeout_s,
        )
    raise LLMProviderConfigurationError(f"Unknown EDGAR_BACKEND_LLM_PROVIDER: {kind!r}")
