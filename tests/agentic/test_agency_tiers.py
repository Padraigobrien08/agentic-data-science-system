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
