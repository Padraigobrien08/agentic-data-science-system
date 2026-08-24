"""
The loop writing its own answer, and refusing to keep one that invents a figure.

A conclusion built by joining hypothesis statements is true and unreadable, so the
synthesizer may ask its policy for prose. What it may never do is let that prose introduce a
number: the governing rule is that no number in a trace originates from a language model,
and a sentence is the easiest place for one to hide.

These tests are mostly about what is *not* kept. The deterministic ``statement`` is always
present and is the answer of record; the narrative is a bonus that has to earn its place.
"""

from __future__ import annotations

import pytest

from agentic.agent.components import ConclusionSynthesizer
from agentic.agent.ids import DeterministicIds
from agentic.agent.policy import AnswerNarration
from agentic.domain import Hypothesis, InvestigationGoal, InvestigationState
from agentic.domain.enums import HypothesisStatus, ProvenanceSource, TerminationReason
from agentic.domain.provenance import Provenance

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")


def _state() -> InvestigationState:
    state = InvestigationState(objective=InvestigationGoal(objective="does staffing drive service?"))
    for i, statement in enumerate(["staffing drives it", "volume drives it"]):
        h = Hypothesis(id=f"hyp-{i}", statement=statement, provenance=_PROV)
        h.confidence = 0.95
        h.set_status(HypothesisStatus.active)
        h.set_status(HypothesisStatus.supported)
        state.add_hypothesis(h)
    return state


class _Writes:
    """A policy that writes whatever it is told to."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.seen: dict | None = None

    def write_answer(self, *, question: str, findings: dict) -> AnswerNarration:
        self.seen = {"question": question, "findings": findings}
        return AnswerNarration(answer=self.answer)


class _Silent:
    """A policy with no narration at all — the four-method contract is still valid."""


def _synthesize(policy: object | None, question: str = "does staffing drive service?"):
    return ConclusionSynthesizer().synthesize(
        _state(),
        TerminationReason.sufficient_evidence,
        DeterministicIds("inv"),
        policy=policy,
        question=question,
    )


def test_prose_whose_figures_all_check_out_is_kept() -> None:
    concl = _synthesize(_Writes("Both claims held, at 95% confidence."))

    assert concl.narrative == "Both claims held, at 95% confidence."


def test_prose_that_invents_a_figure_is_discarded_whole() -> None:
    # 0.87 appears nowhere in the run. The rest of the sentence is true, and it still goes.
    concl = _synthesize(_Writes("Both claims held, at 87% confidence."))

    assert concl.narrative is None


def test_the_deterministic_statement_survives_a_discarded_narrative() -> None:
    concl = _synthesize(_Writes("It held across 4,000 quarters."))

    assert concl.narrative is None
    assert "staffing drives it" in concl.statement


def test_a_policy_that_cannot_write_is_not_a_failure() -> None:
    concl = _synthesize(_Silent())

    assert concl.narrative is None
    assert concl.statement


def test_no_policy_at_all_still_concludes() -> None:
    concl = _synthesize(None)

    assert concl.narrative is None
    assert concl.statement


def test_a_policy_that_raises_does_not_take_the_run_with_it() -> None:
    class _Explodes:
        def write_answer(self, *, question: str, findings: dict) -> AnswerNarration:
            raise RuntimeError("provider down")

    concl = _synthesize(_Explodes())

    assert concl.narrative is None
    assert concl.statement


def test_an_empty_answer_is_treated_as_no_answer() -> None:
    assert _synthesize(_Writes("   ")).narrative is None


def test_a_figure_from_the_widened_findings_verifies() -> None:
    # The evidence split per claim is handed over so a longer answer has something true to
    # say; it must therefore also be admitted by the check, or the writer is trapped.
    policy = _Writes("Both claims held at 95%, with 0 evidence items against either.")

    assert _synthesize(policy).narrative is not None


def test_the_policy_is_given_the_question_and_computed_findings() -> None:
    policy = _Writes("It held.")
    _synthesize(policy, question="why did service slip?")

    assert policy.seen is not None
    assert policy.seen["question"] == "why did service slip?"
    findings = policy.seen["findings"]
    assert findings["counts"]["hypotheses"] == 2
    assert findings["counts"]["supported"] == 2
    # Values, already computed — the policy is never asked to do arithmetic.
    assert [c["confidence"] for c in findings["claims"]] == [0.95, 0.95]
    # Material for a longer answer: how each claim was carried, what ran, where it stopped.
    assert findings["claims"][0]["supporting_evidence"] == 0
    assert findings["stopped_because"] == "sufficient_evidence"
    assert findings["experiments_run"] == []
    assert findings["open_questions"] == []


def test_writing_the_answer_is_counted_against_the_budget() -> None:
    """
    A model call the budget cannot see makes a run look cheaper than it was. Recorded, never
    gated: the run has already terminated by this point, so refusing the call would cost the
    answer without saving the spend.
    """
    from agentic.agent.budget import BudgetTracker, LoopBudget, SafetyLimits

    class _Priced:
        def write_answer(self, *, question: str, findings: dict) -> AnswerNarration:
            return AnswerNarration(answer="It held.")

        def drain_cost_usd(self) -> float:
            return 0.004

    tracker = BudgetTracker(LoopBudget(), SafetyLimits())
    before = tracker.model_calls_used

    ConclusionSynthesizer().synthesize(
        _state(), TerminationReason.sufficient_evidence, DeterministicIds("inv"),
        policy=_Priced(), question="q", tracker=tracker,
    )

    assert tracker.model_calls_used == before + 1
    assert tracker.cost_used_usd == pytest.approx(0.004)


def test_the_conclusion_still_forms_without_a_tracker() -> None:
    # Callers outside the loop (tests, replay) have no budget to charge.
    concl = ConclusionSynthesizer().synthesize(
        _state(), TerminationReason.sufficient_evidence, DeterministicIds("inv"),
        policy=_Writes("It held."), question="q",
    )

    assert concl.narrative == "It held."
