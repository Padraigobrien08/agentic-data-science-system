"""Tests asserting the worked example investigations are valid and coherent."""

from __future__ import annotations

from agentic.domain import (
    ConclusionDisposition,
    HypothesisStatus,
    InvestigationStatus,
    TerminationReason,
)
from agentic.domain.examples import (
    example_edgar_manifest,
    example_inconclusive_investigation,
    example_investigation,
)


def test_example_manifest_is_edgar_shaped() -> None:
    m = example_edgar_manifest()
    assert m.entity_id_column().name == "ticker"
    assert m.time_index_column().name == "period"
    assert "net_margin" in m.metric_names()


def test_converged_example_is_internally_consistent() -> None:
    inv = example_investigation()
    assert inv.status is InvestigationStatus.converged
    state = inv.state

    # dataset lineage is wired
    dset = state.datasets[0]
    assert dset.manifest is not None
    assert dset.manifest.dataset_reference_id == dset.id

    # the supported hypothesis has linked supporting evidence that exists
    hyp = state.hypotheses[0]
    assert hyp.status is HypothesisStatus.supported
    assert hyp.supporting_evidence_ids
    evidence_ids = {e.id for e in state.evidence}
    assert set(hyp.supporting_evidence_ids).issubset(evidence_ids)

    # evidence references an experiment result that exists
    ev = state.evidence[0]
    result_ids = {r.id for r in state.completed_experiments}
    assert ev.experiment_result_id in result_ids

    # conclusion cites the hypothesis and evidence
    concl = state.current_conclusion
    assert concl.disposition is ConclusionDisposition.supported
    assert hyp.id in concl.supporting_hypothesis_ids
    assert ev.id in concl.key_evidence_ids

    # termination is an explicit, provenance-backed decision
    assert state.termination.should_stop
    assert state.termination.reason is TerminationReason.sufficient_evidence
    assert state.termination.provenance is not None

    # every decision/critique carries provenance
    assert state.decisions and all(d.provenance is not None for d in state.decisions)
    assert all(c.provenance is not None for c in state.critiques)


def test_inconclusive_example_stops_on_insufficient_evidence() -> None:
    inv = example_inconclusive_investigation()
    assert inv.status is InvestigationStatus.exhausted
    state = inv.state
    assert state.termination.reason is TerminationReason.insufficient_evidence
    # a valid honest outcome: hypothesis left unresolved, question left open
    assert state.hypotheses[0].status is HypothesisStatus.unresolved
    assert state.unresolved_questions()
