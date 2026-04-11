"""LLM provider errors (transport / API only — no domain semantics)."""


class ChatCompletionProviderError(Exception):
    """The upstream provider failed or returned an error (wrapped cause preserved)."""


class LLMProviderConfigurationError(ValueError):
    """Settings do not allow constructing the requested provider (e.g. missing API key)."""
