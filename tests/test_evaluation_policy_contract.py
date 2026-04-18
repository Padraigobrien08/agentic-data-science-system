"""Validation policy and degradation schema contract for evaluation suites."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from edgar_project.evaluation.schemas import (
    BenchmarkSuite,
    EvaluationResult,
    InputMode,
    ValidationDegradationClass,
)


def test_fixture_manifest_remains_valid_without_policy_block() -> None:
    suite = BenchmarkSuite.model_validate(
        {
            "suite_id": "fixture_only",
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
    )

    assert suite.cases[0].input.mode == InputMode.fixture
    assert suite.cases[0].input.policy is None


def test_live_manifest_requires_policy_block() -> None:
    with pytest.raises(ValidationError) as exc:
        BenchmarkSuite.model_validate(
            {
                "suite_id": "live_missing_policy",
                "cases": [
                    {
                        "case_id": "live_case",
                        "input": {
                            "mode": "live",
                            "tickers": ["AAPL"],
                            "goal": "Check live validation policy",
                        },
                    }
                ],
            }
        )

    assert "require a policy block" in str(exc.value)


def test_live_manifest_rejects_merge_blocking_policy() -> None:
    with pytest.raises(ValidationError) as exc:
        BenchmarkSuite.model_validate(
            {
                "suite_id": "live_bad_policy",
                "cases": [
                    {
                        "case_id": "live_case",
                        "input": {
                            "mode": "live",
                            "tickers": ["AAPL"],
                            "goal": "Check live validation policy",
                            "policy": {
                                "requires_explicit_live_opt_in": True,
                                "fair_access_policy": "sec_fair_access_operator_invoked",
                                "allow_merge_blocking": True,
                                "normal_user_visible": False,
                                "freshness_window_seconds": 300,
                            },
                        },
                    }
                ],
            }
        )

    assert "non-merge-blocking" in str(exc.value)


def test_evaluation_result_defaults_degradation_class_to_none() -> None:
    result = EvaluationResult(case_id="fixture_case")

    assert result.status.value == "pending"
    assert result.degradation_class == ValidationDegradationClass.none


def test_suite_smoke_live_case_uses_explicit_policy_contract() -> None:
    suite_path = (
        Path(__file__).resolve().parents[1]
        / "edgar_project"
        / "evaluation"
        / "benchmarks"
        / "suite_smoke.json"
    )
    suite = BenchmarkSuite.model_validate_json(suite_path.read_text(encoding="utf-8"))

    live_case = suite.cases[0]
    assert live_case.input.mode == InputMode.live
    assert live_case.input.policy is not None
    assert live_case.input.policy.requires_explicit_live_opt_in is True
    assert live_case.input.policy.fair_access_policy == "sec_fair_access_operator_invoked"
    assert live_case.input.policy.allow_merge_blocking is False
    assert live_case.input.policy.normal_user_visible is False
    assert live_case.input.policy.freshness_window_seconds == 300


def test_policy_skipped_enum_value_is_stable() -> None:
    dumped = json.loads(
        json.dumps(
            {"degradation_class": ValidationDegradationClass.policy_skipped},
            default=str,
        )
    )

    assert dumped["degradation_class"] == ValidationDegradationClass.policy_skipped
