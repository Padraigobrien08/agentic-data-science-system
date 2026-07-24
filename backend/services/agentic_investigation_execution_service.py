"""
Execute the generalized agentic investigation loop against a persisted analysis run.

This is the additive, flag-gated counterpart to
:class:`~backend.services.edgar_pipeline_execution_service.EdgarPipelineExecutionService`.
When a run opts into the agentic engine (and the ``agentic_engine_enabled`` flag is on),
this service:

1. resolves a dataset (in-memory records, a local CSV/Parquet file, or the EDGAR panel)
   from the run's ``input_payload_json`` into a typed ``DatasetManifest`` + live frame,
2. runs :class:`~agentic.agent.loop.InvestigationLoop` over it, checkpointing every
   iteration into the durable investigation persistence layer via
   :class:`~backend.services.investigation_store.SqlAlchemyInvestigationStore`,
3. maps the terminal :class:`~agentic.domain.InvestigationStatus` onto the existing
   ``AnalysisRunStatus`` and writes a compact ``output_payload_json`` summary.

The deterministic EDGAR path is untouched and remains the default. The loop is
offline-safe: with no LLM configured it uses the deterministic fixture policy, so runs
still reach a typed termination without network or model access.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pandas as pd
import structlog
from sqlalchemy import select

from agentic.adapters.base import AdapterRequest
from agentic.adapters.edgar import EDGARAdapter
from agentic.adapters.manifest_builder import DatasetManifestBuilder
from agentic.adapters.materialize import DatasetMaterializer, InMemoryMaterializer
from agentic.adapters.tabular import LocalTabularAdapter
from agentic.agent.loop import InvestigationLoop
from agentic.domain import Investigation, InvestigationStatus
from agentic.domain.manifest import DatasetManifest
from agentic.experiments import InMemoryArtifactSink
from agentic.experiments.artifacts import ArtifactRecord
from agentic.experiments.descriptor import ArtifactType
from backend.agents.agentic_model_policy import build_agent_policy
from backend.config.settings import Settings, get_settings
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.models.investigation_entities import ExperimentResultRow
from backend.observability.context import bind_run_context
from backend.observability.metrics import (
    monotonic_s,
    observe_agentic_artifacts_ingested,
    observe_agentic_complete,
    observe_agentic_exception,
)
from backend.observability.tracing import bind_current_trace_for_logs, get_tracer
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.services.exceptions import RunCancelledDuringExecution
from backend.services.investigation_store import SqlAlchemyInvestigationStore

log = structlog.get_logger(__name__)

ENGINE_EDGAR = "edgar"
ENGINE_AGENTIC = "agentic"

_EXECUTABLE_STATUSES: frozenset[AnalysisRunStatus] = frozenset(
    {
        AnalysisRunStatus.pending,
        AnalysisRunStatus.error,
        AnalysisRunStatus.partial_success,
        AnalysisRunStatus.no_data,
        AnalysisRunStatus.cancelled,
    }
)

# Terminal investigation status -> analysis-run status. ``exhausted`` means the loop ran
# but stopped short of sufficient evidence: partial success, not an error.
_STATUS_MAP: dict[InvestigationStatus, AnalysisRunStatus] = {
    InvestigationStatus.converged: AnalysisRunStatus.success,
    InvestigationStatus.exhausted: AnalysisRunStatus.partial_success,
    InvestigationStatus.failed: AnalysisRunStatus.error,
}

# Emitted-artifact type -> (storage kind, filename suffix) for ingestion into the artifacts table.
_ARTIFACT_KIND: dict[ArtifactType, tuple[ArtifactKind, str]] = {
    ArtifactType.table: (ArtifactKind.tabular, ".csv"),
    ArtifactType.json: (ArtifactKind.json, ".json"),
    ArtifactType.chart_spec: (ArtifactKind.json, ".chart.json"),
    ArtifactType.summary: (ArtifactKind.json, ".json"),
}


def _payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def select_run_engine(row: AnalysisRun, settings: Settings | None = None) -> str:
    """Return the execution engine for a run.

    The agentic engine is chosen only when the ``agentic_engine_enabled`` flag is on AND
    the run explicitly opts in via ``input_payload_json['engine'] == 'agentic'``. In every
    other case (default) the deterministic EDGAR engine is used, so existing behavior is
    unchanged unless an operator both enables the flag and a run requests it.
    """
    s = settings if settings is not None else get_settings()
    if not s.agentic_engine_enabled:
        return ENGINE_EDGAR
    engine = str(_payload_dict(row.input_payload_json).get("engine") or "").strip().lower()
    return ENGINE_AGENTIC if engine == ENGINE_AGENTIC else ENGINE_EDGAR


@dataclass
class AgenticExecutionResult:
    """Compact outcome the API route maps into ``ExecuteRunResponse``."""

    analysis_run_id: UUID
    investigation_id: str
    investigation_status: InvestigationStatus
    db_status: AnalysisRunStatus
    message: str
    final_summary: str
    hypotheses_count: int
    evidence_count: int
    experiments_count: int


@dataclass
class _ResolvedDataset:
    manifest: DatasetManifest
    frame: pd.DataFrame | None
    adapter_id: str


class AgenticInvestigationExecutionService:
    """Run the adaptive investigation loop for a persisted analysis run."""

    def __init__(
        self,
        session,
        *,
        run_service: AnalysisRunService | None = None,
        policy_factory: Callable[[Settings], Any] | None = None,
        artifact_service: ArtifactService | None = None,
    ) -> None:
        self._session = session
        self._runs = run_service or AnalysisRunService(self._session)
        self._policy_factory = policy_factory or (lambda s: build_agent_policy(s))
        self._artifact_service = artifact_service

    def execute_analysis_run(
        self,
        analysis_run_id: UUID,
        *,
        analysis_goal: str | None = None,
        from_worker: bool = False,
        execution_checkpoint: Callable[[], None] | None = None,
        # Accepted for call-site compatibility with the EDGAR service; not used by the
        # agentic engine (dataset scope comes from input_payload_json).
        tickers: list[str] | None = None,
        refresh: bool | None = None,
    ) -> AgenticExecutionResult:
        """Mark the run running, run the loop, map terminal status, persist a summary.

        Raises:
            ValueError: unknown run or status not executable.
            RunCancelledDuringExecution: the run was cancelled during execution.
        """
        bind_run_context(
            analysis_run_id=analysis_run_id,
            component="agentic",
            from_worker=from_worker,
        )
        bind_current_trace_for_logs()
        t0 = monotonic_s()
        tracer = get_tracer("backend.agentic")
        with tracer.start_as_current_span(
            "agentic.execute",
            attributes={"analysis.run.id": str(analysis_run_id), "agentic.from_worker": from_worker},
        ):
            bind_current_trace_for_logs()
            row = self._runs.require(analysis_run_id)
            self._guard_status(row, from_worker=from_worker)

            goal_text = self._resolve_goal(row, analysis_goal)
            resolved = self._resolve_dataset(row)

            self._runs.transition_status(analysis_run_id, AnalysisRunStatus.running)
            self._session.flush()
            self._session.commit()
            self._raise_if_cancelled(analysis_run_id, "before the investigation started")
            if execution_checkpoint is not None:
                execution_checkpoint()

            settings = get_settings()
            store = SqlAlchemyInvestigationStore(
                self._session,
                project_id=row.project_id,
                user_id=row.initiated_by_user_id,
                analysis_run_id=analysis_run_id,
            )
            # Shared sink: every experiment emits into it, so the emitted bytes survive the
            # loop and can be ingested into the artifacts table + linked to their results.
            sink = InMemoryArtifactSink()
            loop = InvestigationLoop(policy=self._policy_factory(settings), artifact_sink=sink)

            try:
                investigation = loop.start(
                    goal_text,
                    manifest=resolved.manifest,
                    frame=resolved.frame,
                    adapter_id=resolved.adapter_id,
                    store=store,
                    seed=str(analysis_run_id),
                )
            except Exception as exc:  # noqa: BLE001 - boundary: fail the run, don't leak
                self._session.rollback()
                if self._is_cancelled(analysis_run_id):
                    raise RunCancelledDuringExecution(
                        "Run was cancelled while the investigation was executing"
                    ) from exc
                log.exception("agentic_failed", analysis_run_id=str(analysis_run_id), exc_type=type(exc).__name__)
                self._runs.set_error_summary(analysis_run_id, str(exc)[:2048])
                self._runs.transition_status(analysis_run_id, AnalysisRunStatus.error)
                self._session.commit()
                observe_agentic_exception(exc)
                raise

            if execution_checkpoint is not None:
                execution_checkpoint()
            self._raise_if_cancelled(analysis_run_id, "before the investigation results were persisted")

            self._ingest_artifacts(analysis_run_id, investigation, sink)
            return self._finalize(analysis_run_id, investigation, resolved, t0)

    # -- status guards -------------------------------------------------------

    def _guard_status(self, row: AnalysisRun, *, from_worker: bool) -> None:
        if from_worker:
            if row.status != AnalysisRunStatus.queued:
                raise ValueError(f"Worker execution requires status 'queued', got {row.status.value!r}")
            return
        if row.status == AnalysisRunStatus.running:
            raise ValueError("Run is already executing (stale running state)")
        if row.status == AnalysisRunStatus.queued:
            raise ValueError(
                "Run is queued for background execution; use the worker or create without enqueue"
            )
        if row.status not in _EXECUTABLE_STATUSES:
            raise ValueError(f"Run status {row.status.value!r} is not executable")

    def _is_cancelled(self, analysis_run_id: UUID) -> bool:
        row = self._runs.get(analysis_run_id)
        return row is not None and row.status == AnalysisRunStatus.cancelled

    def _raise_if_cancelled(self, analysis_run_id: UUID, when: str) -> None:
        if self._is_cancelled(analysis_run_id):
            self._session.rollback()
            raise RunCancelledDuringExecution(f"Run was cancelled {when}")

    # -- goal / dataset resolution -------------------------------------------

    def _resolve_goal(self, row: AnalysisRun, analysis_goal: str | None) -> str:
        payload = _payload_dict(row.input_payload_json)
        for candidate in (analysis_goal, payload.get("analysis_goal"), payload.get("goal"), row.orchestration_goal_text):
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return "Investigate the provided dataset for notable patterns."

    def _resolve_dataset(self, row: AnalysisRun) -> _ResolvedDataset:
        payload = _payload_dict(row.input_payload_json)
        dataset = payload.get("dataset") if isinstance(payload.get("dataset"), Mapping) else {}
        adapter_id, adapter_version, materializer = self._materializer_for(payload, dict(dataset))
        materialized = materializer.materialize()
        manifest = DatasetManifestBuilder().build(
            materialized, adapter_id=adapter_id, adapter_version=adapter_version
        )
        return _ResolvedDataset(manifest=manifest, frame=materialized.frame, adapter_id=adapter_id)

    def _materializer_for(
        self, payload: Mapping[str, Any], dataset: dict[str, Any]
    ) -> tuple[str, str, DatasetMaterializer]:
        adapter = str(dataset.get("adapter") or "").strip().lower()
        records = dataset.get("records")
        path = dataset.get("path")

        if adapter == "in_memory" or (not adapter and isinstance(records, list) and records):
            entity_fields = self._as_str_list(dataset.get("entity_id_fields"))
            return (
                "in_memory",
                "1",
                InMemoryMaterializer(
                    adapter_id="in_memory",
                    name=str(dataset.get("name") or "in_memory_dataset"),
                    records=list(records or []),
                    time_field=dataset.get("time_field") or None,
                    entity_id_fields=entity_fields,
                ),
            )

        if adapter == "local_tabular" or (not adapter and path):
            params: dict[str, str] = {"path": str(path)}
            if dataset.get("time_field"):
                params["time_field"] = str(dataset["time_field"])
            if dataset.get("entity_id_fields"):
                params["entity_id_fields"] = ",".join(self._as_str_list(dataset.get("entity_id_fields")))
            tabular = LocalTabularAdapter()
            return (tabular.adapter_id, tabular.adapter_version, tabular.materializer(AdapterRequest(parameters=params)))

        # Default / explicit EDGAR: entities from dataset or the run's tickers.
        entities = self._as_str_list(dataset.get("entities")) or self._as_str_list(payload.get("tickers"))
        params = {}
        if dataset.get("panel_csv"):
            params["panel_csv"] = str(dataset["panel_csv"])
        edgar = EDGARAdapter()
        request = AdapterRequest(entities=entities, parameters=params)
        return (edgar.adapter_id, edgar.adapter_version, edgar.materializer(request))

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, (list, tuple)):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    # -- artifact ingestion --------------------------------------------------

    def _ingest_artifacts(
        self, analysis_run_id: UUID, investigation: Investigation, sink: InMemoryArtifactSink
    ) -> None:
        """Ingest each experiment-emitted artifact into the artifacts table and link it to its result.

        Bytes emitted during this run live in ``sink``; the domain results carry the artifact ids
        that reference them. Idempotent: a persisted result row that already has artifact links is
        skipped, so retries and resumed runs never duplicate linkage.
        """
        records: dict[str, ArtifactRecord] = {r.id: r for r in sink.records}
        if not records:
            return
        repo = SqlAlchemyInvestigationRepository(self._session)
        inv_row = repo.get_by_domain_id(investigation.id)
        if inv_row is None:
            return
        result_rows = {
            r.domain_id: r
            for r in self._session.scalars(
                select(ExperimentResultRow).where(ExperimentResultRow.investigation_id == inv_row.id)
            ).all()
        }
        artifacts = self._artifact_service or ArtifactService(self._session)
        state = investigation.state
        ingested = 0
        for result in [*state.completed_experiments, *state.failed_experiments]:
            res_row = result_rows.get(result.id)
            if res_row is None or res_row.artifact_links:
                continue  # result not persisted yet, or already ingested (idempotent)
            for art_id in result.artifact_ids:
                rec = records.get(art_id)
                data = sink.contents.get(art_id) if rec is not None else None
                if rec is None or data is None:
                    continue  # emitted in a prior call (resume) — bytes not in this sink
                kind, suffix = _ARTIFACT_KIND.get(rec.artifact_type, (ArtifactKind.other, ""))
                artifact_row = artifacts.save_bytes(
                    data,
                    role_key=f"agentic/experiment/{result.tool_name}/{rec.name}",
                    analysis_run_id=analysis_run_id,
                    kind=kind,
                    mime_type=rec.media_type,
                    filename_suffix=suffix,
                    meta_json={
                        "source": "agentic_experiment",
                        "artifact_name": rec.name,
                        "artifact_type": rec.artifact_type.value,
                        "fingerprint": rec.fingerprint,
                        "tool_name": result.tool_name,
                        "experiment_result_domain_id": result.id,
                    },
                )
                repo.link_experiment_result_artifact(res_row.id, artifact_row.id)
                ingested += 1
        if ingested:
            self._session.flush()
            observe_agentic_artifacts_ingested(ingested)
            log.info(
                "agentic_artifacts_ingested",
                analysis_run_id=str(analysis_run_id),
                investigation_id=investigation.id,
                artifacts=ingested,
            )

    # -- finalize ------------------------------------------------------------

    def _finalize(
        self, analysis_run_id: UUID, investigation: Investigation, resolved: _ResolvedDataset, t0: float
    ) -> AgenticExecutionResult:
        state = investigation.state
        db_status = _STATUS_MAP.get(investigation.status, AnalysisRunStatus.partial_success)
        conclusion = state.current_conclusion
        termination = state.termination

        final_summary = conclusion.statement if conclusion is not None else ""
        message = final_summary or (termination.rationale if termination is not None else "Investigation finished.")

        summary = {
            "engine": ENGINE_AGENTIC,
            "investigation_id": investigation.id,
            "status": investigation.status.value,
            "confidence": state.confidence,
            "message": message,
            "final_summary": final_summary,
            "termination": (
                {"reason": termination.reason.value, "rationale": termination.rationale}
                if termination is not None
                else None
            ),
            "conclusion": (
                {
                    "statement": conclusion.statement,
                    "disposition": conclusion.disposition.value,
                    "confidence": conclusion.confidence,
                    "caveats": list(conclusion.caveats),
                }
                if conclusion is not None
                else None
            ),
            "counts": {
                "hypotheses": len(state.hypotheses),
                "evidence": len(state.evidence),
                "experiments_completed": len(state.completed_experiments),
                "experiments_failed": len(state.failed_experiments),
                "observations": len(state.observations),
                "open_questions": len(state.open_questions),
            },
            "hypotheses": [
                {"statement": h.statement, "status": h.status.value, "confidence": h.confidence}
                for h in state.hypotheses
            ],
            "dataset": {
                "adapter_id": resolved.adapter_id,
                "name": resolved.manifest.name,
                "fingerprint": resolved.manifest.fingerprint,
                "row_count": resolved.manifest.row_count,
            },
        }

        self._runs.set_output_payload(analysis_run_id, summary)
        self._runs.set_error_summary(
            analysis_run_id,
            None if investigation.status is not InvestigationStatus.failed else (message or "Investigation failed"),
        )
        self._runs.transition_status(analysis_run_id, db_status)
        self._session.commit()

        duration_s = monotonic_s() - t0
        observe_agentic_complete(
            duration_s,
            db_status=db_status.value,
            investigation_status=investigation.status.value,
            experiments_completed=len(state.completed_experiments),
            experiments_failed=len(state.failed_experiments),
        )

        log.info(
            "agentic_completed",
            analysis_run_id=str(analysis_run_id),
            investigation_id=investigation.id,
            investigation_status=investigation.status.value,
            db_status=db_status.value,
            duration_s=round(duration_s, 4),
            hypotheses=len(state.hypotheses),
            evidence=len(state.evidence),
            experiments=len(state.completed_experiments),
        )

        return AgenticExecutionResult(
            analysis_run_id=analysis_run_id,
            investigation_id=investigation.id,
            investigation_status=investigation.status,
            db_status=db_status,
            message=message,
            final_summary=final_summary,
            hypotheses_count=len(state.hypotheses),
            evidence_count=len(state.evidence),
            experiments_count=len(state.completed_experiments),
        )
