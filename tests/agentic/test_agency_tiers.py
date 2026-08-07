"""
The hard tier's admission rule, enforced.

`suite_agency_v1` turned out to be saturated: a keyword-matching rule engine and a frontier
model both scored 100% on every property. The instrument was fine — it later caught a prompt
defect worth 38 points — but it had no headroom above "working", so it could not rank.

The hard tier is that headroom, and "harder" needs an operational definition or it degrades
into taste. The definition is: **a hard case must fail `FixtureAgentPolicy`**. That is free,
deterministic, and checkable on every PR, which is why it lives here rather than in a review
checklist.

Two guards keep the rule honest. A case must fail on a named `AgencyProperty` — a case that
fails because the loop crashed or a tool was unavailable is measuring plumbing, not reasoning.
And the rule engine is the yardstick of convenience, not the target: a case whose only claim
to a place is that it defeats `FixtureAgentPolicy` is a trick, which is why each one also
carries a description that has to read as a fair test on its own. That second guard is human;
this file enforces the first.
"""

from __future__ import annotations

import pytest

from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.evaluation.cases import (
    AGENCY_CASES,
    SUITE_V1_CASE_IDS,
    SUITE_V1_CASES,
    CaseTier,
    cases_for_tier,
)
from agentic.evaluation.fixtures import FIXTURES, build_fixture
from agentic.evaluation.runner import run_case


def _hard_cases():
    return cases_for_tier(CaseTier.hard)


# -- the frozen suite --------------------------------------------------------


def test_suite_v1_is_frozen_at_its_published_size() -> None:
    """
    `docs/agent/agency-scoreboard.md` publishes a measurement over 13 cases. Growing that set
    in place would invalidate the published result rather than extend it.
    """
    assert len(SUITE_V1_CASE_IDS) == 13
    assert len(SUITE_V1_CASES) == 13


def test_every_frozen_id_still_resolves_to_a_case() -> None:
    """A rename would otherwise shrink the frozen suite silently, and the count test above
    would keep passing on the declared ids alone."""
    known = {c.case_id for c in AGENCY_CASES}
    missing = [cid for cid in SUITE_V1_CASE_IDS if cid not in known]

    assert not missing, (
        f"frozen suite_agency_v1 ids no longer exist: {missing}. The published scoreboard "
        "measures these; restore the ids rather than editing the frozen list."
    )


def test_the_frozen_suite_is_all_core_tier() -> None:
    assert all(c.tier is CaseTier.core for c in SUITE_V1_CASES)


# -- the admission rule ------------------------------------------------------


def test_the_hard_tier_is_not_empty() -> None:
    """An empty tier would make every assertion below vacuously true."""
    assert _hard_cases(), "the hard tier has no cases; the headroom claim is unbacked"


@pytest.mark.parametrize("case", _hard_cases(), ids=lambda c: c.case_id)
def test_every_hard_case_defeats_the_deterministic_baseline(case) -> None:
    """The admission rule. A case the rule engine passes belongs in the core tier."""
    result = run_case(case, policy=FixtureAgentPolicy())

    assert not result.passed, (
        f"{case.case_id!r} is tagged hard but FixtureAgentPolicy passes it, so it does not "
        "discriminate. Either move it to the core tier or sharpen it."
    )


@pytest.mark.parametrize("case", _hard_cases(), ids=lambda c: c.case_id)
def test_every_hard_case_fails_on_a_named_property(case) -> None:
    """
    Fails for a *reasoning* reason. A case that fails with no scored outcomes asserted nothing
    — the loop errored, or the expectations were empty — and would count as discrimination
    while measuring plumbing.
    """
    result = run_case(case, policy=FixtureAgentPolicy())

    assert result.outcomes, f"{case.case_id!r} scored no properties at all"
    assert result.failures, f"{case.case_id!r} failed without any property failing"


def test_the_hard_tier_spans_more_than_one_property() -> None:
    """
    Breadth, so the tier cannot be cleared by one narrow fix.

    The plan for this phase asked for coverage across three *policy methods*. That turned out
    not to be fairly constructible — see the 28-02 summary: `expected_information_gain` is a
    pure function of a tool's position in the intent list, so a `select_experiment`
    discriminator would test disagreement with the planner's priority rather than reasoning;
    and a `generate_hypotheses` one is structurally unwinnable, because the planner
    parameterises every tool from a single `metric_hint` and a second hypothesis about a
    second metric can never be investigated by any policy.

    Breadth is therefore asserted over the properties the tier exercises, which is the thing
    that actually stops a single narrow fix from clearing it.
    """
    failed_properties = {
        outcome.property
        for case in _hard_cases()
        for outcome in run_case(case, policy=FixtureAgentPolicy()).failures
    }

    assert len(failed_properties) >= 3, (
        f"the hard tier only exercises {sorted(p.value for p in failed_properties)}; a tier "
        "this narrow is cleared by one fix and measures less than it appears to"
    )


def test_the_hard_tier_punishes_overclaiming_as_well_as_under_reasoning() -> None:
    """
    The pairing discipline the whole suite is built on, applied to the hard tier.

    Without a case where declining is correct, a policy could clear the tier by being
    uniformly more assertive — which is the exact failure the core tier's negative controls
    exist to catch.
    """
    declining = [
        c
        for c in _hard_cases()
        if c.expectations.max_confidence is not None
        or "supported" in c.expectations.hypothesis_status_not_in
    ]

    assert declining, (
        "no hard case rewards declining, so the tier can be cleared by always asserting more"
    )


def test_hard_cases_are_described_in_their_own_terms() -> None:
    """
    The human guard, given the smallest possible mechanical footing: a case needs a description
    substantial enough to argue it is a fair test. It cannot check that the argument is *good*
    — that is a review job — but it can stop an undescribed case being added silently.
    """
    thin = [c.case_id for c in _hard_cases() if len(c.description) < 60]

    assert not thin, (
        f"hard cases without a real description: {thin}. State the analytical judgement the "
        "case requires, so a reader can agree it is fair without knowing FixtureAgentPolicy exists."
    )


# -- fixtures ----------------------------------------------------------------


@pytest.mark.parametrize("fixture_id", sorted(FIXTURES), ids=str)
def test_every_fixture_is_deterministic(fixture_id: str) -> None:
    """
    The offline claim rests on this. A fixture seeded from the clock, or from an unseeded RNG,
    would make a case flap and be indistinguishable from a policy that reasons inconsistently
    — the exact confusion the multi-trial stability tracking exists to resolve.
    """
    first = build_fixture(fixture_id)
    second = build_fixture(fixture_id)

    assert first.equals(second), f"fixture {fixture_id!r} is not reproducible across builds"


@pytest.mark.parametrize("case", _hard_cases(), ids=lambda c: c.case_id)
def test_every_hard_case_uses_a_registered_fixture(case) -> None:
    assert case.fixture_id in FIXTURES, (
        f"{case.case_id!r} references unregistered fixture {case.fixture_id!r}"
    )
