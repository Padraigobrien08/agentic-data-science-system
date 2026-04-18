"""Runner degradation routing and summary/report output contracts."""

from __future__ import annotations

from edgar_project.evaluation.runner import EvaluationRunner
from edgar_project.evaluation.schemas import (
    BenchmarkSuite,
    EvaluationResult,
    EvaluationStatus,
    InputMode,
    ValidationDegradationClass,
    ValidationObservation,
)
from edgar_project.evaluation.summary_report import (
    format_benchmark_cli_summary,
    format_console_report,
    render_markdown_report,
    summary_json_blob,
)


def _live_case() -> dict:
    return {
        "case_id": "live_case",
        "input": {
            "mode": "live",
            "tickers": ["AAPL"],
            "goal": "Check live policy",
            "policy": {
                "requires_explicit_live_opt_in": True,
                "fair_access_policy": "sec_fair_access_operator_invoked",
                "allow_merge_blocking": False,
                "normal_user_visible": False,
                "freshness_window_seconds": 300,
            },
        },
    }


def test_run_case_marks_live_without_opt_in_as_policy_skipped() -> None:
    suite = BenchmarkSuite.model_validate({"suite_id": "policy_guard", "cases": [_live_case()]})
    runner = EvaluationRunner(suite=suite)

    result = runner.run_case(suite.cases[0])

    assert result.status == EvaluationStatus.skipped
    assert result.degradation_class == ValidationDegradationClass.policy_skipped
    assert result.policy is not None
    assert result.observation is not None
    assert result.observation.freshness_window_seconds == 300
    assert "requires explicit --allow-live opt-in" in result.message


def test_run_case_with_allow_live_keeps_current_not_implemented_skip() -> None:
    suite = BenchmarkSuite.model_validate({"suite_id": "policy_guard", "cases": [_live_case()]})
    runner = EvaluationRunner(suite=suite, allow_live_cases=True)

    result = runner.run_case(suite.cases[0])

    assert result.status == EvaluationStatus.skipped
    assert result.degradation_class == ValidationDegradationClass.none
    assert "not implemented yet" in result.message


def test_classify_degradation_class_distinguishes_product_stale_and_upstream() -> None:
    runner = EvaluationRunner(suite=BenchmarkSuite(suite_id="classification"))

    fixture_case = suite_case = BenchmarkSuite.model_validate(
        {
            "suite_id": "classification",
            "cases": [
                {
                    "case_id": "fixture_case",
                    "input": {
                        "mode": "fixture",
                        "fixture_paths": {"features_csv": "fixtures/example.csv"},
                    },
                }
            ],
        }
    ).cases[0]

    failed_result = EvaluationResult(case_id="fixture_case", status=EvaluationStatus.failed)
    assert (
        runner._classify_degradation_class(fixture_case, failed_result)
        == ValidationDegradationClass.product_regression
    )

    live_case = BenchmarkSuite.model_validate({"suite_id": "classification", "cases": [_live_case()]}).cases[0]
    stale_result = EvaluationResult(
        case_id="live_case",
        status=EvaluationStatus.skipped,
        observation=ValidationObservation(source_age_seconds=301, freshness_window_seconds=300),
    )
    assert runner._classify_degradation_class(live_case, stale_result) == ValidationDegradationClass.policy_skipped

    live_runner = EvaluationRunner(suite=BenchmarkSuite(suite_id="classification"), allow_live_cases=True)
    stale_result = EvaluationResult(
        case_id="live_case",
        status=EvaluationStatus.skipped,
        observation=ValidationObservation(source_age_seconds=301, freshness_window_seconds=300),
    )
    assert live_runner._classify_degradation_class(live_case, stale_result) == ValidationDegradationClass.stale_source

    upstream_result = EvaluationResult(
        case_id="live_case",
        status=EvaluationStatus.error,
        metadata={"upstream_error_code": "sec_rate_limited"},
    )
    assert (
        live_runner._classify_degradation_class(live_case, upstream_result)
        == ValidationDegradationClass.upstream_sec_degraded
    )


def test_summary_helpers_surface_degradation_counts_and_labels() -> None:
    results = [
        EvaluationResult(
            case_id="fixture_ok",
            status=EvaluationStatus.passed,
            degradation_class=ValidationDegradationClass.none,
            message="passed",
            elapsed_seconds=0.21,
        ),
        EvaluationResult(
            case_id="live_policy",
            status=EvaluationStatus.skipped,
            degradation_class=ValidationDegradationClass.policy_skipped,
            message="policy skipped: live/hybrid validation requires explicit --allow-live opt-in and remains non-merge-blocking by default.",
            elapsed_seconds=0.01,
        ),
        EvaluationResult(
            case_id="fixture_fail",
            status=EvaluationStatus.failed,
            degradation_class=ValidationDegradationClass.product_regression,
            message="fixture mismatch in expected findings",
            elapsed_seconds=0.03,
        ),
    ]
    runner = EvaluationRunner(suite=BenchmarkSuite(suite_id="summary_suite"))
    summary = runner._build_summary(results)
    blob = summary_json_blob(summary, results)

    assert blob["degradation_counts"] == {
        "policy_skipped": 1,
        "product_regression": 1,
    }
    assert blob["failed_case_briefs"][0]["degradation_class"] == "product_regression"

    cli = format_benchmark_cli_summary(
        summary,
        results,
        results_json_path="/tmp/results.json",
        summary_json_path="/tmp/summary.json",
    )
    assert "degradation:" in cli
    assert "policy_skipped=1" in cli
    assert "product_regression=1" in cli

    console = format_console_report(summary, results)
    assert "policy_skipped" in console
    assert "product_regression" in console

    markdown = render_markdown_report(summary, results)
    assert "| case_id | status | degradation | time (s) | note |" in markdown
    assert "policy_skipped" in markdown
    assert "product_regression" in markdown
