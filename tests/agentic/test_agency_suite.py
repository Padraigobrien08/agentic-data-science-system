"""
The agency evaluation suite, and whether it is worth anything.

A suite that only proves the current agent passes is theatre: it would pass equally if the
checks were vacuous. So the important tests here are the **discrimination** tests — they run
deliberately bad agents and assert the suite catches them, and they are what makes the
baseline result meaningful.

Two failure modes are covered, because they are opposite and a suite that only catches one is
trivially gamed:

* an agent that **hedges** (never concludes) must fail the positive controls;
* an agent that **ignores the question** must fail the adaptivity cases.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.agent.policy import AnalysisIntent, ExperimentChoice, GoalInterpretation
from agentic.evaluation import (
    AGENCY_CASES,
    SUITE_ID,
    AgencyExpectations,
    AgencyProperty,
    build_fixture,
    format_report,
    run_agency_suite,
    run_case,
)
from agentic.evaluation.fixtures import FIXTURES

# -- deliberately bad agents -------------------------------------------------


class HedgingPolicy(FixtureAgentPolicy):
    """Never selects an experiment, so it can never conclude anything.

    This is the agent a negative-only suite would score perfectly: never wrong, never useful.
    """

    def select_experiment(self, *, goal_summary, candidates):
        return ExperimentChoice(request_index=None, rationale="declined")


class AlwaysTrendPolicy(FixtureAgentPolicy):
    """Reads every goal as a trend question, whatever was actually asked."""

    def interpret_goal(self, goal_text, *, capability_summary):
        return GoalInterpretation(intent=AnalysisIntent.trend, rationale="fixed")


# -- the baseline ------------------------------------------------------------


def test_the_deterministic_baseline_passes_the_suite() -> None:
    report = run_agency_suite()
    assert report.suite_id == SUITE_ID
    assert report.failed == 0, format_report(report)
    assert report.total == len(AGENCY_CASES)


def test_every_property_is_exercised_by_the_suite() -> None:
    """A property nothing asserts is a property nobody is measuring."""
    report = run_agency_suite()
    exercised = set(report.property_scores())
    expected = {p.value for p in AgencyProperty}
    assert expected - exercised == set(), f"unexercised properties: {sorted(expected - exercised)}"


# -- discrimination: the tests that make the suite meaningful ----------------


def test_a_hedging_agent_fails_the_positive_controls() -> None:
    """
    The reason positive controls exist. An agent that always concludes "insufficient
    evidence" is never wrong on the adversarial cases, so without these it would score 100%.
    """
    report = run_agency_suite(policy=HedgingPolicy())
    failed = {r.case_id for r in report.results if not r.passed}

    assert "clear_rising_is_concluded" in failed
    assert "clear_falling_is_concluded" in failed
    assert report.failed > 0
    assert report.pass_rate < 1.0


def test_a_hedging_agent_is_caught_by_confidence_calibration() -> None:
    report = run_agency_suite(policy=HedgingPolicy())
    rising = next(r for r in report.results if r.case_id == "clear_rising_is_concluded")
    reasons = {o.property for o in rising.failures}

    assert AgencyProperty.calibrated_confidence in reasons
    assert AgencyProperty.reaches_the_right_disposition in reasons


def test_an_agent_that_ignores_the_question_fails_adaptivity() -> None:
    report = run_agency_suite(policy=AlwaysTrendPolicy())
    failed = {r.case_id for r in report.results if not r.passed}

    assert "comparison_goal_uses_comparison_tools" in failed
    comparison = next(
        r for r in report.results if r.case_id == "comparison_goal_uses_comparison_tools"
    )
    assert AgencyProperty.path_adapts_to_goal in {o.property for o in comparison.failures}


def test_bad_agents_score_strictly_worse_than_the_baseline() -> None:
    baseline = run_agency_suite().pass_rate
    for policy in (HedgingPolicy(), AlwaysTrendPolicy()):
        assert run_agency_suite(policy=policy).pass_rate < baseline


# -- fixtures ----------------------------------------------------------------


@pytest.mark.parametrize("fixture_id", sorted(FIXTURES))
def test_fixtures_are_deterministic(fixture_id: str) -> None:
    """Including the noisy one — it is seeded, so a verdict never depends on the run."""
    first = build_fixture(fixture_id)
    second = build_fixture(fixture_id)
    pd.testing.assert_frame_equal(first, second)


@pytest.mark.parametrize("fixture_id", sorted(FIXTURES))
def test_fixtures_are_non_empty_and_shaped(fixture_id: str) -> None:
    """Structure, not names: an entity column, a time column, and a metric column."""
    frame = build_fixture(fixture_id)
    assert not frame.empty
    assert len(frame.columns) >= 3


def test_non_financial_fixtures_use_their_own_vocabulary() -> None:
    """
    The input-agnosticism claim in one assertion: these fixtures share no column name with
    the generic ones, so a case passing over them cannot be relying on column names.
    """
    generic = set(build_fixture("clear_rising").columns)
    for fixture_id in ("rainfall_rising", "response_latency_flat"):
        assert not (set(build_fixture(fixture_id).columns) & generic), fixture_id


def test_non_financial_cases_are_in_the_suite() -> None:
    from agentic.evaluation import AGENCY_CASES as cases

    non_financial = {c.case_id for c in cases if c.fixture_id in
                     ("rainfall_rising", "response_latency_flat")}
    assert non_financial, "the suite must exercise a non-financial dataset"
    assert all(c.metric_field != "value" for c in cases if c.case_id in non_financial)


def test_unknown_fixture_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown agency fixture"):
        build_fixture("no_such_fixture")


def test_noisy_fixture_actually_has_no_trend() -> None:
    """Guard the fixture's own premise: if the seed drifted into a trend, the case is invalid."""
    import numpy as np

    frame = build_fixture("noisy_no_trend")
    y = frame["value"].to_numpy()
    slope = np.polyfit(np.arange(len(y)), y, 1)[0]
    assert abs(slope) < 0.5, f"the 'no trend' fixture has a slope of {slope}"


def test_opposing_fixture_actually_opposes() -> None:
    frame = build_fixture("opposing_entities")
    assert frame["entity"].nunique() == 2
    first = frame[frame["entity"] == "A"]["value"].to_numpy()
    second = frame[frame["entity"] == "B"]["value"].to_numpy()
    assert (first[-1] - first[0]) > 0 > (second[-1] - second[0])


# -- scoring mechanics -------------------------------------------------------


def test_a_case_only_asserts_what_it_declares() -> None:
    """Expectations are opt-in, so a case probing one property does not assert others."""
    case = next(c for c in AGENCY_CASES if c.case_id == "noise_is_not_a_trend")
    result = run_case(case)
    asserted = {o.property for o in result.outcomes}

    assert AgencyProperty.path_adapts_to_goal not in asserted
    assert AgencyProperty.revises_under_contradiction in asserted


def test_empty_expectations_measure_nothing() -> None:
    """
    Documents the semantics so it is never mistaken for a signal: a case that asserts nothing
    passes, but records no outcomes. A silently-empty expectation set is the way an eval suite
    rots into theatre, so the distinction is explicit.
    """
    from agentic.evaluation.cases import AgencyCase

    case = AgencyCase(
        case_id="empty", description="", goal="value is increasing over time",
        fixture_id="flat", expectations=AgencyExpectations(no_repeated_tools=False),
    )
    result = run_case(case)

    assert result.outcomes == [], "nothing was asserted, so nothing should be reported"
    assert result.passed, "a vacuous case passes — which is why coverage is asserted separately"


def test_report_math_and_property_breakdown() -> None:
    report = run_agency_suite()
    assert report.passed + report.failed == report.total
    assert 0.0 <= report.pass_rate <= 1.0
    scores = report.property_scores()
    assert scores and all(0.0 <= v <= 1.0 for v in scores.values())


def test_results_record_observations_for_diagnosis() -> None:
    """A failure must be diagnosable without re-running the case."""
    report = run_agency_suite(policy=HedgingPolicy())
    failing = next(r for r in report.results if not r.passed)

    assert failing.observed_termination is not None
    assert failing.failures
    assert all(o.detail for o in failing.failures), "every failure must say what went wrong"


def test_formatted_report_names_failures_and_reasons() -> None:
    text = format_report(run_agency_suite(policy=HedgingPolicy()))
    assert "clear_rising_is_concluded" in text
    assert "Per-property pass rate:" in text
    assert "Failures:" in text


def test_report_is_serializable() -> None:
    payload = run_agency_suite().model_dump(mode="json")
    assert payload["suite_id"] == SUITE_ID
    assert isinstance(payload["results"], list)
    assert payload["results"][0]["case_id"]


def test_case_ids_are_unique() -> None:
    ids = [c.case_id for c in AGENCY_CASES]
    assert len(set(ids)) == len(ids)


# -- direction parsing -------------------------------------------------------
#
# Regression: direction keywords were matched as substrings, so "rainfall_mm is increasing"
# matched "fall" and the loop read a rising series as a claim about decline — rejecting a
# hypothesis the data supported. Found by the non-financial agency case, which is exactly
# what those cases exist for.


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # the original failure and its family: a direction word inside a metric name
        ("rainfall_mm is increasing over time", "up"),
        ("shortfall is increasing", "up"),
        ("downtime is increasing", "up"),
        ("upstream_value is decreasing", "down"),
        ("download_count is rising", "up"),
        # "growth" is a noun in metric names, not a claim; "growing" is a claim
        ("revenue_growth_qoq is deteriorating", "down"),
        ("value is growing", "up"),
        # ordinary directional claims
        ("value is decreasing over time", "down"),
        ("revenue is falling", "down"),
        ("margins shrank", "down"),
        ("latency dropped", "down"),
        ("value is up", "up"),
        ("value is down", "down"),
        # non-directional
        ("compare value between groups", None),
        ("profile the dataset", None),
        ("", None),
    ],
)
def test_direction_is_parsed_on_word_boundaries(text: str, expected) -> None:
    from agentic.agent.direction import parse_direction

    assert parse_direction(text) == expected


def test_direction_sign_matches_parse_direction() -> None:
    """The two call sites (goal interpretation, evidence updating) must never disagree."""
    from agentic.agent.direction import direction_sign, parse_direction

    for text in ("value is increasing", "value is decreasing", "compare groups"):
        sign = direction_sign(text)
        direction = parse_direction(text)
        assert sign == (None if direction is None else (1 if direction == "up" else -1))


def test_earliest_direction_wins_when_both_appear() -> None:
    """Fixed precedence made the answer depend on which list was checked first."""
    from agentic.agent.direction import parse_direction

    assert parse_direction("increasing then decreasing") == "up"
    assert parse_direction("decreasing then increasing") == "down"
