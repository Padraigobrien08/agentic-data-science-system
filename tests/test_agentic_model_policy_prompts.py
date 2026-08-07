"""
`build_agent_policy` loads the registered policy prompts and injects them into the loop.

The contract under test has two halves. When a provider and prompt files are both present, the
returned policy must actually use the versioned bodies from `backend/agents/prompts/` — otherwise
the agency benchmark would be measuring the terse in-domain defaults while claiming to measure
the registry. And when anything is missing, the policy must still be constructible: the loop is
required to run offline, and a misconfigured prompt directory is not allowed to be fatal.
"""

from __future__ import annotations

import pytest

import backend.agents.agentic_model_policy as policy_mod
from agentic.agent.policy import (
    DEFAULT_POLICY_PROMPTS,
    CritiqueProposal,
    MalformedPolicyResponse,
    ModelAgentPolicy,
)
from backend.agents.agentic_model_policy import (
    AGENTIC_PROMPT_VERSION,
    CostAwareModelPolicy,
    _load_policy_prompts,
    build_agent_policy,
)
from backend.agents.prompt_registry import AGENTIC_POLICY_ROLES
from backend.config.settings import Settings
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.types import ChatCompletionResult


class _StubProvider:
    """Minimal ChatCompletionProvider stand-in; never touches the network."""

    def __init__(self, assistant_text: str = "{}") -> None:
        self.assistant_text = assistant_text

    def complete(self, request):  # noqa: ANN001 - test double
        return ChatCompletionResult(
            assistant_text=self.assistant_text,
            model=request.model,
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=0,
        )


def _settings() -> Settings:
    return Settings(agent_completion_model="test-model")


def _with_provider(monkeypatch, assistant_text: str = "{}") -> None:
    monkeypatch.setattr(
        policy_mod, "get_chat_completion_provider", lambda s: _StubProvider(assistant_text)
    )


# -- loading -----------------------------------------------------------------


def test_every_registered_role_resolves_to_a_prompt_body() -> None:
    prompts, identity = _load_policy_prompts()

    assert len(identity) == len(AGENTIC_POLICY_ROLES)
    assert set(identity.values()) == {AGENTIC_PROMPT_VERSION}
    for body in (
        prompts.interpret_goal,
        prompts.generate_hypotheses,
        prompts.select_experiment,
        prompts.critique,
    ):
        assert len(body) > 200, "a registered prompt body should be substantive, not a one-liner"


def test_roles_map_to_the_right_decisions() -> None:
    """
    Guards the positional unpack in `_load_policy_prompts`: a reordering of
    AGENTIC_POLICY_ROLES would otherwise silently give the critic the selector's prompt.
    """
    prompts, _ = _load_policy_prompts()

    assert "Goal interpreter" in prompts.interpret_goal
    assert "Hypothesis generator" in prompts.generate_hypotheses
    assert "Experiment selector" in prompts.select_experiment
    assert "Critic" in prompts.critique


def test_the_documented_decline_shape_actually_validates() -> None:
    """
    Regression for the 1.0.0 critic prompt, which told the model to decline "with nulls".
    Only two of `CritiqueProposal`'s five fields are nullable, so a null `message` failed
    validation and took the entire investigation down with `reason=error` — every case that
    reached a supported claim was lost. The prompt now names the nullable fields; this pins
    the shape it documents.
    """
    declined = (
        '{"should_challenge": false, "target_hypothesis_id": null, '
        '"falsification_tool": null, "message": "", "rationale": "nothing to challenge"}'
    )
    policy = ModelAgentPolicy(lambda system, user: declined)

    result = policy.critique(strongest_claim=None, available_tools=[])

    assert isinstance(result, CritiqueProposal)
    assert result.should_challenge is False


def test_a_null_string_field_is_still_rejected() -> None:
    """The constraint the prompt exists to respect — kept visible so it cannot regress."""
    nulled = (
        '{"should_challenge": false, "target_hypothesis_id": null, '
        '"falsification_tool": null, "message": null, "rationale": null}'
    )
    policy = ModelAgentPolicy(lambda system, user: nulled)

    with pytest.raises(MalformedPolicyResponse):
        policy.critique(strongest_claim=None, available_tools=[])


def test_every_prompt_names_its_nullable_fields() -> None:
    """
    Each prompt must state which fields accept null. This is the failure mode that cost a
    whole benchmark run, and prose is where the fix lives, so prose is what gets asserted.
    """
    prompts, _ = _load_policy_prompts()

    for body in (
        prompts.interpret_goal,
        prompts.generate_hypotheses,
        prompts.select_experiment,
        prompts.critique,
    ):
        assert "may be null" in body, "prompt does not tell the model which fields accept null"
        assert "never `null`" in body


def test_missing_prompt_files_degrade_to_the_domain_defaults(monkeypatch) -> None:
    def _boom(role: str, version: str):
        raise FileNotFoundError(f"no prompt for {role} {version}")

    monkeypatch.setattr(policy_mod, "load_registered_prompt", _boom)

    prompts, identity = _load_policy_prompts()

    assert prompts is DEFAULT_POLICY_PROMPTS
    assert identity == {}


# -- build_agent_policy ------------------------------------------------------


def test_configured_provider_yields_a_policy_using_the_registered_prompts(monkeypatch) -> None:
    _with_provider(monkeypatch)

    policy = build_agent_policy(_settings())

    assert isinstance(policy, CostAwareModelPolicy)
    assert policy._prompts is not DEFAULT_POLICY_PROMPTS
    assert policy._prompts.select_experiment != DEFAULT_POLICY_PROMPTS.select_experiment
    assert "edgar.agentic.experiment_selector" in policy.prompt_identity


def test_prompt_identity_names_every_role_for_the_scoreboard(monkeypatch) -> None:
    _with_provider(monkeypatch)

    policy = build_agent_policy(_settings())

    assert set(policy.prompt_identity) == {
        "edgar.agentic.goal_interpreter",
        "edgar.agentic.hypothesis_generator",
        "edgar.agentic.experiment_selector",
        "edgar.agentic.critic",
    }


def test_unreadable_prompts_still_produce_a_working_model_policy(monkeypatch) -> None:
    """A broken prompt directory must not make a configured provider unusable."""
    _with_provider(monkeypatch)
    monkeypatch.setattr(
        policy_mod, "load_registered_prompt", lambda role, version: (_ for _ in ()).throw(OSError("nope"))
    )

    policy = build_agent_policy(_settings())

    assert isinstance(policy, CostAwareModelPolicy)
    assert policy._prompts is DEFAULT_POLICY_PROMPTS
    assert policy.prompt_identity == {}


def test_absent_provider_still_falls_back_to_the_fixture_policy(monkeypatch) -> None:
    """The pre-existing offline contract is unchanged by prompt loading."""

    def _unconfigured(s):  # noqa: ANN001 - test double
        raise LLMProviderConfigurationError("no provider")

    monkeypatch.setattr(policy_mod, "get_chat_completion_provider", _unconfigured)

    policy = build_agent_policy(_settings())

    assert type(policy).__name__ == "FixtureAgentPolicy"


def test_cost_tracking_survives_prompt_injection(monkeypatch) -> None:
    """Injecting prompts must not break the CostAwarePolicy contract the budget relies on."""
    _with_provider(monkeypatch, '{"intent": "trend", "rationale": "r"}')

    policy = build_agent_policy(_settings())
    policy.interpret_goal("revenue trend", capability_summary={"metrics": [], "dimensions": []})

    assert policy.drain_cost_usd() >= 0.0
