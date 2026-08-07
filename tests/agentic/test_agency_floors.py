"""
The regression gate on the deterministic agency baseline.

This is the cheap half of the measurement strategy. Model policies are non-deterministic and
cost money, so they are benchmarked on demand by ``backend.dev.agency_bench``. The fixture
policy is deterministic and free, so it can run on every pull request — which makes it the
right place to catch a change that quietly degrades how the loop reasons.

The failure this exists to prevent is a prompt or component edit that trades one property for
another: overall pass rate barely moves while ``calibrated_confidence`` collapses, because the
loop started hedging. A single aggregate number hides that. Per-property floors do not.

Floors sit exactly at the observed baseline rather than a margin below it. The fixture policy
is deterministic — the first test here proves that — so there is no sampling noise to absorb,
and any drop is a real behaviour change worth stopping on.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentic.evaluation.agency import AgencyProperty
from agentic.evaluation.runner import run_agency_suite

_FLOORS_PATH = (
    Path(__file__).resolve().parents[2]
    / "agentic"
    / "evaluation"
    / "baselines"
    / "fixture_floors.json"
)


def _floors() -> dict:
    return json.loads(_FLOORS_PATH.read_text(encoding="utf-8"))


def test_the_baseline_is_actually_deterministic() -> None:
    """
    The premise of zero-margin floors. If this fails, the floors are wrong before anything
    else is — they would be pinning one sample of a distribution.
    """
    runs = [run_agency_suite() for _ in range(3)]
    scores = [r.property_scores() for r in runs]

    assert all(s == scores[0] for s in scores), (
        f"fixture baseline varied across runs: {scores}. The floors assume determinism; "
        "either restore it or move the floors below the observed spread."
    )


def test_every_property_holds_its_floor() -> None:
    floors = _floors()["properties"]
    observed = run_agency_suite().property_scores()

    below = [
        f"{name}: floor {floor:.4f}, observed {observed.get(name, 0.0):.4f}"
        for name, floor in sorted(floors.items())
        if observed.get(name, 0.0) < floor
    ]

    assert not below, (
        "agency properties regressed below their committed floors "
        f"({_FLOORS_PATH.name}):\n  " + "\n  ".join(below)
    )


def test_overall_pass_rate_holds_its_floor() -> None:
    floor = _floors()["pass_rate"]
    report = run_agency_suite()

    assert report.pass_rate >= floor, (
        f"suite pass rate {report.pass_rate:.4f} is below the committed floor {floor:.4f}; "
        f"failing cases: {[r.case_id for r in report.results if not r.passed]}"
    )


def test_the_floors_file_covers_every_agency_property() -> None:
    """
    A new `AgencyProperty` must arrive with a floor. Without this, adding a property would
    silently leave it ungated — the gap would look exactly like everything passing.
    """
    floors = set(_floors()["properties"])
    declared = {p.value for p in AgencyProperty}

    assert floors == declared, (
        f"floors file and AgencyProperty disagree — missing floors: {sorted(declared - floors)}; "
        f"floors for unknown properties: {sorted(floors - declared)}"
    )


def test_every_floored_property_is_actually_exercised_by_a_case() -> None:
    """
    Guards the other direction: a floor on a property no case asserts is unenforceable, and
    would read as a passing gate while measuring nothing.
    """
    floors = set(_floors()["properties"])
    exercised = set(run_agency_suite().property_scores())

    assert floors <= exercised, (
        f"floors are declared for properties no case asserts: {sorted(floors - exercised)}. "
        "Add a case that exercises them, or remove the floor."
    )
