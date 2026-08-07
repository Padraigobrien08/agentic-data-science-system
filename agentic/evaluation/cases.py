"""
``suite_agency_v1`` — the agency case set.

Cases are paired on purpose. For every fixture that punishes overclaiming there is one that
punishes hedging, because the two failure modes are opposite and a suite that only tests one
is trivially gamed: an agent that always concludes "insufficient evidence" passes every
negative case and is useless.
"""

from __future__ import annotations

from pydantic import Field

from agentic.domain.common import DomainModel
from agentic.evaluation.agency import AgencyExpectations

SUITE_ID = "suite_agency_v1"

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
)
