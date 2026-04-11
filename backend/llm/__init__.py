"""Vendor-neutral chat completion providers (no agent prompts)."""

from backend.llm.exceptions import ChatCompletionProviderError, LLMProviderConfigurationError
from backend.llm.factory import describe_llm_runtime, get_chat_completion_provider
from backend.llm.openai_provider import OPENAI_PROVIDER_ID, OpenAIChatCompletionProvider
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult

__all__ = [
    "OPENAI_PROVIDER_ID",
    "ChatCompletionProvider",
    "ChatCompletionProviderError",
    "ChatCompletionRequest",
    "ChatCompletionResult",
    "LLMProviderConfigurationError",
    "OpenAIChatCompletionProvider",
    "describe_llm_runtime",
    "get_chat_completion_provider",
]
