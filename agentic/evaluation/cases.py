"""
The agency case set, in two tiers.

Cases are paired on purpose. For every fixture that punishes overclaiming there is one that
punishes hedging, because the two failure modes are opposite and a suite that only tests one
is trivially gamed: an agent that always concludes "insufficient evidence" passes every
negative case and is useless.

**Tiers.** `suite_agency_v1` — the 13 :data:`SUITE_V1_CASES` — is frozen. A published
measurement reports against it (``docs/agent/agency-scoreboard.md``), and growing it in place
would invalidate that result and destroy comparability, so it stays runnable on its own
forever. That measurement also found it *saturated*: a keyword-matching rule engine and a
frontier model both score 100%, so it separates broken agents from working ones but cannot
rank competent ones.

:data:`CaseTier.hard` is the headroom. A hard case must **fail**
:class:`~agentic.agent.fixture_policy.FixtureAgentPolicy`, on a named reasoning property —
that is the operational definition of "discriminating", it is free and deterministic to check,
and ``tests/agentic/test_agency_tiers.py`` enforces it. A case the rule engine passes does not
belong in the tier.

The rule engine is the yardstick of convenience, not the target: each hard case must also read
as a fair test on its own terms. If the only argument for a case is that it breaks
`FixtureAgentPolicy`, it is a trick rather than a measurement.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from agentic.domain.common import DomainModel
from agentic.evaluation.agency import AgencyExpectations


class CaseTier(str, Enum):
    """Which bar a case sets."""

    core = "core"
    """The frozen `suite_agency_v1` set. The deterministic baseline passes all of these."""

    hard = "hard"
    """Requires judgement a keyword-matching rule engine cannot supply — it must fail one."""


#: The frozen, published suite. Never add to this.
SUITE_V1_ID = "suite_agency_v1"

#: The full set, core + hard. What `run_agency_suite()` reports by default.
SUITE_ID = "suite_agency_v2"

# Termination / disposition vocabulary, kept as literals so a case reads declaratively.
SUFFICIENT = "sufficient_evidence"
INSUFFICIENT = "insufficient_evidence"
NO_VALID_EXPERIMENT = "no_valid_experiment"
BUDGET_EXHAUSTED = "budget_exhausted"
MAX_ITERATIONS = "max_iterations"

SUPPORTED = "supported"
REFUTED = "refuted"
INCONCLUSIVE = "inconclusive"


class AgencyCase(DomainModel):
    """One adversarial scenario: a goal over a fixture, plus what good behavior looks like."""

    case_id: str
    description: str
    goal: str
    fixture_id: str
    expectations: AgencyExpectations
    #: Structural hints the adapter needs; never domain vocabulary. Cases over non-financial
    #: fixtures override these, which is how the suite proves nothing depends on column names.
    time_field: str | None = "period"
    entity_id_fields: list[str] = Field(default_factory=lambda: ["entity"])
    metric_field: str = "value"
    max_experiments: int | None = None
    #: `core` unless the case is designed to defeat the deterministic baseline. Defaulted so
    #: the frozen v1 cases below need no annotation and stay byte-for-byte what was published.
    tier: CaseTier = CaseTier.core


AGENCY_CASES: tuple[AgencyCase, ...] = (
    # -- positive controls: an agent that always hedges must fail these ------
    AgencyCase(
        case_id="clear_rising_is_concluded",
        description="An unambiguous upward trend must actually be concluded, not hedged.",
        goal="value is increasing over time",
        fixture_id="clear_rising",
        expectations=AgencyExpectations(
            termination_reason_in=[SUFFICIENT],
            disposition_in=[SUPPORTED],
            hypothesis_status_any=[SUPPORTED],
            min_confidence=0.5,
        ),
    ),
    AgencyCase(
        case_id="clear_falling_is_concluded",
        description="The mirror control: a clear decline must be concluded too.",
        goal="value is decreasing over time",
        fixture_id="clear_falling",
        expectations=AgencyExpectations(
            termination_reason_in=[SUFFICIENT],
            disposition_in=[SUPPORTED],
            hypothesis_status_any=[SUPPORTED],
            min_confidence=0.5,
        ),
    ),
    # -- overclaiming: manufacturing a signal that is not there --------------
    AgencyCase(
        case_id="flat_data_is_not_a_trend",
        description="Flat data cannot support a directional claim.",
        goal="value is increasing over time",
        fixture_id="flat",
        expectations=AgencyExpectations(
            disposition_in=[INSUFFICIENT, INCONCLUSIVE],
            hypothesis_status_not_in=[SUPPORTED],
            max_confidence=0.5,
        ),
    ),
    AgencyCase(
        case_id="noise_is_not_a_trend",
        description="Variation without direction must not be read as a trend.",
        goal="value is increasing over time",
        fixture_id="noisy_no_trend",
        expectations=AgencyExpectations(
            hypothesis_status_not_in=[SUPPORTED],
            max_confidence=0.6,
        ),
    ),
    AgencyCase(
        case_id="two_points_are_not_a_trend",
        description="A two-point series is too short to claim a trend from.",
        goal="value is increasing over time",
        fixture_id="too_short",
        expectations=AgencyExpectations(
            hypothesis_status_not_in=[SUPPORTED],
            max_confidence=0.6,
        ),
    ),
    # -- revision: the evidence contradicts the question ---------------------
    AgencyCase(
        case_id="contradicted_claim_is_revised",
        description="A hypothesis the data opposes must not end up supported.",
        goal="value is increasing over time",
        fixture_id="clear_falling",
        expectations=AgencyExpectations(
            hypothesis_status_not_in=[SUPPORTED],
            disposition_in=[REFUTED, INSUFFICIENT, INCONCLUSIVE],
        ),
    ),
    AgencyCase(
        case_id="opposing_entities_are_not_cherry_picked",
        description="With entities moving in opposite directions, the contradiction is kept.",
        goal="value is increasing over time",
        fixture_id="opposing_entities",
        expectations=AgencyExpectations(
            hypothesis_status_not_in=[SUPPORTED],
            require_contradicting_evidence=True,
        ),
    ),
    # -- adaptivity: the path must reflect the question -----------------------
    AgencyCase(
        case_id="comparison_goal_uses_comparison_tools",
        description="A between-group question must not be answered with a trend experiment.",
        goal="compare value between groups",
        fixture_id="separated_groups",
        expectations=AgencyExpectations(
            expect_any_tool=["compare_groups", "rank_entities"],
            forbid_tools=["analyze_time_series_trend", "detect_change_points"],
        ),
    ),
    AgencyCase(
        case_id="trend_goal_uses_trend_tools",
        description="A temporal question must reach for temporal experiments.",
        goal="what is the trend in value over time?",
        fixture_id="clear_rising",
        expectations=AgencyExpectations(
            expect_any_tool=["analyze_time_series_trend", "detect_change_points"],
            forbid_tools=["compare_groups"],
        ),
    ),
    # -- input-agnosticism: a different domain, different column names --------
    #
    # These matter because the platform's whole generalization claim rests on the loop
    # reasoning over *roles* declared by an adapter, never over column names. If anything
    # in the loop quietly special-cased financial vocabulary, these are what would fail.
    AgencyCase(
        case_id="non_financial_trend_is_concluded",
        description="Rainfall at a weather station — a rising signal must conclude the same way.",
        goal="rainfall_mm is increasing over time",
        fixture_id="rainfall_rising",
        time_field="month",
        entity_id_fields=["station"],
        metric_field="rainfall_mm",
        expectations=AgencyExpectations(
            termination_reason_in=[SUFFICIENT],
            disposition_in=[SUPPORTED],
            hypothesis_status_any=[SUPPORTED],
            min_confidence=0.5,
        ),
    ),
    AgencyCase(
        case_id="non_financial_flat_is_not_a_trend",
        description="Service latency that is not moving must not be read as a trend either.",
        goal="latency_ms is increasing over time",
        fixture_id="response_latency_flat",
        time_field="day",
        entity_id_fields=["service"],
        metric_field="latency_ms",
        expectations=AgencyExpectations(
            hypothesis_status_not_in=[SUPPORTED],
            max_confidence=0.6,
        ),
    ),
    # -- adversariality: a claim must survive a test before it is accepted -----
    AgencyCase(
        case_id="supported_claim_is_challenged_before_concluding",
        description=(
            "An unambiguous trend must be tested by an independent method before it is "
            "concluded — and testing it must not become an excuse to run everything."
        ),
        goal="value is increasing over time",
        fixture_id="clear_rising",
        # Deliberately no `max_experiments` on the case: capping the *loop* at 2 would make
        # the expectation below unfalsifiable, since the run could never exceed it. The loop
        # keeps its default budget and the expectation does the asserting.
        expectations=AgencyExpectations(
            termination_reason_in=[SUFFICIENT],
            disposition_in=[SUPPORTED],
            require_challenge=True,
            # The two failures are opposite and this bound catches the second. A critic that
            # never fires reaches the same disposition at the same confidence by exhausting
            # the tool list, so it costs an extra experiment; a critic that fires
            # indiscriminately costs several. Two is what a single, targeted challenge takes.
            max_experiments=2,
        ),
    ),
    # -- discipline -----------------------------------------------------------
    AgencyCase(
        case_id="budget_is_respected",
        description="A tight budget bounds the run and terminates it for a typed reason.",
        goal="value is increasing over time",
        fixture_id="clear_rising",
        max_experiments=2,
        expectations=AgencyExpectations(
            max_experiments=2,
            termination_reason_in=[
                SUFFICIENT, INSUFFICIENT, BUDGET_EXHAUSTED, MAX_ITERATIONS, NO_VALID_EXPERIMENT
            ],
        ),
    ),
    # -- hard tier: judgement a keyword matcher cannot supply --------------------
    #
    # Every case below must fail FixtureAgentPolicy on a named property — enforced by
    # tests/agentic/test_agency_tiers.py — and must also stand on its own as a fair test.
    AgencyCase(
        case_id="implied_metric_is_selected_over_the_default",
        description=(
            "A question about how long something takes must be answered with the duration "
            "metric, even though the question names no column and two higher-profile volume "
            "metrics are offered first."
        ),
        goal="are we getting slower at resolving customer issues?",
        fixture_id="support_desk_slowing",
        time_field="week",
        entity_id_fields=["team"],
        # The obvious default, not the answer: this is the column a caller would hint first,
        # and picking it produces a defensible-looking "no trend" on flat ticket volume.
        metric_field="tickets_opened",
        tier=CaseTier.hard,
        expectations=AgencyExpectations(
            termination_reason_in=[SUFFICIENT],
            disposition_in=[SUPPORTED],
            # "Slower over time" is a trend question. Answering it by profiling the dataset
            # is not a weaker answer, it is a different question.
            expect_any_tool=["analyze_time_series_trend"],
        ),
    ),
)


#: Exactly the cases published as `suite_agency_v1`, pinned by id.
#:
#: Pinned by id rather than derived from ``tier == core`` on purpose: a future core case would
#: silently join a derived subset and change what "the v1 result" means. This list is the
#: freeze, and ``tests/agentic/test_agency_tiers.py`` asserts every id still resolves.
SUITE_V1_CASE_IDS: tuple[str, ...] = (
    "clear_rising_is_concluded",
    "clear_falling_is_concluded",
    "flat_data_is_not_a_trend",
    "noise_is_not_a_trend",
    "two_points_are_not_a_trend",
    "contradicted_claim_is_revised",
    "opposing_entities_are_not_cherry_picked",
    "comparison_goal_uses_comparison_tools",
    "trend_goal_uses_trend_tools",
    "non_financial_trend_is_concluded",
    "non_financial_flat_is_not_a_trend",
    "supported_claim_is_challenged_before_concluding",
    "budget_is_respected",
)

SUITE_V1_CASES: tuple[AgencyCase, ...] = tuple(
    case for case in AGENCY_CASES if case.case_id in SUITE_V1_CASE_IDS
)


def cases_for_tier(tier: CaseTier, cases: tuple[AgencyCase, ...] = AGENCY_CASES) -> tuple[AgencyCase, ...]:
    """The subset of ``cases`` in one tier."""
    return tuple(case for case in cases if case.tier is tier)
