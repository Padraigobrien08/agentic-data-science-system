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
from backend.llm.pricing import ModelPrice, estimate_cost_usd, parse_model_prices
from backend.llm.protocol import ChatCompletionProvider
from backend.llm.types import ChatCompletionRequest

log = structlog.get_logger(__name__)


def _agentic_model(settings: Settings) -> str:
    """Model id for policy calls; reuse the shared agent completion model."""
    return settings.agent_completion_model or "gpt-5.4-mini"


class CostTrackingResponder:
    """
    Adapt a :class:`ChatCompletionProvider` to the loop's ``Responder`` contract while
    accumulating the USD cost of each completion.

    Cost is held here (rather than inside the policy) because usage is only visible at
    the provider boundary. The loop drains it after every policy decision via
    :class:`~agentic.agent.policy.CostAwarePolicy`, so ``LoopBudget.max_cost_usd`` binds
    on real token usage. Unpriced models accrue ``0.0`` — see :mod:`backend.llm.pricing`.
    """

    def __init__(
        self, provider: ChatCompletionProvider, *, model: str, prices: dict[str, ModelPrice] | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._prices = prices or {}
        self._pending_cost_usd = 0.0

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        request = ChatCompletionRequest(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        try:
            result = self._provider.complete(request)
        except ChatCompletionProviderError as exc:
            # Boundary: a provider failure becomes malformed policy output, which the
            # loop treats as a safe termination rather than an unhandled crash.
            log.warning("agentic.policy.provider_error", error=str(exc))
            return ""
        self._pending_cost_usd += estimate_cost_usd(
            self._prices,
            model=result.model or self._model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        return result.assistant_text or ""

    def drain_cost_usd(self) -> float:
        """Cost accrued since the last drain (the loop charges it to the run budget)."""
        pending, self._pending_cost_usd = self._pending_cost_usd, 0.0
        return pending


class CostAwareModelPolicy(ModelAgentPolicy):
    """:class:`ModelAgentPolicy` that reports spend, satisfying ``CostAwarePolicy``."""

    def __init__(self, responder: CostTrackingResponder) -> None:
        super().__init__(responder)
        self._cost_source = responder

    def drain_cost_usd(self) -> float:
        return self._cost_source.drain_cost_usd()


def build_provider_responder(provider: ChatCompletionProvider, *, model: str) -> Responder:
    """Adapt a :class:`ChatCompletionProvider` to the loop's ``Responder`` contract.

    Retained as the plain (cost-unaware) adapter; :class:`CostTrackingResponder` is the
    one wired into :func:`build_agent_policy`.
    """
    return CostTrackingResponder(provider, model=model)


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
    model = _agentic_model(s)
    prices = parse_model_prices(s.llm_model_prices)
    log.info("agentic.policy.model_backed", model=model, priced=model in prices)
    return CostAwareModelPolicy(CostTrackingResponder(provider, model=model, prices=prices))
