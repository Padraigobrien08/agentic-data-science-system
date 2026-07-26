"""
Worked examples of valid investigation states.

These construct fully-populated, serializable domain objects. They are used by
the domain tests and documentation, and double as reference fixtures for future
wiring. They perform no I/O and no network access.
"""

from __future__ import annotations

from .conclusion import Conclusion
from .decisions import AgentDecision, Critique, EntityRef
from .enums import (
    ColumnRole,
    ConclusionDisposition,
    CritiqueSeverity,
    CritiqueType,
    DatasetKind,
    DataSourceKind,
    DecisionType,
    EntityKind,
    EvidenceDirection,
    EvidenceType,
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    ObservationType,
    PayloadKind,
    ProvenanceSource,
    ReferenceKind,
    TerminationReason,
)
from .evidence import Evidence, PayloadReference, SourceReference
from .experiment import CostEstimate, ExperimentRequest, ExperimentResult, Precondition
from .hypothesis import Hypothesis
from .investigation import (
    BudgetState,
    Investigation,
    InvestigationGoal,
    TerminationDecision,
)
from .manifest import (
    ColumnSpec,
    DatasetManifest,
    DatasetProvenance,
    DatasetReference,
    DataSource,
)
from .observation import Observation
from .provenance import Provenance
from .questions import OpenQuestion


def _agent_prov(agent_id: str) -> Provenance:
    return Provenance(source=ProvenanceSource.agent_llm, agent_id=agent_id, prompt_id="demo", prompt_version="1")


def _tool_prov(tool: str) -> Provenance:
    return Provenance(source=ProvenanceSource.deterministic_tool, tool_name=tool, tool_version="1")


def example_edgar_manifest() -> DatasetManifest:
    """A small, truthful EDGAR-shaped panel manifest."""
    return DatasetManifest(
        name="EDGAR financial panel",
        dataset_kind=DatasetKind.tabular_panel,
        columns=[
            ColumnSpec(name="ticker", dtype="str", role=ColumnRole.entity_id, nullable=False),
            ColumnSpec(name="cik", dtype="int", role=ColumnRole.identifier),
            ColumnSpec(name="period", dtype="period", role=ColumnRole.time_index),
            ColumnSpec(name="net_margin", dtype="float", role=ColumnRole.metric, unit="ratio"),
        ],
        entities=["AAPL", "MSFT"],
        provenance=DatasetProvenance(adapter_id="edgar", source="SEC EDGAR companyfacts"),
    )


def example_investigation() -> Investigation:
    """
    A fully-populated, converged EDGAR investigation.

    Demonstrates the full chain: goal -> manifest/dataset -> hypothesis ->
    experiment request/result -> observation -> evidence -> conclusion ->
    termination, with decisions and a critique recorded along the way.
    """
    source = DataSource(kind=DataSourceKind.edgar, name="SEC EDGAR", adapter_id="edgar")
    manifest = example_edgar_manifest()
    manifest.data_source_id = source.id
    dataset = DatasetReference(
        data_source_id=source.id,
        name="AAPL/MSFT panel",
        locator="data/runs/example/processed/panel.csv",
        content_hash="sha256:demo",
        row_count=40,
        manifest=manifest,
    )
    manifest.dataset_reference_id = dataset.id

    goal = InvestigationGoal(
        objective="Identify unusual deterioration in AAPL net margin",
        adapter_id="edgar",
        success_criteria=["At least one supported or rejected hypothesis with linked evidence"],
        parameters={"entities": "AAPL,MSFT", "refresh": "false"},
    )

    investigation = Investigation.start(goal)
    state = investigation.state
    state.datasets.append(dataset)

    hypothesis = Hypothesis(
        statement="AAPL net margin deteriorated abnormally in the last 3 quarters",
        rationale="Goal targets deterioration; net_margin is the priority metric.",
        confidence=0.5,
        status=HypothesisStatus.proposed,
        metric_refs=["net_margin"],
        entity_refs=["AAPL"],
        provenance=_agent_prov("planner"),
    )
    state.add_hypothesis(hypothesis)

    investigation.set_status(InvestigationStatus.planning)
    state.record_decision(
        AgentDecision(
            decision_type=DecisionType.propose_hypothesis,
            rationale="Deterioration goal maps to a margin-decline hypothesis.",
            iteration=0,
            targets=[EntityRef(kind=EntityKind.hypothesis, id=hypothesis.id)],
            provenance=_agent_prov("planner"),
        )
    )

    request = ExperimentRequest(
        tool_name="detect_anomalies",
        parameters={"metric": "net_margin", "zscore_threshold": 2.5, "entities": ["AAPL"]},
        purpose="Test whether recent net_margin values are statistical outliers.",
        target_hypothesis_ids=[hypothesis.id],
        cost_estimate=CostEstimate(compute_seconds=1.5, network_calls=0),
        expected_information_gain=0.7,
        preconditions=[
            Precondition(kind="column_role_present", description="metric column net_margin", ref="net_margin"),
        ],
        provenance=_agent_prov("planner"),
    )
    state.add_experiment_request(request)
    state.record_decision(
        AgentDecision(
            decision_type=DecisionType.select_experiment,
            rationale="Highest expected information gain among candidate experiments.",
            iteration=1,
            targets=[EntityRef(kind=EntityKind.experiment_request, id=request.id)],
            chosen_option="detect_anomalies(net_margin)",
            alternatives_considered=["compute_features", "peer_comparison"],
            provenance=_agent_prov("planner"),
        )
    )
    investigation.set_status(InvestigationStatus.running)
    hypothesis.set_status(HypothesisStatus.active)

    observation = Observation(
        statement="AAPL net_margin z-score = 3.1 in the most recent quarter",
        observation_type=ObservationType.outlier,
        data_reference=SourceReference(kind=ReferenceKind.artifact, ref="anomalies.csv", locator="row=12"),
        magnitude=3.1,
        entity_ref="AAPL",
        metric_ref="net_margin",
        provenance=_tool_prov("detect_anomalies"),
    )
    result = ExperimentResult(
        request_id=request.id,
        tool_name="detect_anomalies",
        status=ExperimentStatus.succeeded,
        observations=[observation],
        artifact_ids=["art_anomalies"],
        metrics={"anomaly_count": 1.0, "max_zscore": 3.1},
        summary="One net_margin outlier detected for AAPL.",
        provenance=_tool_prov("detect_anomalies"),
    )
    state.record_experiment_result(result)

    evidence = Evidence(
        evidence_type=EvidenceType.anomaly_flag,
        source_reference=SourceReference(kind=ReferenceKind.experiment_result, ref=result.id),
        experiment_result_id=result.id,
        hypothesis_ids=[hypothesis.id],
        claim="AAPL net_margin shows a 3.1-sigma decline in the latest quarter",
        direction=EvidenceDirection.supports,
        strength=0.8,
        reliability=0.7,
        coverage=0.6,
        payload_reference=PayloadReference(kind=PayloadKind.artifact, ref="art_anomalies", locator="row=12"),
        artifact_ids=["art_anomalies"],
        provenance=_tool_prov("detect_anomalies"),
    )
    state.add_evidence(evidence)
    hypothesis.set_confidence(0.8)
    hypothesis.set_status(HypothesisStatus.supported)

    state.add_critique(
        Critique(
            critique_type=CritiqueType.competing_explanation,
            severity=CritiqueSeverity.minor,
            target=EntityRef(kind=EntityKind.hypothesis, id=hypothesis.id),
            message="A one-off tax event could explain the single-quarter dip.",
            suggested_action="Check peer comparison before concluding a sustained trend.",
            provenance=_agent_prov("critic"),
        )
    )
    state.add_open_question(
        OpenQuestion(
            question="Is the margin dip sustained across more than one quarter?",
            related_hypothesis_ids=[hypothesis.id],
            provenance=_agent_prov("critic"),
        )
    )

    state.set_conclusion(
        Conclusion(
            statement="AAPL net margin shows a statistically unusual single-quarter decline.",
            disposition=ConclusionDisposition.supported,
            confidence=0.75,
            supporting_hypothesis_ids=[hypothesis.id],
            key_evidence_ids=[evidence.id],
            caveats=["Based on one quarter; sustained-trend confirmation pending."],
            open_question_ids=[q.id for q in state.open_questions],
            provenance=_agent_prov("report"),
        )
    )
    state.confidence = 0.75
    state.record_termination(
        TerminationDecision(
            should_stop=True,
            reason=TerminationReason.sufficient_evidence,
            rationale="Primary hypothesis supported with linked evidence above threshold.",
            at_iteration=state.budget.iterations_used,
            confidence=0.75,
            provenance=_agent_prov("termination_policy"),
        )
    )
    investigation.set_status(InvestigationStatus.converged)
    return investigation


def example_inconclusive_investigation() -> Investigation:
    """An investigation that stops on *insufficient* evidence (a valid outcome)."""
    goal = InvestigationGoal(objective="Detect revenue anomalies with sparse history", adapter_id="edgar")
    investigation = Investigation.start(goal)
    state = investigation.state
    state.budget = BudgetState(max_experiments=2, max_iterations=2)

    hypothesis = Hypothesis(
        statement="Revenue has an abnormal spike",
        rationale="User asked about revenue anomalies.",
        status=HypothesisStatus.proposed,
        provenance=_agent_prov("planner"),
    )
    state.add_hypothesis(hypothesis)
    investigation.set_status(InvestigationStatus.planning)
    investigation.set_status(InvestigationStatus.running)
    hypothesis.set_status(HypothesisStatus.active)

    result = ExperimentResult(
        request_id="expreq_missing",
        tool_name="detect_anomalies",
        status=ExperimentStatus.succeeded,
        metrics={"anomaly_count": 0.0},
        summary="No anomalies; history too short to be conclusive.",
        provenance=_tool_prov("detect_anomalies"),
    )
    state.record_experiment_result(result)
    hypothesis.set_status(HypothesisStatus.unresolved)

    state.add_open_question(
        OpenQuestion(
            question="Is there enough history to detect an anomaly at all?",
            related_hypothesis_ids=[hypothesis.id],
            provenance=_agent_prov("critic"),
        )
    )
    state.record_termination(
        TerminationDecision(
            should_stop=True,
            reason=TerminationReason.insufficient_evidence,
            rationale="No anomaly found and history is too sparse to conclude either way.",
            at_iteration=state.budget.iterations_used,
            confidence=0.2,
            provenance=_agent_prov("termination_policy"),
        )
    )
    investigation.set_status(InvestigationStatus.exhausted)
    return investigation
