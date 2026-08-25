"""
Every intent must be able to test a rival explanation, not just the first claim.

Intent hard-gates which experiments become candidates. When an intent's list runs dry with a
hypothesis still at ``proposed``, the loop stops and reports ``insufficient_evidence`` — and
it is right to: ruling out an alternative nothing was ever run against is exactly the
overreach this system exists not to commit. But the reader sees a run that gave up, and the
cause is a gap in this mapping rather than anything about the data.

That is not hypothetical. A recorded run asking whether a rising mean was a broad shift or a
small tail of very late orders exhausted ``distribution``'s two tools with the tail claim
untested, because the tool that answers it — ``detect_outliers`` — was only offered under
``anomaly``.
"""

from __future__ import annotations

import pytest

from agentic.agent.components import EDGAR_INTENT_TOOLS, INTENT_TOOLS
from agentic.agent.policy import AnalysisIntent
from agentic.experiments import build_default_registry


def test_every_intent_offers_at_least_two_tools() -> None:
    """
    A goal phrased as two competing explanations needs two things to run. One tool means the
    rival can only ever be inferred, never tested.
    """
    thin = {
        intent.value: tools
        for intent, tools in INTENT_TOOLS.items()
        if len(tools) + len(EDGAR_INTENT_TOOLS.get(intent, [])) < 2
    }
    assert not thin, f"intents that cannot test a rival explanation: {thin}"


def test_a_tail_question_can_reach_the_tool_that_answers_it() -> None:
    # The specific gap a real run fell into.
    assert "detect_outliers" in INTENT_TOOLS[AnalysisIntent.distribution]


@pytest.mark.parametrize("intent", list(AnalysisIntent))
def test_every_offered_tool_actually_exists(intent: AnalysisIntent) -> None:
    """
    A name in this table that the registry does not define is a candidate the planner will
    never build — indistinguishable, from the outside, from an intent with too few tools.
    """
    registered = set(build_default_registry().names())
    offered = set(INTENT_TOOLS.get(intent, [])) | set(EDGAR_INTENT_TOOLS.get(intent, []))
    assert offered <= registered, f"{intent.value} offers unknown tools: {offered - registered}"
