"""
Replaying a persisted investigation and diffing the outcome.

The question replay exists to answer: *we changed the model / prompt / budget — did the
analysis actually change, or only the route to it?* These tests cover both halves —
that a replay under identical conditions reproduces the baseline exactly, and that a
replay under changed conditions surfaces the difference with the right verdict.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent import (
    DiffVerdict,
    FixtureAgentPolicy,
    InMemoryInvestigationStore,
    InvestigationLoop,
    LoopBudget,
    ReplayNotPossible,
    diff_investigations,
    replay_investigation,
)
from agentic.agent.replay import REPLAY_ID_SUFFIX, baseline_manifest
from agentic.domain.enums import ColumnRole, ConclusionDisposition, HypothesisStatus

GOAL = "revenue is increasing over time"


def _rising(n: int = 8) -> pd.DataFrame:
    periods = [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)]
    return pd.DataFrame({"entity": ["A"] * n, "period": periods,
                         "revenue": [10.0 + 5.0 * i for i in range(n)]})


def _falling(n: int = 8) -> pd.DataFrame:
    periods = [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)]
    return pd.DataFrame({"entity": ["A"] * n, "period": periods,
                         "revenue": [100.0 - 5.0 * i for i in range(n)]})


def _manifest(df: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=df, time_field="period", entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


def _baseline(df: pd.DataFrame | None = None, *, seed: str = "base", **kwargs):
    frame = df if df is not None else _rising()
    return InvestigationLoop().start(
        GOAL, manifest=_manifest(frame), frame=frame, seed=seed,
        store=InMemoryInvestigationStore(), **kwargs), frame


# -- replaying unchanged reproduces the baseline -----------------------------


def test_replay_under_identical_conditions_is_identical() -> None:
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame)

    assert result.diff.verdict is DiffVerdict.identical
    assert not result.changed
    assert result.diff.baseline_tools == result.diff.candidate_tools
    assert "identical" in result.summary()


def test_replay_is_a_fresh_run_not_a_resume() -> None:
    """Replay must re-decide everything, not continue from the baseline's state."""
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame)

    assert result.candidate.state.budget.iterations_used == baseline.state.budget.iterations_used
    assert len(result.candidate.state.completed_experiments) == len(baseline.state.completed_experiments)
    # A resume would have appended to the baseline's experiments rather than redoing them.
    assert result.candidate is not baseline


def test_candidate_is_relabelled_so_it_cannot_overwrite_the_baseline() -> None:
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame)

    assert result.candidate.id != baseline.id
    assert result.candidate.id.endswith(REPLAY_ID_SUFFIX)
    # Child ids keep the baseline seed, which is what lets the diff align them.
    assert all(h.id.startswith(baseline.id) for h in result.candidate.state.hypotheses)


def test_replay_id_can_be_supplied() -> None:
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame, replay_id="candidate-42")
    assert result.candidate.id == "candidate-42"
    assert result.diff.candidate_id == "candidate-42"


# -- replaying with changed conditions surfaces the change -------------------


def test_a_narrower_budget_changes_the_route() -> None:
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame, budget=LoopBudget(max_experiments=1))

    assert result.changed
    assert len(result.diff.candidate_tools) < len(result.diff.baseline_tools)


def test_different_data_can_change_the_conclusion() -> None:
    """The strongest signal: the answer itself moved."""
    baseline, _ = _baseline(_rising())
    falling = _falling()
    result = replay_investigation(
        baseline, frame=falling, manifest=_manifest(falling), same_dataset=False)

    assert result.diff.verdict is DiffVerdict.diverged
    assert result.diff.conclusion_changed
    assert not result.same_dataset
    assert "different dataset" in result.summary()


def test_replay_notes_flag_a_dataset_substitution() -> None:
    baseline, _ = _baseline()
    falling = _falling()
    result = replay_investigation(
        baseline, frame=falling, manifest=_manifest(falling), same_dataset=False)
    assert any("different dataset" in note for note in result.notes)


def test_replay_without_a_frame_is_flagged() -> None:
    baseline, _ = _baseline()
    result = replay_investigation(baseline, frame=None)
    assert any("without a frame" in note for note in result.notes)


# -- what replay needs from the baseline -------------------------------------


def test_manifest_is_recovered_from_persisted_state() -> None:
    baseline, frame = _baseline()
    recovered = baseline_manifest(baseline)
    assert recovered.name == _manifest(frame).name


def test_replay_refuses_an_investigation_with_no_manifest() -> None:
    baseline, frame = _baseline()
    baseline.state.datasets = []
    with pytest.raises(ReplayNotPossible, match="no persisted dataset manifest"):
        replay_investigation(baseline, frame=frame)


def test_replay_survives_a_round_trip_through_serialization() -> None:
    """A baseline loaded from a store must be replayable — that is the real use case."""
    baseline, frame = _baseline()
    store = InMemoryInvestigationStore()
    store.save(baseline)
    reloaded = store.load(baseline.id)

    result = replay_investigation(reloaded, frame=frame)
    assert result.diff.verdict is DiffVerdict.identical


# -- the diff itself ---------------------------------------------------------


def test_diff_reports_tool_set_differences() -> None:
    baseline, frame = _baseline()
    narrow = InvestigationLoop().start(
        GOAL, manifest=_manifest(frame), frame=frame, seed="base",
        budget=LoopBudget(max_experiments=1), store=InMemoryInvestigationStore())

    diff = diff_investigations(baseline, narrow)
    assert diff.tools_only_in_baseline
    assert diff.experiment_order_changed
    assert diff.baseline_iterations >= diff.candidate_iterations


def test_diff_matches_hypotheses_by_id() -> None:
    baseline, frame = _baseline(_rising())
    falling = _falling()
    other = InvestigationLoop().start(
        GOAL, manifest=_manifest(falling), frame=falling, seed="base",
        store=InMemoryInvestigationStore())

    diff = diff_investigations(baseline, other)
    assert diff.hypothesis_deltas
    ids = {d.hypothesis_id for d in diff.hypothesis_deltas}
    assert all(i.startswith("base-hyp") for i in ids)
    assert diff.changed_hypotheses, "opposing data should land the hypothesis differently"


def test_diff_verdict_separates_a_changed_route_from_a_changed_answer() -> None:
    """
    The distinction the verdict exists for: reaching the same answer by a different path
    is a much weaker signal than reaching a different answer.
    """
    baseline, frame = _baseline()

    same_answer = replay_investigation(baseline, frame=frame).diff
    assert same_answer.verdict is DiffVerdict.identical
    assert not same_answer.conclusion_changed

    falling = _falling()
    changed_answer = replay_investigation(
        baseline, frame=falling, manifest=_manifest(falling), same_dataset=False).diff
    assert changed_answer.verdict is DiffVerdict.diverged
    assert changed_answer.conclusion_changed


def test_diff_is_serializable() -> None:
    """The diff crosses API and storage boundaries, so it must round-trip as JSON."""
    baseline, frame = _baseline()
    diff = replay_investigation(baseline, frame=frame).diff

    payload = diff.model_dump(mode="json")
    assert payload["verdict"] == DiffVerdict.identical.value
    assert payload["baseline_id"] == baseline.id
    from agentic.agent import InvestigationDiff

    assert InvestigationDiff.model_validate(payload) == diff


def test_diff_of_an_investigation_with_itself_is_identical() -> None:
    baseline, _ = _baseline()
    diff = diff_investigations(baseline, baseline)
    assert diff.verdict is DiffVerdict.identical
    assert not diff.conclusion_changed
    assert not diff.termination_changed


def test_conclusion_snapshot_handles_a_missing_conclusion() -> None:
    baseline, _ = _baseline()
    baseline.state.current_conclusion = None
    diff = diff_investigations(baseline, baseline)
    assert diff.baseline_conclusion.disposition is None
    assert diff.verdict is DiffVerdict.identical


def test_a_hypothesis_status_change_alone_counts_as_a_route_change() -> None:
    """Same answer and same experiments, but a claim landed differently."""
    baseline, frame = _baseline()
    twin = InvestigationLoop().start(
        GOAL, manifest=_manifest(frame), frame=frame, seed="base",
        store=InMemoryInvestigationStore())
    assert twin.state.hypotheses, "the fixture must produce a hypothesis to perturb"
    twin.state.hypotheses[0].status = (
        HypothesisStatus.rejected
        if twin.state.hypotheses[0].status is not HypothesisStatus.rejected
        else HypothesisStatus.supported
    )

    diff = diff_investigations(baseline, twin)
    assert diff.verdict is DiffVerdict.same_conclusion
    assert diff.changed_hypotheses
    assert "different route" in diff.summary() or "hypothesis status change" in diff.summary()


def test_summary_names_the_disposition_shift() -> None:
    baseline, _ = _baseline(_rising())
    falling = _falling()
    diff = replay_investigation(
        baseline, frame=falling, manifest=_manifest(falling), same_dataset=False).diff
    if diff.baseline_conclusion.disposition != diff.candidate_conclusion.disposition:
        assert "disposition" in diff.summary()
    else:
        assert "diverged" in diff.summary()


def test_disposition_values_come_from_the_domain_enum() -> None:
    baseline, _ = _baseline()
    diff = diff_investigations(baseline, baseline)
    assert diff.baseline_conclusion.disposition in {d.value for d in ConclusionDisposition}


# -- a changed policy is the headline use case -------------------------------


class _LazyPolicy(FixtureAgentPolicy):
    """A policy that never selects an experiment — stands in for a worse model."""

    def select_experiment(self, *, goal_summary, candidates):
        from agentic.agent.policy import ExperimentChoice

        return ExperimentChoice(request_index=None, rationale="declined")


def test_a_worse_policy_is_detected_as_divergence() -> None:
    """The headline use case: swap the decision-maker, see whether the answer holds."""
    baseline, frame = _baseline()
    result = replay_investigation(baseline, frame=frame, policy=_LazyPolicy())

    assert result.diff.verdict is DiffVerdict.diverged
    assert result.diff.candidate_tools == []
    assert result.diff.baseline_tools, "the baseline must have run experiments to compare against"
    assert result.diff.termination_changed or result.diff.conclusion_changed
