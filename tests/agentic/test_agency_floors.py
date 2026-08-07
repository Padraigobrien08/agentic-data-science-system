"""
The regression gate on the deterministic agency baseline.

This is the cheap half of the measurement strategy. Model policies are non-deterministic and
cost money, so they are benchmarked on demand by ``backend.dev.agency_bench``. The fixture
policy is deterministic and free, so it can run on every pull request — which makes it the
right place to catch a change that quietly degrades how the loop reasons.

The failure this exists to prevent is a prompt or component edit that trades one property for
another: overall pass rate barely moves while ``calibrated_confidence`` collapses, because the
loop started hedging. A single aggregate number hides that. Per-property floors do not.

Floors sit exactly at the observed baseline rather than a margin below it. The fixture policy
is deterministic — the first test here proves that — so there is no sampling noise to absorb,
and any drop is a real behaviour change worth stopping on.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.agent.policy import CritiqueProposal
from agentic.evaluation.agency import AgencyProperty
from agentic.evaluation.cases import CaseTier
from agentic.evaluation.runner import run_agency_suite

_FLOORS_PATH = (
    Path(__file__).resolve().parents[2]
    / "agentic"
    / "evaluation"
    / "baselines"
    / "fixture_floors.json"
)


def _floors() -> dict:
    return json.loads(_FLOORS_PATH.read_text(encoding="utf-8"))


def _core() -> dict:
    """Floors apply to the core tier. The hard tier is bounded from above instead — the
    fixture policy is *expected* to fail it, so a floor there would be backwards."""
    return _floors()["core"]


def test_the_baseline_is_actually_deterministic() -> None:
    """
    The premise of zero-margin floors. If this fails, the floors are wrong before anything
    else is — they would be pinning one sample of a distribution.
    """
    runs = [run_agency_suite() for _ in range(3)]
    scores = [r.property_scores() for r in runs]

    assert all(s == scores[0] for s in scores), (
        f"fixture baseline varied across runs: {scores}. The floors assume determinism; "
        "either restore it or move the floors below the observed spread."
    )


def test_every_property_holds_its_floor() -> None:
    floors = _core()["properties"]
    observed = run_agency_suite(tier=CaseTier.core).property_scores()

    below = [
        f"{name}: floor {floor:.4f}, observed {observed.get(name, 0.0):.4f}"
        for name, floor in sorted(floors.items())
        if observed.get(name, 0.0) < floor
    ]

    assert not below, (
        "agency properties regressed below their committed floors "
        f"({_FLOORS_PATH.name}):\n  " + "\n  ".join(below)
    )


def test_overall_pass_rate_holds_its_floor() -> None:
    floor = _core()["pass_rate"]
    report = run_agency_suite(tier=CaseTier.core)

    assert report.pass_rate >= floor, (
        f"core pass rate {report.pass_rate:.4f} is below the committed floor {floor:.4f}; "
        f"failing cases: {[r.case_id for r in report.results if not r.passed]}"
    )


def test_the_hard_tier_keeps_its_headroom() -> None:
    """
    The ceiling, and the reason it points the opposite way to every other bound here.

    `suite_agency_v1` was saturated — a rule engine and a frontier model both scored 100% —
    so the hard tier exists to hold open a gap above "working". If `FixtureAgentPolicy`
    starts clearing hard cases, that gap is closing, and the two possible causes need
    opposite responses.
    """
    ceiling = _floors()["hard"]["max_pass_rate"]
    report = run_agency_suite(tier=CaseTier.hard)

    assert report.pass_rate <= ceiling, (
        f"the deterministic baseline now passes {report.pass_rate:.0%} of the hard tier, "
        f"above the committed ceiling of {ceiling:.0%} "
        f"(newly passing: {[r.case_id for r in report.results if r.passed]}).\n"
        "Either the deterministic policy genuinely improved — re-baseline deliberately and "
        "say so — or those cases have gone soft and no longer discriminate. Do not raise the "
        "ceiling to make this pass without deciding which."
    )


def test_the_floors_file_covers_every_agency_property() -> None:
    """
    A new `AgencyProperty` must arrive with a floor. Without this, adding a property would
    silently leave it ungated — the gap would look exactly like everything passing.
    """
    floors = set(_core()["properties"])
    declared = {p.value for p in AgencyProperty}

    assert floors == declared, (
        f"floors file and AgencyProperty disagree — missing floors: {sorted(declared - floors)}; "
        f"floors for unknown properties: {sorted(floors - declared)}"
    )


def test_a_critic_that_never_challenges_fails_the_suite() -> None:
    """
    The gap this property was added to close.

    Before `challenges_before_concluding` existed, disabling the critic entirely left the
    suite at 100%: the loop still reached `sufficient_evidence` at the same confidence, just
    by exhausting the candidate tools instead of testing the claim. `TerminationPolicy`
    accepts `tested or not unused`, so "ran everything" is an accepted route to sufficiency
    and the adversarial behaviour degraded silently.
    """

    class _NeverChallenges(FixtureAgentPolicy):
        def critique(self, *, strongest_claim, available_tools):  # noqa: ANN001, ANN201
            return CritiqueProposal(should_challenge=False, rationale="never challenges")

    report = run_agency_suite(policy=_NeverChallenges())

    assert report.property_scores().get("challenges_before_concluding") == 0.0
    assert report.pass_rate < 1.0, (
        "a critic that never challenges must not score a perfect suite; if it does, the "
        "adversarial property is unmeasured again"
    )


def test_every_floored_property_is_actually_exercised_by_a_case() -> None:
    """
    Guards the other direction: a floor on a property no case asserts is unenforceable, and
    would read as a passing gate while measuring nothing.
    """
    floors = set(_core()["properties"])
    exercised = set(run_agency_suite(tier=CaseTier.core).property_scores())

    assert floors <= exercised, (
        f"floors are declared for properties no case asserts: {sorted(floors - exercised)}. "
        "Add a case that exercises them, or remove the floor."
    )
