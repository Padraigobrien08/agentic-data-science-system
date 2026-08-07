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
from agentic.agent.policy import (
    DEFAULT_POLICY_PROMPTS,
    AgentPolicy,
    ModelAgentPolicy,
    PolicyPrompts,
    Responder,
)
from backend.agents.prompt_registry import AGENTIC_POLICY_ROLES, load_registered_prompt
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


#: Prompt file version loaded for every agentic policy role. Bump when a new prompt
#: version ships; the agency benchmark records this so results stay comparable.
AGENTIC_PROMPT_VERSION = "1.0.0"


class CostAwareModelPolicy(ModelAgentPolicy):
    """:class:`ModelAgentPolicy` that reports spend, satisfying ``CostAwarePolicy``."""

    def __init__(
        self,
        responder: CostTrackingResponder,
        *,
        prompts: PolicyPrompts | None = None,
        prompt_identity: dict[str, str] | None = None,
    ) -> None:
        super().__init__(responder, prompts=prompts)
        self._cost_source = responder
        # Read by the agency benchmark so a scoreboard row names the exact prompts that
        # produced it. Empty when the policy fell back to the domain defaults.
        self.prompt_identity: dict[str, str] = dict(prompt_identity or {})

    def drain_cost_usd(self) -> float:
        return self._cost_source.drain_cost_usd()


def _load_policy_prompts(
    version: str = AGENTIC_PROMPT_VERSION,
) -> tuple[PolicyPrompts, dict[str, str]]:
    """
    Load the four registered policy prompts, plus a ``prompt_id -> version`` identity map.

    Never raises. A missing or malformed prompt file degrades to
    :data:`~agentic.agent.policy.DEFAULT_POLICY_PROMPTS` rather than making the loop
    unrunnable — the same never-raise-on-misconfiguration contract
    :func:`build_agent_policy` already honours for an absent LLM provider.
    """
    try:
        loaded = [load_registered_prompt(role, version) for role in AGENTIC_POLICY_ROLES]
    except (FileNotFoundError, ValueError, OSError) as exc:
        log.warning("agentic.policy.prompts_unavailable", version=version, error=str(exc))
        return DEFAULT_POLICY_PROMPTS, {}
    # Positional by AGENTIC_POLICY_ROLES order, which is documented to match the four
    # AgentPolicy methods; named explicitly here so a reordering cannot silently swap them.
    interpreter, generator, selector, critic = loaded
    prompts = PolicyPrompts(
        interpret_goal=interpreter.template.system_body,
        generate_hypotheses=generator.template.system_body,
        select_experiment=selector.template.system_body,
        critique=critic.template.system_body,
    )
    identity = {p.prompt_id: p.prompt_version for p in loaded}
    return prompts, identity


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
    prompts, identity = _load_policy_prompts()
    log.info(
        "agentic.policy.model_backed",
        model=model,
        priced=model in prices,
        prompts=sorted(identity),
        prompt_version=AGENTIC_PROMPT_VERSION if identity else "defaults",
    )
    return CostAwareModelPolicy(
        CostTrackingResponder(provider, model=model, prices=prices),
        prompts=prompts,
        prompt_identity=identity,
    )
