"""
Build the adaptive loop's :class:`~agentic.agent.policy.AgentPolicy` from backend settings.

The agentic investigation loop delegates only its *model-backed* decisions
(goal interpretation, hypothesis generation, experiment selection, critique) to an
``AgentPolicy``. Deterministic computation never goes through the policy.

This module bridges the backend's configured :class:`ChatCompletionProvider` to the
loop's ``Responder`` contract (``(system_prompt, user_prompt) -> raw JSON string``),
returning a :class:`ModelAgentPolicy` when an LLM is configured and falling back to the
deterministic :class:`FixtureAgentPolicy` otherwise. The loop stays offline-safe: with no
provider it still runs to a typed termination, it just makes deterministic decisions.
"""

from __future__ import annotations

import structlog

from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.agent.policy import AgentPolicy, ModelAgentPolicy, Responder
from backend.config.settings import Settings, get_settings
from backend.llm.exceptions import ChatCompletionProviderError, LLMProviderConfigurationError
from backend.llm.factory import get_chat_completion_provider
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest

log = structlog.get_logger(__name__)


def _agentic_model(settings: Settings) -> str:
    """Model id for policy calls; reuse the shared agent completion model."""
    return settings.agent_completion_model or "gpt-5.4-mini"


def build_provider_responder(provider: ChatCompletionProvider, *, model: str) -> Responder:
    """Adapt a :class:`ChatCompletionProvider` to the loop's ``Responder`` contract.

    The returned callable takes ``(system_prompt, user_prompt)`` and returns the raw
    assistant text (expected to be JSON — the policy prompts request JSON explicitly).
    ``ModelAgentPolicy`` validates the string and fails safely on malformed output, so
    provider errors are surfaced as an empty string that fails typed validation there.
    """

    def respond(system_prompt: str, user_prompt: str) -> str:
        request = ChatCompletionRequest(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        try:
            result = provider.complete(request)
        except ChatCompletionProviderError as exc:
            # Boundary: a provider failure becomes malformed policy output, which the
            # loop treats as a safe termination rather than an unhandled crash.
            log.warning("agentic.policy.provider_error", error=str(exc))
            return ""
        return result.assistant_text or ""

    return respond


def build_agent_policy(settings: Settings | None = None) -> AgentPolicy:
    """Return the model-backed policy when an LLM is configured, else the fixture policy.

    Never raises on a missing/misconfigured provider: the loop must always be able to run,
    deterministically, without an LLM.
    """
    s = settings if settings is not None else get_settings()
    try:
        provider = get_chat_completion_provider(s)
    except LLMProviderConfigurationError:
        log.info("agentic.policy.fixture", reason="llm_provider_unavailable")
        return FixtureAgentPolicy()
    log.info("agentic.policy.model_backed", model=_agentic_model(s))
    return ModelAgentPolicy(build_provider_responder(provider, model=_agentic_model(s)))
