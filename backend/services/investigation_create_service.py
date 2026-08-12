"""
Create-and-run an agentic investigation over a user-provided dataset.

This is the entry point that turns the flag-gated agentic engine into something a
user can actually start: given a goal and a small tabular dataset (pasted CSV or
inline records), it creates an ``AnalysisRun`` that opts into the agentic engine
(``input_payload_json.engine == "agentic"``) with an ``in_memory`` dataset, runs
the adaptive loop synchronously, and returns the resulting investigation id so the
caller can open the read surface.

Deliberately input-agnostic: no EDGAR/domain assumptions — the general profilers
infer roles/semantic types from the data. Parsing is capped and validated so a
malformed or oversized paste fails with a clear message instead of a 500.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.models.analysis_run import AnalysisRun
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.services.agentic_investigation_execution_service import (
    ENGINE_AGENTIC,
    AgenticInvestigationExecutionService,
)
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.run_queue_service import RunQueueService

MAX_ROWS = 5000
MAX_COLS = 100


class AgenticEngineDisabledError(RuntimeError):
    """Raised when a create is attempted while the agentic engine flag is off."""


class InvalidDatasetError(ValueError):
    """Raised when the supplied dataset is empty, malformed, or too large."""


@dataclass
class InvestigationCreateResult:
    analysis_run_id: UUID
    status: str
    db_status: str
    investigation_id: UUID | None = None
    queued: bool = False


def _coerce(value: str | None):
    """CSV cells are strings; coerce numerics so the profiler sees real metrics."""
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def parse_csv_to_records(csv_text: str) -> list[dict]:
    """Parse pasted CSV into typed records, with row/column caps and validation."""
    text = (csv_text or "").strip()
    if not text:
        raise InvalidDatasetError("CSV is empty.")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise InvalidDatasetError("CSV has no rows.")
    header = [h.strip() for h in rows[0]]
    if not header or any(h == "" for h in header):
        raise InvalidDatasetError("CSV header row must have a non-empty name for every column.")
    if len(set(header)) != len(header):
        raise InvalidDatasetError("CSV header has duplicate column names.")
    if len(header) > MAX_COLS:
        raise InvalidDatasetError(f"Too many columns ({len(header)} > {MAX_COLS}).")
    data_rows = rows[1:]
    if not data_rows:
        raise InvalidDatasetError("CSV has a header but no data rows.")
    if len(data_rows) > MAX_ROWS:
        raise InvalidDatasetError(f"Too many rows ({len(data_rows)} > {MAX_ROWS}).")
    records: list[dict] = []
    for r in data_rows:
        record = {header[i]: _coerce(r[i]) if i < len(r) else None for i in range(len(header))}
        records.append(record)
    return records


class InvestigationCreateService:
    """Creates an agentic run over a user dataset and executes it synchronously."""

    def __init__(self, session: Session, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    def create_and_run(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        goal: str,
        dataset_format: str,
        csv_text: str | None,
        records: list[dict] | None,
        name: str,
        time_field: str | None,
        entity_id_fields: list[str],
        source: str = "tabular",
        entities: list[str] | None = None,
        refresh: bool = False,
    ) -> InvestigationCreateResult:
        """Create and execute synchronously (best for small pasted datasets)."""
        run = self._prepare_run(
            project_id=project_id, user_id=user_id, goal=goal, dataset_format=dataset_format,
            csv_text=csv_text, records=records, name=name, time_field=time_field,
            entity_id_fields=entity_id_fields, source=source, entities=entities or [],
            refresh=refresh,
        )
        result = AgenticInvestigationExecutionService(self._session).execute_analysis_run(run.id)

        inv_row = SqlAlchemyInvestigationRepository(self._session).get_by_domain_id(str(run.id))
        if inv_row is None:  # pragma: no cover - execute always creates one
            raise RuntimeError("investigation was not persisted for the run")

        return InvestigationCreateResult(
            analysis_run_id=run.id,
            status=result.investigation_status.value,
            db_status=result.db_status.value,
            investigation_id=inv_row.id,
            queued=False,
        )

    def create_and_enqueue(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        goal: str,
        dataset_format: str,
        csv_text: str | None,
        records: list[dict] | None,
        name: str,
        time_field: str | None,
        entity_id_fields: list[str],
        source: str = "tabular",
        entities: list[str] | None = None,
        refresh: bool = False,
        trace_carrier: dict[str, str] | None = None,
    ) -> InvestigationCreateResult:
        """Create and enqueue for background execution by the worker (robust for large datasets)."""
        run = self._prepare_run(
            project_id=project_id, user_id=user_id, goal=goal, dataset_format=dataset_format,
            csv_text=csv_text, records=records, name=name, time_field=time_field,
            entity_id_fields=entity_id_fields, source=source, entities=entities or [],
            refresh=refresh,
        )
        RunQueueService(self._session).enqueue_after_create(run.id, None, trace_carrier=trace_carrier)
        self._session.commit()
        return InvestigationCreateResult(
            analysis_run_id=run.id,
            status="queued",
            db_status="queued",
            investigation_id=None,
            queued=True,
        )

    def _prepare_run(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        goal: str,
        dataset_format: str,
        csv_text: str | None,
        records: list[dict] | None,
        name: str,
        time_field: str | None,
        entity_id_fields: list[str],
        source: str = "tabular",
        entities: list[str] | None = None,
        refresh: bool = False,
    ) -> AnalysisRun:
        """Validate the flag + dataset and create a ``pending`` agentic run (no execution)."""
        if not self._settings.agentic_engine_enabled:
            raise AgenticEngineDisabledError(
                "The agentic investigation engine is disabled. Set "
                "EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true on the api (and worker) to enable it."
            )
        goal = (goal or "").strip()
        if not goal:
            raise InvalidDatasetError("A goal is required.")

        payload = self._build_payload(
            goal=goal,
            source=source,
            dataset_format=dataset_format,
            csv_text=csv_text,
            records=records,
            name=name,
            time_field=time_field,
            entity_id_fields=entity_id_fields,
            entities=entities or [],
            refresh=refresh,
        )
        run = AnalysisRunService(self._session).create(
            project_id,
            initiated_by_user_id=user_id,
            orchestration_goal_text=goal,
            input_payload_json=payload,
        )
        self._session.flush()
        return run

    def _build_payload(
        self,
        *,
        goal: str,
        source: str,
        dataset_format: str,
        csv_text: str | None,
        records: list[dict] | None,
        name: str,
        time_field: str | None,
        entity_id_fields: list[str],
        entities: list[str],
        refresh: bool,
    ) -> dict:
        """
        The run payload for one investigation, per dataset source.

        EDGAR mirrors the shape the deterministic recording path already uses (``tickers`` at
        the top level *and* ``entities`` on the dataset): the execution service reads entities
        from either, and matching the proven shape keeps one payload format across both entry
        points rather than a second one only this route emits.
        """
        if (source or "tabular").strip().lower() == "edgar":
            tickers = [t.strip().upper() for t in entities if t and t.strip()]
            if not tickers:
                raise InvalidDatasetError("At least one ticker is required for an EDGAR investigation.")
            return {
                "engine": ENGINE_AGENTIC,
                "analysis_goal": goal,
                "tickers": tickers,
                "refresh": bool(refresh),
                "dataset": {"adapter": "edgar", "entities": tickers},
            }

        resolved = self._resolve_records(dataset_format, csv_text, records)
        return {
            "engine": ENGINE_AGENTIC,
            "analysis_goal": goal,
            "dataset": {
                "adapter": "in_memory",
                "name": (name or "dataset").strip() or "dataset",
                "records": resolved,
                "time_field": (time_field or None),
                "entity_id_fields": entity_id_fields or [],
            },
        }

    def _resolve_records(
        self, dataset_format: str, csv_text: str | None, records: list[dict] | None
    ) -> list[dict]:
        fmt = (dataset_format or "csv").strip().lower()
        if fmt == "records":
            if not records:
                raise InvalidDatasetError("No records supplied.")
            if len(records) > MAX_ROWS:
                raise InvalidDatasetError(f"Too many rows ({len(records)} > {MAX_ROWS}).")
            if not isinstance(records[0], dict) or not records[0]:
                raise InvalidDatasetError("Records must be non-empty objects.")
            return records
        if fmt == "csv":
            return parse_csv_to_records(csv_text or "")
        raise InvalidDatasetError(f"Unsupported dataset format: {fmt!r} (expected 'csv' or 'records').")
