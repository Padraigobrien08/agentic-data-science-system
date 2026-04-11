"""Construct a :class:`~backend.llm.protocol.ChatCompletionProvider` from settings."""

from __future__ import annotations

from backend.config.settings import Settings, get_settings
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.openai_provider import OpenAIChatCompletionProvider
from backend.llm.protocol import ChatCompletionProvider


def describe_llm_runtime(settings: Settings | None = None) -> tuple[str, bool, str]:
    """
    Return ``(provider_kind, ready_for_live_calls, message)``.

    ``message`` is always a non-empty string so health JSON never uses null for the explanation
    (when ready, it confirms configuration; when not, it says what to fix).

    Used by health checks and worker startup so operators can see why critic/report skip
    (``llm_provider_unavailable``) without reading container logs mid-run.
    """
    s = settings if settings is not None else get_settings()
    kind = (s.llm_provider or "off").strip().lower()
    if kind == "off":
        return (
            kind,
            False,
            "LLM disabled (EDGAR_BACKEND_LLM_PROVIDER=off). "
            "Set EDGAR_BACKEND_LLM_PROVIDER=openai and an API key on every process that runs the pipeline "
            "(Docker: api + worker; restart after changing .env).",
        )
    if kind == "openai":
        key = s.openai_api_key.get_secret_value() if s.openai_api_key else None
        if not key or not str(key).strip():
            return (
                kind,
                False,
                "OpenAI selected but no API key. Set EDGAR_BACKEND_OPENAI_API_KEY or OPENAI_API_KEY "
                "for api and worker (Compose: repo-root .env, then docker compose up -d --force-recreate api worker).",
            )
        return (
            kind,
            True,
            "OpenAI provider and API key are configured in this process; critic/report LLM steps can run here.",
        )
    return kind, False, f"Unknown EDGAR_BACKEND_LLM_PROVIDER={kind!r}."


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
