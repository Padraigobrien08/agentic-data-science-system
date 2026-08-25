"""
The same seed over the same bytes produces the same run — all of it, not just the answer.

The README calls the loop reproducible and names "deterministic IDs" as the reason. That was
true of the entities the loop mints itself (hypotheses, evidence, experiments, decisions) and
false of everything that arrived from somewhere else: the goal, the dataset reference, the
manifest, every observation, every artifact and every reproducibility manifest defaulted to
``uuid4`` and differed on every run.

Nothing caught it, because the only test of the property compared *conclusions and tool
sequences*. Two runs that agreed on every visible outcome and shared not one entity id were
reported ``identical``, which is precisely the shape of a green suite that is compatible with
the feature being broken.

So this compares the serialized run, whole. It is a blunt assertion on purpose: anything that
becomes non-deterministic shows up here whether or not anyone thought to check it.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from agentic.adapters.base import AdapterRequest
from agentic.adapters.memory import InMemoryDatasetAdapter
from agentic.agent import (
    DiffVerdict,
    InMemoryInvestigationStore,
    InvestigationLoop,
    diff_investigations,
)
from agentic.domain.enums import ColumnRole

GOAL = "Has revenue trended upward over recent periods, or is volatility the explanation?"

#: Timestamps are wall-clock by design and are not part of the reproducibility claim.
_VOLATILE_SUFFIX = "_at"
_VOLATILE_KEYS = {"timestamp"}


def _frame(n: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity": ["A"] * n,
            "period": [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)],
            "revenue": [10.0 + 5.0 * i for i in range(n)],
        }
    )


def _run(seed: str = "determinism"):
    frame = _frame()
    manifest = InMemoryDatasetAdapter(
        frame=frame, time_field="period", entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest())
    return InvestigationLoop().start(
        GOAL, manifest=manifest, frame=frame, seed=seed, store=InMemoryInvestigationStore()
    )


def _without_timestamps(value):
    if isinstance(value, dict):
        return {
            k: _without_timestamps(v)
            for k, v in value.items()
            if not k.endswith(_VOLATILE_SUFFIX) and k not in _VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_without_timestamps(v) for v in value]
    return value


@pytest.fixture(scope="module")
def twice():
    return _run(), _run()


def test_two_runs_of_one_seed_serialize_identically(twice) -> None:
    first, second = twice

    assert json.dumps(_without_timestamps(first.model_dump(mode="json")), sort_keys=True) == (
        json.dumps(_without_timestamps(second.model_dump(mode="json")), sort_keys=True)
    )


@pytest.mark.parametrize(
    "kind",
    ["goal", "dataset", "manifest", "hypothesis", "evidence", "experiment",
     "observation", "artifact", "reproducibility"],
)
def test_no_class_of_id_drifts_between_runs(kind: str, twice) -> None:
    """
    Named per kind so a failure says *what* stopped reproducing. Every one of these except
    hypothesis, evidence and experiment used to fail.
    """
    first, second = twice
    from agentic.agent.diff import _identity

    assert _identity(first)[kind] == _identity(second)[kind]


def test_the_diff_reports_identical_for_a_reproduced_run(twice) -> None:
    first, second = twice
    diff = diff_investigations(first, second)

    assert diff.verdict is DiffVerdict.identical
    assert diff.identity_drift == []


def test_the_diff_notices_identity_drift(twice) -> None:
    """
    The guard on the guard. A verdict of ``identical`` is only meaningful if the comparison
    can tell when ids differ — it could not, which is why this went unnoticed for so long.
    """
    first, second = twice
    tampered = second.model_copy(deep=True)
    tampered.state.objective.id = "goal_something_else"

    diff = diff_investigations(first, tampered)

    assert diff.verdict is DiffVerdict.same_conclusion
    assert "goal" in diff.identity_drift
    assert "ids differ" in diff.summary()


def test_a_different_seed_produces_different_ids() -> None:
    """Ids are seeded per investigation, so two investigations must not collide."""
    from agentic.agent.diff import _identity

    assert _identity(_run("seed-a"))["hypothesis"] != _identity(_run("seed-b"))["hypothesis"]
