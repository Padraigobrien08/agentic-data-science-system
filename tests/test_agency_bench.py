"""
The model-backed agency bench harness.

Every test here runs offline against the deterministic fixture policy or an injected stub —
the harness must be exercisable without a provider, or it could only be tested by spending
money. The behaviours worth pinning are the ones that would corrupt a published scoreboard:
silently reporting a fixture result under a model's name, and overrunning the cost ceiling.
"""

from __future__ import annotations

import json

import pytest

from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.agent.policy import (
    CritiqueProposal,
    ExperimentChoice,
    GoalInterpretation,
    HypothesisProposals,
)
from agentic.evaluation.cases import AGENCY_CASES
from agentic.evaluation.runner import run_agency_suite, run_case
from backend.config.settings import Settings
from backend.dev.agency_bench import main, run_policy_rows


def _settings() -> Settings:
    return Settings(agent_completion_model="test-model")


def _fixture_factory(kind: str, settings: Settings):  # noqa: ANN001,ARG001 - test double
    return FixtureAgentPolicy()


class _CostlyPolicy:
    """Fixture behaviour plus a fixed per-decision cost, to drive the ceiling."""

    def __init__(self, cost_per_call: float = 1.0) -> None:
        self._inner = FixtureAgentPolicy()
        self._cost_per_call = cost_per_call
        self._pending = 0.0

    def interpret_goal(self, goal_text: str, *, capability_summary: dict) -> GoalInterpretation:
        self._pending += self._cost_per_call
        return self._inner.interpret_goal(goal_text, capability_summary=capability_summary)

    def generate_hypotheses(self, interpretation, *, metric_names, dimension_names) -> HypothesisProposals:  # noqa: ANN001
        self._pending += self._cost_per_call
        return self._inner.generate_hypotheses(
            interpretation, metric_names=metric_names, dimension_names=dimension_names
        )

    def select_experiment(self, *, goal_summary: dict, candidates: list[dict]) -> ExperimentChoice:
        self._pending += self._cost_per_call
        return self._inner.select_experiment(goal_summary=goal_summary, candidates=candidates)

    def critique(self, *, strongest_claim, available_tools) -> CritiqueProposal:  # noqa: ANN001
        self._pending += self._cost_per_call
        return self._inner.critique(
            strongest_claim=strongest_claim, available_tools=available_tools
        )

    def drain_cost_usd(self) -> float:
        pending, self._pending = self._pending, 0.0
        return pending


# -- rows --------------------------------------------------------------------


def test_fixture_row_runs_offline_and_reports_its_trials() -> None:
    rows = run_policy_rows(
        ["fixture"], trials=2, settings=_settings(), policy_factory=_fixture_factory
    )

    assert len(rows) == 1
    assert rows[0].label == "fixture"
    assert rows[0].trials == 2
    assert not rows[0].truncated


def test_the_deterministic_baseline_is_stable_across_trials() -> None:
    """If the fixture policy ever flaps, the suite's determinism claim is broken."""
    rows = run_policy_rows(
        ["fixture"], trials=3, settings=_settings(), policy_factory=_fixture_factory
    )

    assert rows[0].unstable_cases == []
    assert rows[0].fully_stable


def test_a_model_row_without_a_provider_is_refused_not_faked(monkeypatch) -> None:
    """
    `build_agent_policy` degrades to the fixture policy when no provider is configured.
    Publishing that as a model result would silently invalidate the scoreboard's whole claim,
    so the harness must refuse the row instead.
    """
    with pytest.raises(SystemExit, match="no LLM provider is configured"):
        run_policy_rows(
            ["model"],
            model="some-model",
            trials=1,
            settings=_settings(),
            policy_factory=_fixture_factory,
        )


def test_an_unpriced_model_row_is_refused_before_spending() -> None:
    """
    Unpriced models cost 0.0 by design, which would make the scoreboard's cost column
    meaningless and leave --max-cost-usd unable to ever fire. Fail before the first call.
    """
    with pytest.raises(SystemExit, match="no price configured"):
        run_policy_rows(
            ["model"],
            model="unpriced-model",
            trials=1,
            settings=_settings(),
            policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=0.0),
        )


def test_allow_unpriced_opts_into_a_quality_only_run() -> None:
    rows = run_policy_rows(
        ["model"],
        model="unpriced-model",
        trials=1,
        allow_unpriced=True,
        settings=_settings(),
        policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=0.0),
    )

    assert rows[0].trials == 1
    assert rows[0].total_cost_usd == 0.0


def test_a_priced_model_row_proceeds() -> None:
    priced = Settings(
        agent_completion_model="test-model",
        llm_model_prices={"priced-model": {"input_per_1m": 0.15, "output_per_1m": 0.60}},
    )

    rows = run_policy_rows(
        ["model"],
        model="priced-model",
        trials=1,
        settings=priced,
        policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=1.0),
    )

    assert rows[0].label == "priced-model"
    assert rows[0].total_cost_usd > 0


def test_a_resolved_snapshot_mismatch_is_caught_after_one_trial() -> None:
    """
    The static price check keys off the configured id, but the API bills a dated snapshot and
    the lookup is exact. Observed spend of $0.00 across real model calls is the only signal
    that the price key missed, so the run must stop after one trial rather than complete.
    """
    priced = Settings(
        agent_completion_model="test-model",
        llm_model_prices={"priced-model": {"input_per_1m": 0.15, "output_per_1m": 0.60}},
    )

    with pytest.raises(SystemExit, match="does not match the id the API billed against"):
        run_policy_rows(
            ["model"],
            model="priced-model",
            trials=5,
            settings=priced,
            # Configured id is priced, but this policy accrues nothing — the shape of a
            # snapshot-id mismatch.
            policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=0.0),
        )


def test_multiple_rows_are_measured_in_order() -> None:
    rows = run_policy_rows(
        ["fixture", "fixture"], trials=1, settings=_settings(), policy_factory=_fixture_factory
    )

    assert [r.label for r in rows] == ["fixture", "fixture"]


# -- cost ceiling ------------------------------------------------------------


def test_the_cost_ceiling_truncates_remaining_trials() -> None:
    rows = run_policy_rows(
        ["fixture"],
        trials=5,
        max_cost_usd=0.5,
        settings=_settings(),
        policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=1.0),
    )

    assert rows[0].truncated
    assert rows[0].trials < 5
    assert rows[0].total_cost_usd > 0


def test_no_ceiling_runs_every_requested_trial() -> None:
    rows = run_policy_rows(
        ["fixture"],
        trials=3,
        settings=_settings(),
        policy_factory=lambda kind, s: _CostlyPolicy(cost_per_call=1.0),
    )

    assert rows[0].trials == 3
    assert not rows[0].truncated


# -- budget passthrough ------------------------------------------------------


def test_a_supplied_budget_does_not_disarm_a_cases_own_experiment_cap() -> None:
    """
    A case's `max_experiments` is part of what it asserts, so it must win over a
    caller-supplied budget. Passing a wide budget used to replace the case's cap wholesale,
    which would let the budget cases pass vacuously whenever the bench set a cost ceiling.

    The shipped `budget_is_respected` case cannot detect this — `clear_rising` converges at
    two experiments unaided, so capped and uncapped runs look identical. A cap of 1 is below
    the natural stopping point and therefore observable.
    """
    from agentic.agent.budget import LoopBudget

    base = next(c for c in AGENCY_CASES if c.case_id == "budget_is_respected")
    tight = base.model_copy(update={"case_id": "probe", "max_experiments": 1})

    result = run_case(tight, budget=LoopBudget(max_cost_usd=5.0, max_experiments=99))

    assert len(result.observed_tools) == 1, (
        "the case's own cap of 1 was overridden by the supplied budget's 99"
    )


def test_a_supplied_budgets_other_fields_survive_the_merge() -> None:
    """The case pins only `max_experiments`; the caller's cost bound must still apply."""
    from agentic.agent.budget import LoopBudget

    base = next(c for c in AGENCY_CASES if c.case_id == "budget_is_respected")
    merged = LoopBudget(max_cost_usd=5.0, max_experiments=99).model_copy(
        update={"max_experiments": base.max_experiments}
    )

    assert merged.max_experiments == base.max_experiments
    assert merged.max_cost_usd == 5.0


def test_suite_level_budget_reaches_every_case() -> None:
    from agentic.agent.budget import LoopBudget

    report = run_agency_suite(budget=LoopBudget(max_experiments=2))

    assert report.total == len(AGENCY_CASES)


# -- CLI ---------------------------------------------------------------------


def test_cli_writes_both_artifacts(tmp_path, capsys) -> None:
    out = tmp_path / "scoreboard"

    code = main(["--policy", "fixture", "--trials", "2", "--out", str(out), "--format", "both"])

    assert code == 0
    assert out.with_suffix(".md").is_file()
    payload = json.loads(out.with_suffix(".json").read_text())
    assert payload["suite_id"] == "suite_agency_v1"
    assert payload["requested_trials"] == 2
    assert payload["rows"][0]["label"] == "fixture"
    assert payload["prompt_version"]


def test_cli_defaults_to_the_fixture_row(capsys) -> None:
    assert main(["--trials", "1"]) == 0
    assert "fixture" in capsys.readouterr().out


def test_cli_rejects_a_zero_trial_run() -> None:
    with pytest.raises(SystemExit, match="--trials must be at least 1"):
        main(["--policy", "fixture", "--trials", "0"])
