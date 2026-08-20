"""
Decisions carry the iteration they were made in.

`AgentDecision.iteration` defaults to 0 and six of the seven components never passed it, so a
recorded run rendered as fifteen decisions all stamped `iter 0` — a list that could not be
read as a sequence, which is most of what a trace is for. Only `select_experiment` was
correct, which is why the bug survived: the one row that counted up made the rest look
intentional.

Stamped in `record_decision` now, so a component cannot forget. These tests are about that
guarantee rather than about any one component.
"""

from __future__ import annotations

from agentic.domain import InvestigationGoal, InvestigationState
from agentic.domain.decisions import AgentDecision
from agentic.domain.enums import DecisionType, ProvenanceSource
from agentic.domain.provenance import Provenance

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")


def _state() -> InvestigationState:
    return InvestigationState(objective=InvestigationGoal(objective="why did it move?"))


def _decision(rationale: str = "because") -> AgentDecision:
    return AgentDecision(
        decision_type=DecisionType.revise_confidence, rationale=rationale, provenance=_PROV
    )


def test_a_decision_is_stamped_with_the_current_iteration() -> None:
    state = _state()
    state.advance_iteration()
    state.advance_iteration()

    recorded = state.record_decision(_decision())

    assert recorded.iteration == 2


def test_the_first_iteration_is_zero() -> None:
    """The loop reads `iterations_used` before advancing, so iteration 0 is a real value."""
    state = _state()

    assert state.record_decision(_decision()).iteration == 0


def test_decisions_across_iterations_form_a_readable_sequence() -> None:
    """The property the trace actually needs: stamps that move with the loop."""
    state = _state()
    for _ in range(3):
        state.record_decision(_decision("planned"))
        state.record_decision(_decision("revised"))
        state.advance_iteration()

    assert [d.iteration for d in state.decisions] == [0, 0, 1, 1, 2, 2]


def test_a_component_cannot_forget_to_pass_it() -> None:
    """
    The regression this fix exists for.

    A decision constructed without `iteration` used to keep the field default of 0 forever;
    it now picks up the loop's counter regardless of what the caller did or did not pass.
    """
    state = _state()
    state.advance_iteration()

    naive = AgentDecision(
        decision_type=DecisionType.revise_confidence, rationale="no iteration passed",
        provenance=_PROV,
    )
    assert naive.iteration == 0  # the default that caused the bug

    assert state.record_decision(naive).iteration == 1


def test_a_stale_iteration_from_the_caller_is_corrected() -> None:
    """A decision describes something happening now, so the loop's counter wins."""
    state = _state()
    state.advance_iteration()
    state.advance_iteration()

    stale = AgentDecision(
        decision_type=DecisionType.revise_confidence, rationale="claims iteration 0",
        iteration=0, provenance=_PROV,
    )

    assert state.record_decision(stale).iteration == 2
