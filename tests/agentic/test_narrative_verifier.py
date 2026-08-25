"""
The narrative check, attacked directly.

``test_conclusion_narrative.py`` covers the synthesizer's contract — that a bad narrative is
dropped whole and the deterministic statement survives. This file is about the check itself,
and it exists because the first version passed everything below.

That version held one flat set of every number the run recorded and asked only whether a token
appeared in it. A run with seven experiments and three open questions therefore licensed
``"Revenue grew 7% while margin fell 3%."`` — two invented financial figures, each borrowing
the authority of an unrelated count. The set was untyped, unpositioned and sign-blind, and the
governing invariant ("no number in a trace originates from a language model") did not survive
contact with it.

Two things are asserted here, and the second matters as much as the first:

* fabricated figures are refused, and
* the seven narratives this loop has *actually produced* are still accepted.

Without the second, the natural fix to the first is to tighten until nothing passes, which is
how an earlier iteration discarded five of eight real narratives and made the feature
unusable. A check that rejects everything is not a safe check, it is a broken feature with
good optics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic.agent.narrative import AllowedFigures, verify_narrative

_DEMOS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "demo-static"

#: The flagship EDGAR run's real recorded figures: 2 hypotheses, 7 evidence, 7 experiments,
#: 1 supported, 3 open questions; confidences 0.05 (rejected), 0.95 (supported), 0.5 overall.
_METRICS = ["net_margin", "revenue", "revenue_growth_qoq", "period", "entity"]


@pytest.fixture
def allowed() -> AllowedFigures:
    figures = (
        AllowedFigures()
        .add_counts(
            {"hypotheses": 2, "evidence": 7, "experiments": 7, "supported": 1, "open_questions": 3}
        )
        .add_confidence(0.5)
        .add_confidence(0.05)
        .add_confidence(0.95)
    )
    for value in (0, 1, 2, 3, 4, 5):
        figures.add("supporting_evidence", value).add("refuting_evidence", value)
    return figures.add_metric_terms(_METRICS)


# -- what must be refused ----------------------------------------------------


@pytest.mark.parametrize(
    "prose",
    [
        # The motivating case: 7 and 3 are real counts, spent as percentages of a metric.
        "Revenue grew 7% while margin fell 3%.",
        # 5 is a real confidence read as a percentage (0.05). Attached to a metric it is not.
        "Net margin deteriorated by 5% over the period.",
        # 0.95 is a real confidence. As a metric value it is invented.
        "Net margin was 0.95 in the final period.",
        # Sign-blindness: the magnitude is recorded, the direction is not.
        "Margin fell by -5 percentage points.",
        # Nothing in the run records a figure of this size at all.
        "It held across 4,000 quarters.",
        "Margin dropped from 45.2% to 38.1%.",
        # Unlabelled: the value is recorded, but nothing says what it is a count of.
        "There were 7 of them.",
    ],
)
def test_fabricated_figures_are_refused(prose: str, allowed: AllowedFigures) -> None:
    assert verify_narrative(prose, allowed) is None


@pytest.mark.parametrize(
    "prose",
    [
        "Revenue growth was more than twice as fast as the margin decline.",
        "Margin roughly doubled over the window.",
        "The effect was an order of magnitude larger than noise.",
        "Revenue growth outpaced margin erosion by a factor of three.",
        "It tripled.",
        "Net margin fell by half of the prior level.",
    ],
)
def test_ratios_stated_without_a_numeral_are_refused(prose: str, allowed: AllowedFigures) -> None:
    """A multiplicative relation is a figure the run never computed, spelled in words."""
    assert verify_narrative(prose, allowed) is None


# -- what must survive -------------------------------------------------------


@pytest.mark.parametrize(
    "prose",
    [
        "The run tested 2 hypotheses and ended with 1 supported claim.",
        "It ran 7 experiments and recorded 7 evidence items.",
        "Three open questions remain.",
        "Both claims were supported, each with high confidence and no refuting evidence.",
        # A claim statement names its metric; an explicit confidence word says which quantity
        # the figure is, so the metric veto must not fire here.
        "The revenue-growth claim was supported at 95% confidence.",
        # Ordinal and qualitative comparisons describe orderings the run genuinely holds.
        "The margin claim was rejected, with more refuting evidence than supporting evidence.",
        "Overall the evidence points toward revenue growth as the stronger explanation.",
    ],
)
def test_honest_prose_is_kept(prose: str, allowed: AllowedFigures) -> None:
    assert verify_narrative(prose, allowed) == prose


# -- the regression corpus ---------------------------------------------------


def _published_runs():
    for path in sorted(_DEMOS.glob("*.json")):
        if path.name in {"index.json", "artifacts.json"} or ".capture." in path.name:
            continue
        yield path.stem, json.loads(path.read_text())


def _allowed_for(detail: dict) -> AllowedFigures:
    """Rebuild the allowed set the synthesizer would have built for this run."""
    hypotheses = detail["hypotheses"]
    figures = AllowedFigures().add_counts(
        {
            "hypotheses": len(hypotheses),
            "evidence": len(detail["evidence"]),
            "experiments": len(detail["experiments"]),
            "supported": sum(1 for h in hypotheses if h["status"] == "supported"),
            "open_questions": len(detail["open_questions"]),
        }
    )
    figures.add_confidence((detail["conclusion_detail"] or {}).get("confidence"))
    for hypothesis in hypotheses:
        figures.add_confidence(hypothesis["confidence"])

    supporting = {h["id"]: 0 for h in hypotheses}
    refuting = {h["id"]: 0 for h in hypotheses}
    for item in detail["evidence"]:
        bucket = refuting if item["direction"] == "refutes" else supporting
        for hid in item.get("hypothesis_ids") or []:
            if hid in bucket:
                bucket[hid] += 1
    for role, per_claim in (("supporting_evidence", supporting), ("refuting_evidence", refuting)):
        for value in per_claim.values():
            figures.add(role, value)
    return figures


@pytest.mark.parametrize("slug,detail", list(_published_runs()))
def test_every_narrative_this_loop_has_written_still_verifies(slug: str, detail: dict) -> None:
    """
    The over-rejection guard. Each of these is real output that was checked, kept and
    published; a change that starts discarding them has broken the feature even if every
    adversarial test above still passes.
    """
    narrative = (detail["conclusion_detail"] or {}).get("narrative")
    if not narrative:
        pytest.skip(f"{slug} has no narrative")

    assert verify_narrative(narrative, _allowed_for(detail)) == narrative.strip()
