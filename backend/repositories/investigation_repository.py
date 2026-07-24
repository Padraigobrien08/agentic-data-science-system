"""
Persistence for the generalized investigation model.

``InvestigationRepository`` is the interface; ``SqlAlchemyInvestigationRepository``
is the implementation. It maps the framework-independent domain aggregate
(``agentic.domain``) onto the ORM rows, maintains the append-only event log and
durable checkpoints, records experiment results idempotently, and imports legacy
EDGAR ``analysis_runs`` as compatibility investigations.

Source of truth:
  * native investigations   -> these tables (the normalized rows + latest checkpoint).
  * legacy-import investigations -> the linked ``analysis_runs`` row remains the
    source of truth; the investigation is a queryable representation.

Exact resume is served from the latest :class:`OrchestrationCheckpoint`, which
stores the full serialized ``InvestigationState``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from agentic.domain import (
    AgentDecision,
    BudgetState,
    Conclusion,
    Critique,
    DatasetReference,
    Evidence,
    ExperimentRequest,
    ExperimentResult,
    Hypothesis,
    Investigation as DomainInvestigation,
    InvestigationGoal,
    InvestigationState,
    InvestigationStatus,
    Observation,
    OpenQuestion,
    ReproducibilityManifest,
    TerminationDecision,
)
from agentic.domain.enums import ConclusionDisposition
from agentic.domain.provenance import Provenance
from backend.models.analysis_run import AnalysisRun
from backend.models.enums_investigation import InvestigationOrigin, StateEventType
from backend.models.investigation import (
    Investigation,
    InvestigationDataset,
    InvestigationStateEvent,
    OrchestrationCheckpoint,
    ReproducibilityManifestRow,
)
from backend.models.investigation_entities import (
    AgentDecisionRow,
    ConclusionRow,
    CritiqueRow,
    EvidenceArtifactLink,
    EvidenceHypothesisLink,
    EvidenceRow,
    ExperimentRequestRow,
    ExperimentResultArtifactLink,
    ExperimentResultRow,
    HypothesisRow,
    ObservationRow,
    OpenQuestionRow,
)


class InvestigationConcurrencyError(RuntimeError):
    """Raised when a save is attempted against a stale ``state_version``."""


class InvestigationNotFoundError(LookupError):
    """Raised when an investigation id has no row."""


def _json(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [v.model_dump(mode="json") if hasattr(v, "model_dump") else v for v in value]
    return value


_LEGACY_STATUS_MAP = {
    "success": InvestigationStatus.converged,
    "partial_success": InvestigationStatus.converged,
    "no_data": InvestigationStatus.exhausted,
    "error": InvestigationStatus.failed,
    "cancelled": InvestigationStatus.failed,
    "pending": InvestigationStatus.created,
    "queued": InvestigationStatus.created,
    "running": InvestigationStatus.running,
}


@runtime_checkable
class InvestigationRepository(Protocol):
    """Interface for persisting and restoring generalized investigations."""

    def create(self, investigation: DomainInvestigation, **kwargs) -> Investigation: ...

    def get(self, investigation_id: UUID) -> Investigation | None: ...

    def load_domain(self, investigation_id: UUID) -> DomainInvestigation: ...

    def save_state(self, investigation_id: UUID, investigation: DomainInvestigation, **kwargs) -> Investigation: ...

    def record_experiment_result(
        self, investigation_id: UUID, *, result: ExperimentResult, idempotency_key: str, **kwargs
    ) -> tuple[ExperimentResultRow, bool]: ...


class SqlAlchemyInvestigationRepository:
    """SQLAlchemy implementation of :class:`InvestigationRepository`."""

    def __init__(self, session: Session) -> None:
        self._s = session

    # -- lookups -------------------------------------------------------------

    def get(self, investigation_id: UUID) -> Investigation | None:
        return self._s.get(Investigation, investigation_id)

    def require(self, investigation_id: UUID) -> Investigation:
        row = self.get(investigation_id)
        if row is None:
            raise InvestigationNotFoundError(str(investigation_id))
        return row

    def get_by_domain_id(self, domain_id: str) -> Investigation | None:
        return self._s.scalar(select(Investigation).where(Investigation.domain_id == domain_id))

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Investigation | None:
        return self._s.scalar(select(Investigation).where(Investigation.analysis_run_id == analysis_run_id))

    def list_for_user(
        self, user_id: UUID, *, project_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[Investigation]:
        """Investigations owned by the user's projects or initiated by the user, newest first.

        When ``project_id`` is given it is scoped to that project (which the caller must have
        already confirmed the user owns).
        """
        from backend.models.project import Project

        stmt = select(Investigation)
        if project_id is not None:
            stmt = stmt.where(Investigation.project_id == project_id)
        else:
            owned_projects = select(Project.id).where(Project.owner_user_id == user_id)
            stmt = stmt.where(
                (Investigation.project_id.in_(owned_projects))
                | (Investigation.initiated_by_user_id == user_id)
            )
        stmt = stmt.order_by(Investigation.created_at.desc()).limit(limit).offset(offset)
        return list(self._s.scalars(stmt).all())

    # -- create --------------------------------------------------------------

    def create(
        self,
        investigation: DomainInvestigation,
        *,
        project_id: UUID | None = None,
        initiated_by_user_id: UUID | None = None,
        analysis_run_id: UUID | None = None,
        origin: InvestigationOrigin = InvestigationOrigin.native,
    ) -> Investigation:
        state = investigation.state
        repro_row = self._persist_repro(investigation.reproducibility, investigation_id=None)
        row = Investigation(
            domain_id=investigation.id,
            project_id=project_id,
            initiated_by_user_id=initiated_by_user_id,
            analysis_run_id=analysis_run_id,
            origin=origin,
            status=investigation.status.value,
            schema_version=investigation.schema_version,
            goal_json=_json(state.objective),
            confidence=state.confidence,
            budget_json=_json(state.budget),
            termination_json=_json(state.termination),
        )
        self._s.add(row)
        self._s.flush()
        if repro_row is not None:
            repro_row.investigation_id = row.id
            row.reproducibility_manifest_id = repro_row.id
        self._persist_children(row, state, initial=True)
        self._append_event(row, StateEventType.created, payload={"origin": origin.value})
        self._save_checkpoint(row, investigation, label="created")
        self._s.flush()
        return row

    # -- save / resume -------------------------------------------------------

    def save_state(
        self,
        investigation_id: UUID,
        investigation: DomainInvestigation,
        *,
        expected_state_version: int | None = None,
        event_type: StateEventType = StateEventType.status_changed,
        label: str | None = None,
    ) -> Investigation:
        row = self.require(investigation_id)
        if expected_state_version is not None and row.state_version != expected_state_version:
            raise InvestigationConcurrencyError(
                f"stale state_version: expected {expected_state_version}, have {row.state_version}"
            )
        state = investigation.state
        row.status = investigation.status.value
        row.confidence = state.confidence
        row.goal_json = _json(state.objective)
        row.budget_json = _json(state.budget)
        row.termination_json = _json(state.termination)
        # Touch a real column so version_id_col bumps state_version on every save
        # (gives optimistic-concurrency conflict detection between concurrent saves).
        row.updated_at = _utcnow()
        self._persist_children(row, state, initial=False)
        self._append_event(row, event_type, payload={"status": investigation.status.value})
        self._save_checkpoint(row, investigation, label=label)
        # version_id_col bumps state_version on flush (optimistic concurrency).
        self._s.flush()
        return row

    def load_domain(self, investigation_id: UUID) -> DomainInvestigation:
        """Restore the exact domain aggregate from the latest checkpoint."""
        cp = self.latest_checkpoint(investigation_id)
        if cp is None:
            raise InvestigationNotFoundError(f"no checkpoint for investigation {investigation_id}")
        return DomainInvestigation.model_validate(cp.state_json)

    def latest_checkpoint(self, investigation_id: UUID) -> OrchestrationCheckpoint | None:
        return self._s.scalar(
            select(OrchestrationCheckpoint)
            .where(OrchestrationCheckpoint.investigation_id == investigation_id)
            .order_by(OrchestrationCheckpoint.sequence.desc())
            .limit(1)
        )

    def list_events(self, investigation_id: UUID) -> list[InvestigationStateEvent]:
        return list(
            self._s.scalars(
                select(InvestigationStateEvent)
                .where(InvestigationStateEvent.investigation_id == investigation_id)
                .order_by(InvestigationStateEvent.sequence)
            ).all()
        )

    # -- idempotent experiment recording ------------------------------------

    def record_experiment_result(
        self,
        investigation_id: UUID,
        *,
        result: ExperimentResult,
        idempotency_key: str,
        input_fingerprint: str | None = None,
        output_fingerprint: str | None = None,
        request_row_id: UUID | None = None,
    ) -> tuple[ExperimentResultRow, bool]:
        """Insert a result once. A retry with the same key returns the existing row."""
        existing = self._s.scalar(
            select(ExperimentResultRow).where(
                ExperimentResultRow.investigation_id == investigation_id,
                ExperimentResultRow.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing, False

        repro_row = self._persist_repro(result.reproducibility, investigation_id=investigation_id)
        res_row = ExperimentResultRow(
            investigation_id=investigation_id,
            domain_id=result.id,
            request_id=request_row_id,
            request_domain_id=result.request_id,
            tool_name=result.tool_name,
            status=result.status.value,
            idempotency_key=idempotency_key,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            metrics_json=dict(result.metrics),
            summary=result.summary,
            error_json=_json(result.error),
            reproducibility_manifest_id=repro_row.id if repro_row is not None else None,
            provenance_json=_json(result.provenance),
        )
        self._s.add(res_row)
        self._s.flush()
        for obs in result.observations:
            self._s.add(self._observation_row(investigation_id, obs, experiment_result_id=res_row.id))
        row = self.get(investigation_id)
        if row is not None:
            self._append_event(
                row, StateEventType.experiment_recorded, entity_id=result.id,
                payload={"tool": result.tool_name, "status": result.status.value},
            )
        self._s.flush()
        return res_row, True

    # -- artifact linkage (to the existing artifacts table) ------------------

    def link_evidence_artifact(self, evidence_row_id: UUID, artifact_id: UUID) -> EvidenceArtifactLink:
        link = EvidenceArtifactLink(evidence_id=evidence_row_id, artifact_id=artifact_id)
        self._s.add(link)
        self._s.flush()
        return link

    def link_experiment_result_artifact(self, result_row_id: UUID, artifact_id: UUID) -> ExperimentResultArtifactLink:
        link = ExperimentResultArtifactLink(experiment_result_id=result_row_id, artifact_id=artifact_id)
        self._s.add(link)
        self._s.flush()
        return link

    # -- legacy compatibility ------------------------------------------------

    def import_legacy_run(self, analysis_run: AnalysisRun) -> Investigation:
        """Represent an existing EDGAR run as a legacy-import investigation."""
        existing = self.get_by_analysis_run_id(analysis_run.id)
        if existing is not None:
            return existing

        payload = analysis_run.input_payload_json if isinstance(analysis_run.input_payload_json, dict) else {}
        tickers = [str(t) for t in (payload.get("tickers") or [])]
        goal_text = (
            payload.get("analysis_goal")
            or analysis_run.orchestration_goal_text
            or "Legacy EDGAR analysis run"
        )
        status = _LEGACY_STATUS_MAP.get(analysis_run.status.value, InvestigationStatus.converged)
        prov = Provenance.system(note=f"imported from analysis_run {analysis_run.id}")
        goal = InvestigationGoal(
            objective=str(goal_text), adapter_id="edgar",
            parameters={"tickers": ",".join(tickers), "analysis_run_id": str(analysis_run.id)},
        )
        state = InvestigationState(objective=goal)
        if tickers:
            state.datasets.append(
                DatasetReference(name="EDGAR financial panel", locator=str(analysis_run.id))
            )
        out = analysis_run.output_payload_json if isinstance(analysis_run.output_payload_json, dict) else {}
        message = out.get("message") or out.get("final_summary") or goal_text
        disposition = (
            ConclusionDisposition.supported
            if status is InvestigationStatus.converged
            else ConclusionDisposition.insufficient_evidence
        )
        state.set_conclusion(
            Conclusion(statement=str(message), disposition=disposition, provenance=prov)
        )
        investigation = DomainInvestigation(status=status, state=state)
        return self.create(
            investigation,
            project_id=analysis_run.project_id,
            initiated_by_user_id=analysis_run.initiated_by_user_id,
            analysis_run_id=analysis_run.id,
            origin=InvestigationOrigin.legacy_import,
        )

    # -- internals -----------------------------------------------------------

    def _existing_domain_ids(self, model, investigation_id: UUID) -> set[str]:
        return set(
            self._s.scalars(
                select(model.domain_id).where(model.investigation_id == investigation_id)
            ).all()
        )

    def _persist_children(self, row: Investigation, state: InvestigationState, *, initial: bool) -> None:
        inv_id = row.id

        for dref in state.datasets:
            self._s.add(InvestigationDataset(
                investigation_id=inv_id, domain_id=dref.id, name=dref.name,
                data_source_json=None, locator=dref.locator, content_hash=dref.content_hash,
                row_count=dref.row_count, manifest_json=_json(dref.manifest),
            ))

        existing_hyp = self._existing_domain_ids(HypothesisRow, inv_id) if not initial else set()
        for h in state.hypotheses:
            if h.id in existing_hyp:
                r = self._s.scalar(select(HypothesisRow).where(
                    HypothesisRow.investigation_id == inv_id, HypothesisRow.domain_id == h.id))
                if r is not None:
                    r.status, r.confidence = h.status.value, h.confidence
                continue
            self._s.add(self._hypothesis_row(inv_id, h))

        existing_req = self._existing_domain_ids(ExperimentRequestRow, inv_id) if not initial else set()
        for req in [*state.pending_experiments]:
            if req.id in existing_req:
                r = self._s.scalar(select(ExperimentRequestRow).where(
                    ExperimentRequestRow.investigation_id == inv_id, ExperimentRequestRow.domain_id == req.id))
                if r is not None:
                    r.status = req.status.value
                continue
            self._s.add(self._request_row(inv_id, req))

        existing_res = self._existing_domain_ids(ExperimentResultRow, inv_id) if not initial else set()
        for res in [*state.completed_experiments, *state.failed_experiments]:
            if res.id in existing_res:
                continue
            self._s.add(ExperimentResultRow(
                investigation_id=inv_id, domain_id=res.id, request_domain_id=res.request_id,
                tool_name=res.tool_name, status=res.status.value,
                idempotency_key=res.id, metrics_json=dict(res.metrics), summary=res.summary,
                error_json=_json(res.error), provenance_json=_json(res.provenance),
            ))

        existing_obs = self._existing_domain_ids(ObservationRow, inv_id) if not initial else set()
        for obs in state.observations:
            if obs.id in existing_obs:
                continue
            self._s.add(self._observation_row(inv_id, obs))

        self._s.flush()  # ensure hypotheses/results exist before evidence links

        existing_ev = self._existing_domain_ids(EvidenceRow, inv_id) if not initial else set()
        hyp_by_domain = {r.domain_id: r for r in self._s.scalars(
            select(HypothesisRow).where(HypothesisRow.investigation_id == inv_id)).all()}
        for ev in state.evidence:
            if ev.id in existing_ev:
                continue
            ev_row = self._evidence_row(inv_id, ev)
            self._s.add(ev_row)
            self._s.flush()
            for hid in ev.hypothesis_ids:
                hrow = hyp_by_domain.get(hid)
                if hrow is not None:
                    self._s.add(EvidenceHypothesisLink(
                        evidence_id=ev_row.id, hypothesis_id=hrow.id, direction=ev.direction.value))

        existing_dec = self._existing_domain_ids(AgentDecisionRow, inv_id) if not initial else set()
        for i, dec in enumerate(state.decisions):
            if dec.id in existing_dec:
                continue
            self._s.add(AgentDecisionRow(
                investigation_id=inv_id, domain_id=dec.id, sequence=i, decision_type=dec.decision_type.value,
                rationale=dec.rationale, iteration=dec.iteration, targets_json=_json(dec.targets),
                chosen_option=dec.chosen_option, alternatives_json=list(dec.alternatives_considered),
                provenance_json=_json(dec.provenance),
            ))

        existing_crit = self._existing_domain_ids(CritiqueRow, inv_id) if not initial else set()
        for c in state.critiques:
            if c.id in existing_crit:
                continue
            self._s.add(CritiqueRow(
                investigation_id=inv_id, domain_id=c.id, critique_type=c.critique_type.value,
                severity=c.severity.value, target_kind=c.target.kind.value, target_id=c.target.id,
                message=c.message, suggested_action=c.suggested_action, resolved=c.resolved,
                provenance_json=_json(c.provenance),
            ))

        existing_q = self._existing_domain_ids(OpenQuestionRow, inv_id) if not initial else set()
        for q in state.open_questions:
            if q.id in existing_q:
                r = self._s.scalar(select(OpenQuestionRow).where(
                    OpenQuestionRow.investigation_id == inv_id, OpenQuestionRow.domain_id == q.id))
                if r is not None:
                    r.status, r.answer = q.status.value, q.answer
                continue
            self._s.add(OpenQuestionRow(
                investigation_id=inv_id, domain_id=q.id, question=q.question, status=q.status.value,
                priority=q.priority, related_hypothesis_ids_json=list(q.related_hypothesis_ids),
                answered_by_evidence_ids_json=list(q.answered_by_evidence_ids), answer=q.answer,
                provenance_json=_json(q.provenance),
            ))

        if state.current_conclusion is not None:
            existing_concl = self._existing_domain_ids(ConclusionRow, inv_id) if not initial else set()
            c = state.current_conclusion
            if c.id not in existing_concl:
                crow = self._conclusion_row(inv_id, c)
                self._s.add(crow)
                self._s.flush()
                row.current_conclusion_id = crow.id

    # -- row builders --------------------------------------------------------

    def _hypothesis_row(self, inv_id: UUID, h: Hypothesis) -> HypothesisRow:
        return HypothesisRow(
            investigation_id=inv_id, domain_id=h.id, statement=h.statement, rationale=h.rationale,
            status=h.status.value, confidence=h.confidence,
            prior_confidence=getattr(h, "prior_confidence", h.confidence),
            metric_refs_json=list(h.metric_refs), entity_refs_json=list(h.entity_refs),
            provenance_json=_json(h.provenance),
        )

    def _request_row(self, inv_id: UUID, req: ExperimentRequest) -> ExperimentRequestRow:
        return ExperimentRequestRow(
            investigation_id=inv_id, domain_id=req.id, definition_id=req.definition_id, tool_name=req.tool_name,
            parameters_json=dict(req.parameters), purpose=req.purpose,
            target_hypothesis_ids_json=list(req.target_hypothesis_ids), cost_estimate_json=_json(req.cost_estimate),
            expected_information_gain=req.expected_information_gain, preconditions_json=_json(req.preconditions),
            status=req.status.value, provenance_json=_json(req.provenance),
        )

    def _observation_row(self, inv_id: UUID, obs: Observation, *, experiment_result_id: UUID | None = None) -> ObservationRow:
        return ObservationRow(
            investigation_id=inv_id, domain_id=obs.id, experiment_result_id=experiment_result_id,
            statement=obs.statement, observation_type=obs.observation_type.value, magnitude=obs.magnitude,
            entity_ref=obs.entity_ref, metric_ref=obs.metric_ref, data_reference_json=_json(obs.data_reference),
            provenance_json=_json(obs.provenance),
        )

    def _evidence_row(self, inv_id: UUID, ev: Evidence) -> EvidenceRow:
        return EvidenceRow(
            investigation_id=inv_id, domain_id=ev.id, evidence_type=ev.evidence_type.value, claim=ev.claim,
            direction=ev.direction.value, strength=ev.strength, reliability=ev.reliability, coverage=ev.coverage,
            source_reference_json=_json(ev.source_reference), payload_reference_json=_json(ev.payload_reference),
            statistics_json=_json(ev.statistics), provenance_json=_json(ev.provenance),
        )

    def _conclusion_row(self, inv_id: UUID, c: Conclusion) -> ConclusionRow:
        return ConclusionRow(
            investigation_id=inv_id, domain_id=c.id, statement=c.statement, disposition=c.disposition.value,
            confidence=c.confidence, supporting_hypothesis_ids_json=list(c.supporting_hypothesis_ids),
            key_evidence_ids_json=list(c.key_evidence_ids), caveats_json=list(c.caveats),
            open_question_ids_json=list(c.open_question_ids), provenance_json=_json(c.provenance),
        )

    def _persist_repro(self, repro: ReproducibilityManifest | None, *, investigation_id: UUID | None) -> ReproducibilityManifestRow | None:
        if repro is None:
            return None
        r = ReproducibilityManifestRow(
            investigation_id=investigation_id, domain_id=repro.id, code_version=repro.code_version,
            tool_versions_json=dict(repro.tool_versions), prompt_versions_json=dict(repro.prompt_versions),
            model_config_json=_json(repro.model_config_snapshot), random_seed=repro.random_seed,
            dataset_reference_ids_json=list(repro.dataset_reference_ids), parameters_hash=repro.parameters_hash,
            environment_json=_json(repro.environment),
        )
        self._s.add(r)
        self._s.flush()
        return r

    def _next_sequence(self, model, investigation_id: UUID) -> int:
        current = self._s.scalar(
            select(func.max(model.sequence)).where(model.investigation_id == investigation_id)
        )
        return int(current) + 1 if current is not None else 0

    def _append_event(
        self, row: Investigation, event_type: StateEventType, *,
        entity_kind: str | None = None, entity_id: str | None = None, payload: dict | None = None,
    ) -> InvestigationStateEvent:
        seq = self._next_sequence(InvestigationStateEvent, row.id)
        event = InvestigationStateEvent(
            investigation_id=row.id, sequence=seq, event_type=event_type.value,
            entity_kind=entity_kind, entity_id=entity_id, state_version=row.state_version, payload_json=payload,
        )
        self._s.add(event)
        return event

    def _save_checkpoint(self, row: Investigation, investigation: DomainInvestigation, *, label: str | None) -> OrchestrationCheckpoint:
        seq = self._next_sequence(OrchestrationCheckpoint, row.id)
        cp = OrchestrationCheckpoint(
            investigation_id=row.id, sequence=seq, label=label, status=investigation.status.value,
            state_version=row.state_version, iteration=investigation.state.budget.iterations_used,
            state_json=investigation.model_dump(mode="json"),
        )
        self._s.add(cp)
        return cp
