"""
AgentPolicy — the model-backed decision surface.

Deterministic computation never goes through the policy; only *interpretation*,
*hypothesis generation*, *experiment selection*, and *critique* do. Each policy
method is one "model call" with a defined input and a typed, validated output.
Model-backed policies validate the raw response into these types and fail safely
(:class:`MalformedPolicyResponse`) on malformed output.

Two implementations satisfy the protocol: :class:`FixtureAgentPolicy`
(deterministic, for tests) and :class:`ModelAgentPolicy` (wraps a JSON responder).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, ValidationError

from agentic.domain.common import DomainModel


class AnalysisIntent(str, Enum):
    """What the goal is primarily asking for (drives which experiments are candidates)."""

    trend = "trend"
    comparison = "comparison"
    correlation = "correlation"
    anomaly = "anomaly"
    distribution = "distribution"
    ranking = "ranking"
    association = "association"
    profile = "profile"
    general = "general"


# -- typed policy I/O --------------------------------------------------------


class GoalInterpretation(DomainModel):
    intent: AnalysisIntent
    metric_hint: str | None = None
    group_hint: str | None = None
    direction: Literal["up", "down"] | None = None
    rationale: str = ""


class HypothesisProposal(DomainModel):
    statement: str = Field(..., min_length=1)
    metric: str | None = None
    direction: Literal["up", "down", "none"] = "none"
    rationale: str = ""


class HypothesisProposals(DomainModel):
    hypotheses: list[HypothesisProposal] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class ExperimentChoice(DomainModel):
    """Selection among candidate experiments; ``request_index`` indexes candidates."""

    request_index: int | None = None
    rationale: str = ""


class CritiqueProposal(DomainModel):
    should_challenge: bool = False
    target_hypothesis_id: str | None = None
    falsification_tool: str | None = None
    message: str = ""
    rationale: str = ""


# -- errors ------------------------------------------------------------------


class AgentPolicyError(RuntimeError):
    """Base for policy failures (the loop terminates safely on these)."""


class MalformedPolicyResponse(AgentPolicyError):
    """The model returned output that failed typed validation."""


# -- protocol ----------------------------------------------------------------


@runtime_checkable
class AgentPolicy(Protocol):
    """The set of model-backed decisions the loop delegates."""

    def interpret_goal(self, goal_text: str, *, capability_summary: dict) -> GoalInterpretation: ...

    def generate_hypotheses(
        self, interpretation: GoalInterpretation, *, metric_names: list[str], dimension_names: list[str]
    ) -> HypothesisProposals: ...

    def select_experiment(self, *, goal_summary: dict, candidates: list[dict]) -> ExperimentChoice: ...

    def critique(self, *, strongest_claim: dict | None, available_tools: list[str]) -> CritiqueProposal: ...


@runtime_checkable
class CostAwarePolicy(Protocol):
    """
    Optional policy extension: report and reset the cost accrued since the last drain.

    Policies that know their token usage (model-backed ones) implement this so the
    loop's ``max_cost_usd`` budget is enforceable. Policies that don't are unaffected
    — :func:`drain_policy_cost` reports zero for them.
    """

    def drain_cost_usd(self) -> float: ...


def drain_policy_cost(policy: object) -> float:
    """
    Cost accrued by ``policy`` since the last drain, or ``0.0`` when it doesn't
    track cost. Kept duck-typed so :class:`AgentPolicy` stays a four-method contract
    and existing implementations need no change.
    """
    drain = getattr(policy, "drain_cost_usd", None)
    if not callable(drain):
        return 0.0
    try:
        return max(0.0, float(drain()))
    except (TypeError, ValueError):
        return 0.0


# -- model-backed implementation --------------------------------------------

Responder = Callable[[str, str], str]
"""A function (system_prompt, user_prompt) -> raw JSON string."""


@dataclass(frozen=True)
class PolicyPrompts:
    """
    The system prompt for each of the four model-backed decisions.

    Defaults are terse but sufficient: they keep this package standalone, so
    :class:`ModelAgentPolicy` works with no external prompt files and the loop stays
    runnable outside this repository. Richer, versioned bodies live under
    ``backend/agents/prompts/`` and are *injected* — this module never loads them, which
    is what keeps ``agentic/`` free of a dependency on the backend.
    """

    interpret_goal: str = "Interpret the analytical goal. Reply as GoalInterpretation JSON."
    generate_hypotheses: str = (
        "Propose falsifiable hypotheses and open questions. Reply as HypothesisProposals JSON."
    )
    select_experiment: str = "Choose the most informative next experiment. Reply as ExperimentChoice JSON."
    critique: str = (
        "Challenge the strongest current claim; suggest a falsification tool. "
        "Reply as CritiqueProposal JSON."
    )


DEFAULT_POLICY_PROMPTS = PolicyPrompts()
"""The standalone defaults, used whenever no prompts are injected."""


class ModelAgentPolicy:
    """
    Policy backed by a JSON responder (e.g. an LLM). Every method validates the
    raw response into a typed model and raises :class:`MalformedPolicyResponse`
    on malformed output, so the loop can fail safely.

    ``prompts`` overrides the system prompt of each decision; omitting it selects
    :data:`DEFAULT_POLICY_PROMPTS`.
    """

    def __init__(self, respond: Responder, *, prompts: PolicyPrompts | None = None) -> None:
        self._respond = respond
        self._prompts = prompts or DEFAULT_POLICY_PROMPTS

    def _call(self, system: str, user: str, model: type[BaseModel]):
        raw = self._respond(system, user)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MalformedPolicyResponse(f"policy response is not valid JSON: {exc}") from exc
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise MalformedPolicyResponse(f"policy response failed {model.__name__} validation: {exc}") from exc

    def interpret_goal(self, goal_text: str, *, capability_summary: dict) -> GoalInterpretation:
        return self._call(
            self._prompts.interpret_goal,
            json.dumps({"goal": goal_text, "capabilities": capability_summary}),
            GoalInterpretation,
        )

    def generate_hypotheses(
        self, interpretation: GoalInterpretation, *, metric_names: list[str], dimension_names: list[str]
    ) -> HypothesisProposals:
        return self._call(
            self._prompts.generate_hypotheses,
            json.dumps({"interpretation": interpretation.model_dump(mode="json"),
                        "metrics": metric_names, "dimensions": dimension_names}),
            HypothesisProposals,
        )

    def select_experiment(self, *, goal_summary: dict, candidates: list[dict]) -> ExperimentChoice:
        return self._call(
            self._prompts.select_experiment,
            json.dumps({"goal": goal_summary, "candidates": candidates}),
            ExperimentChoice,
        )

    def critique(self, *, strongest_claim: dict | None, available_tools: list[str]) -> CritiqueProposal:
        return self._call(
            self._prompts.critique,
            json.dumps({"claim": strongest_claim, "tools": available_tools}),
            CritiqueProposal,
        )
