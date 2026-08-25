"""
The policy's system prompts are injectable, and the domain still stands alone without them.

Two properties matter here and they pull in opposite directions. Richer prompts belong in
the backend's versioned registry, so ``ModelAgentPolicy`` must accept them from outside.
But ``agentic/`` must keep working with no prompt files at all — that is what lets the
investigation domain be used outside this repository. Injection with defaults satisfies both;
these tests pin the pair so a later refactor cannot quietly drop either half.
"""

from __future__ import annotations

import dataclasses

import pytest

from agentic.agent.policy import (
    DEFAULT_POLICY_PROMPTS,
    GoalInterpretation,
    ModelAgentPolicy,
    PolicyPrompts,
)


class _Recorder:
    """Responder that records the system prompt it was handed and returns fixed JSON."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.system_prompts: list[str] = []

    def __call__(self, system: str, user: str) -> str:
        self.system_prompts.append(system)
        return self.payload


_GOAL = '{"intent": "trend", "rationale": "r"}'
_HYPOTHESES = '{"hypotheses": [], "questions": []}'
_CHOICE = '{"request_index": 0, "rationale": "r"}'
_CRITIQUE = '{"should_challenge": false, "rationale": "r"}'


def test_default_construction_uses_the_standalone_defaults() -> None:
    """No prompts supplied -> the package's own defaults, with no external file needed."""
    recorder = _Recorder(_GOAL)
    policy = ModelAgentPolicy(recorder)

    policy.interpret_goal("revenue trend", capability_summary={})

    assert recorder.system_prompts == [DEFAULT_POLICY_PROMPTS.interpret_goal]


def test_every_decision_reads_its_prompt_from_the_container() -> None:
    """All four call sites are wired to the container, not to inline literals."""
    injected = PolicyPrompts(
        interpret_goal="INTERPRET",
        generate_hypotheses="HYPOTHESISE",
        select_experiment="SELECT",
        critique="CRITIQUE",
    )
    # One recorder per call so each response parses as the type that call expects.
    seen: list[str] = []
    for payload, invoke in (
        (_GOAL, lambda p: p.interpret_goal("g", capability_summary={})),
        (_HYPOTHESES, lambda p: p.generate_hypotheses(
            GoalInterpretation(intent="trend"), metric_names=[], dimension_names=[])),
        (_CHOICE, lambda p: p.select_experiment(goal_summary={}, candidates=[{"index": 0}])),
        (_CRITIQUE, lambda p: p.critique(strongest_claim=None, available_tools=[])),
    ):
        recorder = _Recorder(payload)
        invoke(ModelAgentPolicy(recorder, prompts=injected))
        seen.extend(recorder.system_prompts)

    assert seen == ["INTERPRET", "HYPOTHESISE", "SELECT", "CRITIQUE"]


def test_partial_override_keeps_the_remaining_defaults() -> None:
    """Overriding one decision must not blank out the other three."""
    prompts = PolicyPrompts(select_experiment="SELECT")

    assert prompts.select_experiment == "SELECT"
    assert prompts.interpret_goal == DEFAULT_POLICY_PROMPTS.interpret_goal
    assert prompts.generate_hypotheses == DEFAULT_POLICY_PROMPTS.generate_hypotheses
    assert prompts.critique == DEFAULT_POLICY_PROMPTS.critique


def test_prompts_are_immutable() -> None:
    """Frozen, so a shared container cannot be mutated by one caller for everyone."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_POLICY_PROMPTS.interpret_goal = "mutated"  # type: ignore[misc]


def test_defaults_are_unchanged_from_the_pre_injection_literals() -> None:
    """
    The defaults are the exact strings that were inline before the seam existed, so
    a no-argument ``ModelAgentPolicy`` behaves identically to the previous version.
    """
    # Moved on from the pre-injection literal for the same reason the critique default did,
    # below: `GoalInterpretation` gained `answerable`/`unsupported_concept`, and a default
    # prompt that never mentions them means a standalone `agentic/` can never decline an
    # unanswerable question — it would substitute the nearest metric instead, which is the
    # failure the field exists to stop.
    assert DEFAULT_POLICY_PROMPTS.interpret_goal == (
        "Interpret the analytical goal. The capability summary lists every column that "
        "exists; a concept the goal names that is not measured by any of them cannot be "
        "answered here, however close another column sounds. In that case set "
        "answerable=false and put the missing concept in unsupported_concept — do not "
        "substitute the nearest metric, because a confident answer about something the user "
        "did not ask is worse than no answer. Reply as GoalInterpretation JSON."
    )
    assert DEFAULT_POLICY_PROMPTS.generate_hypotheses == (
        "Propose falsifiable hypotheses and open questions. Reply as HypothesisProposals JSON."
    )
    assert DEFAULT_POLICY_PROMPTS.select_experiment == (
        "Choose the most informative next experiment. Reply as ExperimentChoice JSON."
    )
    # The critique default has moved on from the pre-injection literal, deliberately: the
    # policy contract gained `contradicts_hypothesis_id`, and a default prompt that never
    # mentions it means a standalone `agentic/` — the offline path these defaults exist for —
    # could never report a contradiction between two supported claims.
    assert DEFAULT_POLICY_PROMPTS.critique == (
        "Challenge the strongest current claim; suggest a falsification tool. If two claims "
        "in supported_claims cannot both be true, report the conflict in "
        "contradicts_hypothesis_id. Reply as CritiqueProposal JSON."
    )


def test_injection_survives_subclassing() -> None:
    """
    ``CostAwareModelPolicy`` in the backend subclasses this and forwards ``prompts=``;
    the keyword must therefore work through ``super().__init__``.
    """

    class _Sub(ModelAgentPolicy):
        pass

    recorder = _Recorder(_GOAL)
    _Sub(recorder, prompts=PolicyPrompts(interpret_goal="SUB")).interpret_goal(
        "g", capability_summary={}
    )

    assert recorder.system_prompts == ["SUB"]
