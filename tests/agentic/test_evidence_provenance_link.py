"""
Evidence must name the computation that produced it, from both ends.

This is the load-bearing edge of the whole traceability claim: a conclusion cites evidence,
and evidence is only auditable if it can say *which experiment computed this number*. The
link existed in the schema, in the persistence layer and in the read model, and was never
written — ``EvidenceUpdater`` hardcoded ``experiment_result_id=None``, while
``ExperimentResult.produced_evidence_ids`` carried the ids the *tool* minted before the loop
re-minted its own. Two id spaces, disjoint, so every traversal from either side landed on
nothing. Six published demos shipped with 123 of 123 evidence rows unlinked, and the frontend
grew a comment explaining that grouping by experiment was "currently unanswerable".

Nothing failed. That is the point of these tests: a green suite was fully compatible with the
product's central guarantee being false, because every existing assertion checked one side of
the link against itself. These check the two sides against *each other*, over a real run.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters.base import AdapterRequest
from agentic.adapters.memory import InMemoryDatasetAdapter
from agentic.agent import InMemoryInvestigationStore, InvestigationLoop
from agentic.domain.enums import ColumnRole

GOAL = "Has revenue trended upward over recent periods, or is volatility the explanation?"


def _frame(n: int = 8) -> pd.DataFrame:
    periods = [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)]
    return pd.DataFrame(
        {
            "entity": ["A"] * n,
            "period": periods,
            "revenue": [10.0 + 5.0 * i for i in range(n)],
        }
    )


def _manifest(df: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=df,
        time_field="period",
        entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


@pytest.fixture(scope="module")
def state():
    frame = _frame()
    investigation = InvestigationLoop().start(
        GOAL,
        manifest=_manifest(frame),
        frame=frame,
        seed="link",
        store=InMemoryInvestigationStore(),
    )
    return investigation.state


def test_the_run_actually_produced_evidence(state) -> None:
    """Guards the rest of this module: assertions over an empty list all pass vacuously."""
    assert state.evidence, "no evidence produced — the link tests below would be vacuous"
    assert state.completed_experiments


def test_every_evidence_item_names_the_experiment_that_produced_it(state) -> None:
    unlinked = [e.id for e in state.evidence if not e.experiment_result_id]

    assert not unlinked, (
        "evidence with no experiment_result_id cannot be traced back to the computation "
        f"behind its number: {unlinked}"
    )


def test_every_evidence_link_resolves_to_a_real_result(state) -> None:
    """A link is only worth writing if following it lands somewhere."""
    known = {r.id for r in state.completed_experiments} | {r.id for r in state.failed_experiments}
    dangling = sorted(
        {e.experiment_result_id for e in state.evidence if e.experiment_result_id} - known
    )

    assert not dangling, f"evidence points at experiment results that do not exist: {dangling}"


def test_every_produced_evidence_id_resolves_to_a_real_evidence_item(state) -> None:
    """
    The reverse traversal. This is the one that was silently broken: the tool's own evidence
    ids were carried into the domain result while state held re-minted ones, so the list was
    100% dangling and no test noticed.
    """
    known = {e.id for e in state.evidence}
    produced = {eid for r in state.completed_experiments for eid in r.produced_evidence_ids}
    dangling = sorted(produced - known)

    assert not dangling, f"results claim evidence that does not exist in state: {dangling}"


def test_the_two_directions_agree(state) -> None:
    """Following the link forwards and backwards must describe the same pairing."""
    forward = {(e.experiment_result_id, e.id) for e in state.evidence if e.experiment_result_id}
    backward = {
        (r.id, eid) for r in state.completed_experiments for eid in r.produced_evidence_ids
    }

    assert forward == backward, (
        "the evidence→result and result→evidence links disagree; "
        f"only forwards: {sorted(forward - backward)}; only backwards: {sorted(backward - forward)}"
    )


def test_a_failed_experiment_claims_no_evidence(state) -> None:
    """An experiment that did not run produced nothing, and must not say otherwise."""
    for result in state.failed_experiments:
        assert not result.produced_evidence_ids
