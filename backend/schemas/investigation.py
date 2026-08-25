"""
Read schemas for the generalized investigation model.

Projects the normalized investigation rows (`backend/models/investigation*.py`) into
stable, typed wire shapes for the read-API. The UI reads hypotheses, evidence, agent
decisions, critiques, experiments, the conclusion, and the append-only event timeline —
the structured state that makes agency inspectable rather than hidden in prompts.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from backend.models.investigation import Investigation as InvestigationRow
from backend.models.investigation import InvestigationDataset
from backend.models.investigation_entities import CritiqueRow

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
    #: Where these rows came from, declared by the caller. Surfaced on the published run so a
    #: reader never has to infer whether a demo analysed real data; EDGAR sets it itself.
    dataset_origin: Literal["live", "synthetic", "user_upload", "unknown"] = "unknown"

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


class InvestigationOutcome(BaseModel):
    """
    How a run actually ended, classified from persisted state.

    ``status`` alone is misleading in the place it matters most: a run that correctly declined
    to answer is stored as ``exhausted``, which reads to a newcomer as a failure. The honest
    headline is the *outcome* — did claims stand, did they conflict, did the loop decline —
    and that needs the termination reason, the claim statuses and the critique types together.

    Classified here rather than in each client so the API, the static export and any future
    surface agree on what a run was. The wording of the label is a presentation decision and
    stays with the caller; this is only the classification and the counts behind it.
    """

    #: unanswerable | contradicted | mixed | supported | refuted | declined | stopped
    kind: str
    termination_reason: str | None = None
    claims_supported: int = 0
    claims_rejected: int = 0
    claims_weakened: int = 0
    claims_unresolved: int = 0
    #: True when the loop found two of its own supported claims mutually exclusive.
    contradiction_found: bool = False


#: Terminations where the loop was cut off rather than reaching a view of the evidence.
_STOPPED_EARLY = {"budget_exhausted", "safety_constraint", "repeated_failure", "user_stop"}


def _dataset_item(row: InvestigationDataset) -> "DatasetItem":
    """
    One dataset as the API serves it, including where its rows came from.

    Lineage lives inside the persisted manifest rather than in its own columns, so it is read
    back out here. Defaulting ``origin`` to ``unknown`` rather than to ``live`` is the point:
    a run recorded before this field existed cannot be shown to have used real data, and
    saying so is cheaper than being wrong about it.
    """
    manifest = getattr(row, "manifest_json", None)
    provenance = manifest.get("provenance") if isinstance(manifest, dict) else None
    provenance = provenance if isinstance(provenance, dict) else {}
    return DatasetItem(
        id=row.domain_id,
        name=row.name,
        locator=row.locator,
        row_count=row.row_count,
        content_hash=row.content_hash,
        source=provenance.get("source"),
        origin=str(provenance.get("origin") or "unknown"),
    )


def _summary_origin(row: InvestigationRow) -> str:
    """One origin for the whole run, for the listing. ``mixed`` when its datasets disagree."""
    origins = {_dataset_item(d).origin for d in row.datasets}
    if not origins:
        return "unknown"
    return origins.pop() if len(origins) == 1 else "mixed"


def _pair_was_separated(statuses: dict[str, str], critique: CritiqueRow) -> bool:
    """
    True when evidence left exactly one side of a contradiction standing.

    Read-model mirror of ``agentic.agent.components._contradiction_is_settled``, and needed
    only for rows written before the loop maintained ``resolved`` itself. Returns False when
    the second side is unknown — a conflict whose pairing was never recorded cannot be shown
    to have been settled, and guessing in the permissive direction would hide a live one.
    """
    other = getattr(critique, "conflicts_with_id", None)
    target = str(getattr(critique, "target_id", "") or "")
    if not other or not target:
        return False
    pair = [statuses.get(target), statuses.get(str(other))]
    if any(s is None for s in pair):
        return False
    return sum(1 for s in pair if s == "supported") == 1


def _build_outcome(row: InvestigationRow) -> InvestigationOutcome:
    counts = Counter(str(h.status) for h in row.hypotheses)
    termination = row.termination_json if isinstance(row.termination_json, dict) else {}
    reason = termination.get("reason")
    reason = str(reason) if reason is not None else None

    # Persisted `resolved` is now maintained by the loop (a conflict is settled when evidence
    # leaves exactly one of the pair standing), so this reads it rather than recomputing.
    # Guarded by the claim statuses as well: a run stored before the loop learned to settle
    # conflicts has `resolved=False` on a pair the evidence plainly separated, and reporting
    # that as a live contradiction would misdescribe every historical row.
    statuses = {str(h.domain_id): str(h.status) for h in row.hypotheses}
    contradiction = any(
        str(c.critique_type) == "contradiction"
        and not c.resolved
        and not _pair_was_separated(statuses, c)
        for c in row.critiques
    )
    supported = counts.get("supported", 0)
    rejected = counts.get("rejected", 0)
    weakened = counts.get("weakened", 0)
    unresolved = counts.get("unresolved", 0)

    if reason == "unanswerable_premise":
        # Ordered first: this run never got as far as having claims to classify, and the
        # distinction it carries is the one a reader most needs. "Declined" says the evidence
        # did not settle it; "unanswerable" says no evidence here could, which is the
        # difference between running more analysis and bringing a different dataset.
        kind = "unanswerable"
    elif contradiction:
        # Ordered next deliberately: a run holding two claims that cannot both be true has
        # not concluded anything, whatever else its claims say.
        kind = "contradicted"
    elif reason in _STOPPED_EARLY:
        kind = "stopped"
    elif supported and (rejected or weakened or unresolved):
        kind = "mixed"
    elif supported:
        kind = "supported"
    elif rejected and not (weakened or unresolved):
        # Every claim was actively overturned by the run's own evidence. Distinct from
        # `declined`, which says the evidence did not settle the matter: this run settled it,
        # and the answer was no. Collapsing the two reported "no claim survived the evidence"
        # for a run that had in fact disproved its own hypotheses — the strongest thing an
        # investigation can do, described as a failure to conclude.
        kind = "refuted"
    else:
        kind = "declined"

    return InvestigationOutcome(
        kind=kind,
        termination_reason=reason,
        claims_supported=supported,
        claims_rejected=rejected,
        claims_weakened=weakened,
        claims_unresolved=unresolved,
        contradiction_found=contradiction,
    )


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
    #: Public replay-tier slug when the investigation is published (see /v1/demos); the
    #: listing is useless to a client without the URL segment that reaches the detail.
    demo_slug: str | None = None
    counts: InvestigationCounts
    #: How the run ended, classified from persisted state — see :class:`InvestigationOutcome`.
    outcome: InvestigationOutcome
    #: Where this run's data came from — ``live``, ``synthetic``, ``user_upload`` or
    #: ``unknown``. On the *summary* because the listing is where a reader decides what a set
    #: of runs is worth, and a set that mixes real filings with generated rows has to say so
    #: there rather than one detail page down. ``mixed`` when a run spans several sources.
    dataset_origin: str = "unknown"
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
    #: The claims this experiment was raised to test, in the same domain-id space as
    #: `hypotheses[].id`. Empty when the request behind it was not recorded — true of every
    #: run before the request-persistence fix, so a reader must treat empty as "unknown"
    #: rather than "tested nothing".
    target_hypothesis_ids: list[str] = []
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


class EntityRefItem(BaseModel):
    kind: str
    id: str


class DecisionItem(BaseModel):
    id: str
    sequence: int
    decision_type: str
    rationale: str
    iteration: int
    chosen_option: str | None = None
    alternatives: list = []
    #: What the decision acted on. Exposed because it is the only structured link between a
    #: decision and the claims behind it: a contradiction weakens two hypotheses in one act
    #: and carries both here, which is what lets a client render it as one event rather than
    #: two unrelated rows. Without this the ids exist only in prose, if at all.
    targets: list[EntityRefItem] = []


class CritiqueItem(BaseModel):
    id: str
    critique_type: str
    severity: str
    target_kind: str
    target_id: str
    #: The other claim, when this is a ``contradiction``. Lets a client show both sides of a
    #: conflict and check for itself whether the run went on to separate them.
    conflicts_with_id: str | None = None
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
    #: The finding as prose, when the run recorded one whose every figure was verified
    #: against its own state. Null is ordinary — `statement` is the answer of record.
    narrative: str | None = None
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
    #: Human-readable lineage, e.g. "SEC EDGAR companyfacts (AAPL, MSFT, NVDA)".
    source: str | None = None
    #: live | synthetic | user_upload | unknown. Served so a client never has to guess
    #: whether a published run analysed real data — see ``DatasetOrigin``.
    origin: str = "unknown"


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
        demo_slug=row.demo_slug,
        counts=InvestigationCounts(
            hypotheses=len(row.hypotheses),
            evidence=len(row.evidence),
            experiments=len(row.experiment_results),
            observations=len(row.observations),
            decisions=len(row.decisions),
            critiques=len(row.critiques),
            open_questions=len(row.open_questions),
        ),
        outcome=_build_outcome(row),
        dataset_origin=_summary_origin(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _hypothesis(h) -> HypothesisItem:
    return HypothesisItem(
        id=h.domain_id, statement=h.statement, status=h.status, confidence=h.confidence,
        prior_confidence=h.prior_confidence, rationale=h.rationale,
        metric_refs=_as_list(h.metric_refs_json), entity_refs=_as_list(h.entity_refs_json),
    )


def _evidence(e, hypothesis_domain_ids: dict[str, str], experiment_domain_ids: dict[str, str]) -> EvidenceItem:
    """
    One evidence item, with its links expressed in the same id space as everything else.

    Every other item in this contract is keyed by ``domain_id`` — ``HypothesisItem.id``,
    ``ExperimentItem.id``. These two links used to be emitted as database primary keys, so
    they could not be joined against the things they point at: ``evidenceForHypothesis`` in
    the frontend matched zero rows on every published demo, and the trace rendered claims with
    no supporting evidence rather than failing loudly.

    A link that cannot be resolved is dropped rather than emitted in a foreign id space,
    because a dangling id invites exactly the silent-empty-join this is fixing.
    """
    hyp_ids = [
        hypothesis_domain_ids[key]
        for link in e.hypothesis_links
        if (key := str(link.hypothesis_id)) in hypothesis_domain_ids
    ]
    experiment_id = (
        experiment_domain_ids.get(str(e.experiment_result_id)) if e.experiment_result_id else None
    )
    return EvidenceItem(
        id=e.domain_id, claim=e.claim, evidence_type=e.evidence_type, direction=e.direction,
        strength=e.strength, reliability=e.reliability, coverage=e.coverage,
        experiment_result_id=experiment_id,
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


def _experiment(x, request_targets: dict[str, list[str]] | None = None) -> ExperimentItem:
    targets = (request_targets or {}).get(x.request_domain_id or "", [])
    return ExperimentItem(
        id=x.domain_id, tool_name=x.tool_name, status=x.status, summary=x.summary,
        metrics=x.metrics_json if isinstance(x.metrics_json, dict) else None,
        error=x.error_json if isinstance(x.error_json, dict) else None,
        request_domain_id=x.request_domain_id, target_hypothesis_ids=targets,
        created_at=x.created_at,
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
        targets=[
            EntityRefItem(kind=str(t.get("kind", "")), id=str(t.get("id", "")))
            for t in _as_list(d.targets_json)
            if isinstance(t, dict) and t.get("id")
        ],
    )


def _critique(c) -> CritiqueItem:
    return CritiqueItem(
        id=c.domain_id, critique_type=c.critique_type, severity=c.severity, target_kind=c.target_kind,
        target_id=c.target_id, conflicts_with_id=c.conflicts_with_id,
        message=c.message, suggested_action=c.suggested_action, resolved=c.resolved,
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
            id=concl.domain_id, statement=concl.statement, narrative=concl.narrative,
            disposition=concl.disposition,
            confidence=concl.confidence, caveats=[str(x) for x in _as_list(concl.caveats_json)],
            supporting_hypothesis_ids=[str(x) for x in _as_list(concl.supporting_hypothesis_ids_json)],
            key_evidence_ids=[str(x) for x in _as_list(concl.key_evidence_ids_json)],
        )
    # Primary key -> domain id, so evidence links come out in the id space every other item
    # in this response is keyed by. Built once from rows already loaded.
    # Which claims each experiment was raised to test, keyed by the request domain id the
    # result carries. Already domain ids on both sides, so nothing to resolve.
    request_targets = {
        r.domain_id: [str(x) for x in _as_list(r.target_hypothesis_ids_json)]
        for r in row.experiment_requests
    }
    hypothesis_domain_ids = {str(h.id): h.domain_id for h in row.hypotheses}
    experiment_domain_ids = {str(x.id): x.domain_id for x in row.experiment_results}
    return InvestigationDetail(
        **summary.model_dump(),
        success_criteria=[str(x) for x in _as_list(_goal_field(row, "success_criteria"))],
        constraints=[str(x) for x in _as_list(_goal_field(row, "constraints"))],
        termination=_termination(row),
        hypotheses=[_hypothesis(h) for h in row.hypotheses],
        evidence=[_evidence(e, hypothesis_domain_ids, experiment_domain_ids) for e in row.evidence],
        experiments=[
            _experiment(x, request_targets)
            for x in sorted(row.experiment_results, key=lambda r: r.created_at)
        ],
        observations=[_observation(o) for o in row.observations],
        decisions=[_decision(d) for d in sorted(row.decisions, key=lambda d: d.sequence)],
        critiques=[_critique(c) for c in row.critiques],
        open_questions=[_open_question(q) for q in sorted(row.open_questions, key=lambda q: -q.priority)],
        conclusion_detail=conclusion_detail,
        datasets=[_dataset_item(d) for d in row.datasets],
        events=[
            EventItem(sequence=e.sequence, event_type=e.event_type, entity_kind=e.entity_kind,
                      entity_id=e.entity_id, payload=e.payload_json if isinstance(e.payload_json, dict) else None,
                      created_at=e.created_at)
            for e in sorted(row.events, key=lambda e: e.sequence)
        ],
    )
