"""
Read schemas for the generalized investigation model.

Projects the normalized investigation rows (`backend/models/investigation*.py`) into
stable, typed wire shapes for the read-API. The UI reads hypotheses, evidence, agent
decisions, critiques, experiments, the conclusion, and the append-only event timeline —
the structured state that makes agency inspectable rather than hidden in prompts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from backend.models.investigation import Investigation as InvestigationRow

#: Each ticker is a separate SEC fetch before the loop can start, so the panel build is linear
#: in this number and a large list turns one request into a very long one.
MAX_EDGAR_ENTITIES = 10


class InvestigationDatasetInput(BaseModel):
    """
    What an investigation should run over.

    ``source`` selects the adapter. It defaults to ``tabular`` so every caller written before
    EDGAR was reachable here keeps working unchanged — the field is additive, not a new
    required discriminator.

    The fields are flat rather than a tagged union because the two sources overlap (both carry
    a name and a goal-facing identity) and because a union would have broken that
    compatibility. ``check_source_fields`` enforces which fields each source actually needs, so
    the looseness is in the shape, not in the validation.
    """

    source: Literal["tabular", "edgar"] = "tabular"

    # tabular
    format: Literal["csv", "records"] = "csv"
    csv_text: str | None = None
    records: list[dict] | None = None
    name: str = "dataset"
    time_field: str | None = None
    entity_id_fields: list[str] = Field(default_factory=list)

    # edgar
    entities: list[str] = Field(
        default_factory=list,
        description="Ticker symbols when source is 'edgar' (e.g. ['AAPL', 'MSFT']).",
    )
    refresh: bool = Field(
        default=False,
        description="Force a fresh SEC fetch rather than reusing cached filings.",
    )

    @model_validator(mode="after")
    def check_source_fields(self) -> "InvestigationDatasetInput":
        if self.source == "edgar":
            cleaned = [t.strip().upper() for t in self.entities if t and t.strip()]
            if not cleaned:
                raise ValueError("source 'edgar' requires at least one ticker in 'entities'.")
            if len(cleaned) > MAX_EDGAR_ENTITIES:
                raise ValueError(
                    f"Too many tickers ({len(cleaned)} > {MAX_EDGAR_ENTITIES}). Each one is a "
                    "separate SEC fetch."
                )
            object.__setattr__(self, "entities", cleaned)
            return self
        if self.format == "csv" and not (self.csv_text or "").strip():
            raise ValueError("source 'tabular' with format 'csv' requires 'csv_text'.")
        if self.format == "records" and not self.records:
            raise ValueError("source 'tabular' with format 'records' requires 'records'.")
        return self


class InvestigationCreateRequest(BaseModel):
    project_id: UUID
    goal: str = Field(min_length=1, description="What the investigation should answer.")
    dataset: InvestigationDatasetInput
    async_execution: bool = Field(
        default=False,
        description="Run in the background via the worker (requires a running worker) instead of synchronously.",
    )


class InvestigationCreateResponse(BaseModel):
    analysis_run_id: UUID
    status: str
    db_status: str
    investigation_id: UUID | None = None
    queued: bool = False


def _as_list(value: Any) -> list:
    return list(value) if isinstance(value, (list, tuple)) else []


def _goal_field(row: InvestigationRow, key: str) -> Any:
    goal = row.goal_json if isinstance(row.goal_json, dict) else {}
    return goal.get(key)


class InvestigationCounts(BaseModel):
    hypotheses: int = 0
    evidence: int = 0
    experiments: int = 0
    observations: int = 0
    decisions: int = 0
    critiques: int = 0
    open_questions: int = 0


class InvestigationSummary(BaseModel):
    id: UUID
    domain_id: str | None = None
    analysis_run_id: UUID | None = None
    project_id: UUID | None = None
    origin: str
    status: str
    confidence: float | None = None
    objective: str | None = None
    adapter_id: str | None = None
    conclusion: str | None = None
    counts: InvestigationCounts
    created_at: datetime
    updated_at: datetime


class HypothesisItem(BaseModel):
    id: str
    statement: str
    status: str
    confidence: float
    prior_confidence: float
    rationale: str | None = None
    metric_refs: list = []
    entity_refs: list = []


class EvidenceItem(BaseModel):
    id: str
    claim: str
    evidence_type: str
    direction: str
    strength: float
    reliability: float
    coverage: float
    experiment_result_id: str | None = None
    hypothesis_ids: list[str] = []
    statistics: dict | None = None


class ArtifactRef(BaseModel):
    """A downloadable artifact emitted by an experiment (bytes served via the artifacts API)."""

    id: UUID
    name: str
    kind: str
    mime_type: str | None = None
    byte_size: int | None = None


class ExperimentItem(BaseModel):
    id: str
    tool_name: str
    status: str
    summary: str | None = None
    metrics: dict | None = None
    error: dict | None = None
    request_domain_id: str | None = None
    created_at: datetime
    artifacts: list[ArtifactRef] = []


class ObservationItem(BaseModel):
    id: str
    statement: str
    observation_type: str
    magnitude: float | None = None
    entity_ref: str | None = None
    metric_ref: str | None = None
    experiment_result_id: str | None = None


class DecisionItem(BaseModel):
    id: str
    sequence: int
    decision_type: str
    rationale: str
    iteration: int
    chosen_option: str | None = None
    alternatives: list = []


class CritiqueItem(BaseModel):
    id: str
    critique_type: str
    severity: str
    target_kind: str
    target_id: str
    message: str
    suggested_action: str | None = None
    resolved: bool = False


class OpenQuestionItem(BaseModel):
    id: str
    question: str
    status: str
    priority: int
    answer: str | None = None
    related_hypothesis_ids: list[str] = []


class ConclusionItem(BaseModel):
    id: str
    statement: str
    disposition: str
    confidence: float
    caveats: list[str] = []
    supporting_hypothesis_ids: list[str] = []
    key_evidence_ids: list[str] = []


class DatasetItem(BaseModel):
    id: str | None = None
    name: str
    locator: str | None = None
    row_count: int | None = None
    content_hash: str | None = None


class EventItem(BaseModel):
    sequence: int
    event_type: str
    entity_kind: str | None = None
    entity_id: str | None = None
    payload: dict | None = None
    created_at: datetime


class TerminationView(BaseModel):
    reason: str | None = None
    rationale: str | None = None
    at_iteration: int | None = None


class InvestigationDetail(InvestigationSummary):
    objective: str | None = None
    success_criteria: list[str] = []
    constraints: list[str] = []
    termination: TerminationView | None = None
    hypotheses: list[HypothesisItem] = []
    evidence: list[EvidenceItem] = []
    experiments: list[ExperimentItem] = []
    observations: list[ObservationItem] = []
    decisions: list[DecisionItem] = []
    critiques: list[CritiqueItem] = []
    open_questions: list[OpenQuestionItem] = []
    conclusion_detail: ConclusionItem | None = None
    datasets: list[DatasetItem] = []
    events: list[EventItem] = []


# -- projectors --------------------------------------------------------------


def _current_conclusion_row(row: InvestigationRow):
    if row.current_conclusion_id is None:
        return None
    return next((c for c in row.conclusions if c.id == row.current_conclusion_id), None)


def build_summary(row: InvestigationRow) -> InvestigationSummary:
    concl = _current_conclusion_row(row)
    return InvestigationSummary(
        id=row.id,
        domain_id=row.domain_id,
        analysis_run_id=row.analysis_run_id,
        project_id=row.project_id,
        origin=row.origin.value,
        status=row.status,
        confidence=row.confidence,
        objective=_goal_field(row, "objective"),
        adapter_id=_goal_field(row, "adapter_id"),
        conclusion=concl.statement if concl is not None else None,
        counts=InvestigationCounts(
            hypotheses=len(row.hypotheses),
            evidence=len(row.evidence),
            experiments=len(row.experiment_results),
            observations=len(row.observations),
            decisions=len(row.decisions),
            critiques=len(row.critiques),
            open_questions=len(row.open_questions),
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _hypothesis(h) -> HypothesisItem:
    return HypothesisItem(
        id=h.domain_id, statement=h.statement, status=h.status, confidence=h.confidence,
        prior_confidence=h.prior_confidence, rationale=h.rationale,
        metric_refs=_as_list(h.metric_refs_json), entity_refs=_as_list(h.entity_refs_json),
    )


def _evidence(e) -> EvidenceItem:
    hyp_ids = [str(link.hypothesis_id) for link in e.hypothesis_links]
    return EvidenceItem(
        id=e.domain_id, claim=e.claim, evidence_type=e.evidence_type, direction=e.direction,
        strength=e.strength, reliability=e.reliability, coverage=e.coverage,
        experiment_result_id=(str(e.experiment_result_id) if e.experiment_result_id else None),
        hypothesis_ids=hyp_ids,
        statistics=e.statistics_json if isinstance(e.statistics_json, dict) else None,
    )


def _artifact_ref(link) -> ArtifactRef:
    a = link.artifact
    meta = a.meta_json if isinstance(a.meta_json, dict) else {}
    name = str(meta.get("artifact_name") or a.role_key.rsplit("/", 1)[-1] or "artifact")
    return ArtifactRef(
        id=a.id, name=name, kind=a.kind.value if hasattr(a.kind, "value") else str(a.kind),
        mime_type=a.mime_type, byte_size=a.byte_size,
    )


def _experiment(x) -> ExperimentItem:
    return ExperimentItem(
        id=x.domain_id, tool_name=x.tool_name, status=x.status, summary=x.summary,
        metrics=x.metrics_json if isinstance(x.metrics_json, dict) else None,
        error=x.error_json if isinstance(x.error_json, dict) else None,
        request_domain_id=x.request_domain_id, created_at=x.created_at,
        artifacts=[_artifact_ref(link) for link in x.artifact_links],
    )


def _observation(o) -> ObservationItem:
    return ObservationItem(
        id=o.domain_id, statement=o.statement, observation_type=o.observation_type,
        magnitude=o.magnitude, entity_ref=o.entity_ref, metric_ref=o.metric_ref,
        experiment_result_id=(str(o.experiment_result_id) if o.experiment_result_id else None),
    )


def _decision(d) -> DecisionItem:
    return DecisionItem(
        id=d.domain_id, sequence=d.sequence, decision_type=d.decision_type, rationale=d.rationale,
        iteration=d.iteration, chosen_option=d.chosen_option, alternatives=_as_list(d.alternatives_json),
    )


def _critique(c) -> CritiqueItem:
    return CritiqueItem(
        id=c.domain_id, critique_type=c.critique_type, severity=c.severity, target_kind=c.target_kind,
        target_id=c.target_id, message=c.message, suggested_action=c.suggested_action, resolved=c.resolved,
    )


def _open_question(q) -> OpenQuestionItem:
    return OpenQuestionItem(
        id=q.domain_id, question=q.question, status=q.status, priority=q.priority, answer=q.answer,
        related_hypothesis_ids=[str(x) for x in _as_list(q.related_hypothesis_ids_json)],
    )


def _termination(row: InvestigationRow) -> TerminationView | None:
    t = row.termination_json if isinstance(row.termination_json, dict) else None
    if not t:
        return None
    return TerminationView(reason=t.get("reason"), rationale=t.get("rationale"), at_iteration=t.get("at_iteration"))


def build_detail(row: InvestigationRow) -> InvestigationDetail:
    summary = build_summary(row)
    concl = _current_conclusion_row(row)
    conclusion_detail = None
    if concl is not None:
        conclusion_detail = ConclusionItem(
            id=concl.domain_id, statement=concl.statement, disposition=concl.disposition,
            confidence=concl.confidence, caveats=[str(x) for x in _as_list(concl.caveats_json)],
            supporting_hypothesis_ids=[str(x) for x in _as_list(concl.supporting_hypothesis_ids_json)],
            key_evidence_ids=[str(x) for x in _as_list(concl.key_evidence_ids_json)],
        )
    return InvestigationDetail(
        **summary.model_dump(),
        success_criteria=[str(x) for x in _as_list(_goal_field(row, "success_criteria"))],
        constraints=[str(x) for x in _as_list(_goal_field(row, "constraints"))],
        termination=_termination(row),
        hypotheses=[_hypothesis(h) for h in row.hypotheses],
        evidence=[_evidence(e) for e in row.evidence],
        experiments=[_experiment(x) for x in sorted(row.experiment_results, key=lambda r: r.created_at)],
        observations=[_observation(o) for o in row.observations],
        decisions=[_decision(d) for d in sorted(row.decisions, key=lambda d: d.sequence)],
        critiques=[_critique(c) for c in row.critiques],
        open_questions=[_open_question(q) for q in sorted(row.open_questions, key=lambda q: -q.priority)],
        conclusion_detail=conclusion_detail,
        datasets=[
            DatasetItem(id=d.domain_id, name=d.name, locator=d.locator, row_count=d.row_count,
                        content_hash=d.content_hash)
            for d in row.datasets
        ],
        events=[
            EventItem(sequence=e.sequence, event_type=e.event_type, entity_kind=e.entity_kind,
                      entity_id=e.entity_id, payload=e.payload_json if isinstance(e.payload_json, dict) else None,
                      created_at=e.created_at)
            for e in sorted(row.events, key=lambda e: e.sequence)
        ],
    )
