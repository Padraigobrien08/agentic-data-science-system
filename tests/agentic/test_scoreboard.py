"""
Multi-trial aggregation, driven from synthetic reports.

The property worth protecting is that a flapping case stays visible. Averaging is the natural
thing to do with N runs and it is exactly wrong here: a case that passes two trials in three
and one that passes deterministically both read as "mostly fine" once collapsed to a number,
and only one of them is a result you can publish. So these tests pin stability detection
first, and the arithmetic second.
"""

from __future__ import annotations

from agentic.agent.observer import InvestigationEnded
from agentic.domain import InvestigationStatus, TerminationReason
from agentic.evaluation.agency import AgencyCaseResult, AgencyProperty, AgencyReport, PropertyOutcome
from agentic.evaluation.scoreboard import (
    MetricsObserver,
    RunMetrics,
    Scoreboard,
    _p95,
    aggregate_trials,
)


def _result(case_id: str, passed: bool, *, prop=AgencyProperty.calibrated_confidence) -> AgencyCaseResult:
    return AgencyCaseResult(
        case_id=case_id,
        passed=passed,
        outcomes=[PropertyOutcome(property=prop, passed=passed)],
    )


def _report(*results: AgencyCaseResult) -> AgencyReport:
    return AgencyReport(
        suite_id="suite_agency_v1",
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        results=list(results),
    )


def _ended(*, cost: float = 0.0, elapsed: float = 0.0, partial: bool = False) -> InvestigationEnded:
    return InvestigationEnded(
        investigation_id="inv",
        status=InvestigationStatus.converged,
        termination_reason=TerminationReason.sufficient_evidence,
        iterations=1,
        experiments_completed=1,
        experiments_failed=0,
        hypotheses=1,
        evidence=1,
        elapsed_seconds=elapsed,
        cost_usd=cost,
        model_calls=2,
        partial=partial,
    )


# -- stability ---------------------------------------------------------------


def test_a_unanimously_passing_case_is_not_reported_as_unstable() -> None:
    reports = [_report(_result("a", True)) for _ in range(3)]

    card = aggregate_trials("fixture", reports)

    assert card.unstable_cases == []
    assert card.fully_stable


def test_a_unanimously_failing_case_is_also_stable() -> None:
    """Consistently wrong is a different problem from flapping, and must not be conflated."""
    reports = [_report(_result("a", False)) for _ in range(3)]

    card = aggregate_trials("fixture", reports)

    assert card.unstable_cases == []
    assert card.mean_pass_rate == 0.0


def test_a_flapping_case_is_surfaced_with_its_counts() -> None:
    reports = [_report(_result("a", True)), _report(_result("a", False)), _report(_result("a", True))]

    card = aggregate_trials("model", reports)

    assert [c.case_id for c in card.unstable_cases] == ["a"]
    assert card.unstable_cases[0].passed_trials == 2
    assert card.unstable_cases[0].total_trials == 3
    assert not card.fully_stable


def test_only_the_flapping_case_is_listed() -> None:
    reports = [
        _report(_result("steady", True), _result("flaky", True)),
        _report(_result("steady", True), _result("flaky", False)),
    ]

    card = aggregate_trials("model", reports)

    assert [c.case_id for c in card.unstable_cases] == ["flaky"]


# -- arithmetic --------------------------------------------------------------


def test_property_means_average_across_reports() -> None:
    reports = [_report(_result("a", True)), _report(_result("a", False))]

    card = aggregate_trials("model", reports)

    assert card.property_means["calibrated_confidence"] == 0.5


def test_a_property_no_case_asserts_is_absent_rather_than_zero() -> None:
    card = aggregate_trials("fixture", [_report(_result("a", True))])

    assert "calibrated_confidence" in card.property_means
    assert "respects_budget" not in card.property_means


def test_cost_is_totalled_and_averaged_per_trial() -> None:
    reports = [_report(_result("a", True)) for _ in range(2)]
    metrics = [RunMetrics(cost_usd=0.10), RunMetrics(cost_usd=0.30)]

    card = aggregate_trials("model", reports, metrics)

    assert card.total_cost_usd == 0.4
    assert card.mean_cost_usd == 0.2


def test_p95_is_nearest_rank() -> None:
    assert _p95([]) == 0.0
    assert _p95([5.0]) == 5.0
    # n=20 -> rank 19; the 19th smallest of 1..20 is 19.
    assert _p95([float(i) for i in range(1, 21)]) == 19.0
    # small n -> the maximum, which is the honest answer for three samples
    assert _p95([1.0, 9.0, 3.0]) == 9.0


def test_no_reports_yields_an_empty_card_rather_than_raising() -> None:
    card = aggregate_trials("model", [])

    assert card.trials == 0
    assert card.mean_pass_rate == 0.0


def test_truncation_is_carried_onto_the_card() -> None:
    card = aggregate_trials("model", [_report(_result("a", True))], truncated=True)

    assert card.truncated


# -- observer ----------------------------------------------------------------


def test_the_metrics_observer_captures_terminal_runs() -> None:
    observer = MetricsObserver()

    observer.on_investigation_end(_ended(cost=0.02, elapsed=1.5))

    assert len(observer.runs) == 1
    assert observer.runs[0].cost_usd == 0.02
    assert observer.runs[0].elapsed_seconds == 1.5


def test_partial_returns_are_not_counted_as_runs() -> None:
    """A resumable partial belongs to the run it will finish in, not to a run of its own."""
    observer = MetricsObserver()

    observer.on_investigation_end(_ended(partial=True))

    assert observer.runs == []


def test_drain_resets_so_one_observer_can_span_trials() -> None:
    observer = MetricsObserver()
    observer.on_investigation_end(_ended(cost=0.01))

    first = observer.drain()

    assert len(first) == 1
    assert observer.drain() == []


# -- rendering ---------------------------------------------------------------


def test_markdown_table_lists_every_policy_row() -> None:
    board = Scoreboard(
        suite_id="suite_agency_v1",
        rows=[
            aggregate_trials("fixture", [_report(_result("a", True))]),
            aggregate_trials("model-x", [_report(_result("a", False))]),
        ],
    )

    text = board.to_markdown()

    assert "fixture" in text
    assert "model-x" in text
    assert "calibrated_confidence" in text


def test_markdown_calls_out_unstable_cases_explicitly() -> None:
    board = Scoreboard(
        suite_id="suite_agency_v1",
        rows=[aggregate_trials("model-x", [_report(_result("a", True)), _report(_result("a", False))])],
    )

    text = board.to_markdown()

    assert "Unstable cases" in text
    assert "passed 1/2 trials" in text


def test_markdown_flags_a_truncated_row() -> None:
    board = Scoreboard(
        suite_id="suite_agency_v1",
        rows=[aggregate_trials("model-x", [_report(_result("a", True))], truncated=True)],
    )

    text = board.to_markdown()

    assert "Truncated by the cost ceiling" in text


def test_empty_scoreboard_renders_without_raising() -> None:
    assert "No results" in Scoreboard(suite_id="suite_agency_v1").to_markdown()
