"""Persistence for :class:`~backend.models.model_call.ModelCall`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models.enums import ModelCallStatus
from backend.models.model_call import ModelCall


def _contains_text(parts: list[str | None], needle: str) -> bool:
    lowered = needle.lower()
    return any(lowered in part.lower() for part in parts if isinstance(part, str) and part)


class ModelCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: ModelCall) -> ModelCall:
        self._session.add(row)
        return row

    def get(self, model_call_id: UUID) -> ModelCall | None:
        return self._session.get(ModelCall, model_call_id)

    def list_for_analysis_run(
        self,
        analysis_run_id: UUID,
        *,
        status: ModelCallStatus | None = None,
        prompt_id: str | None = None,
        q: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ModelCall]:
        rows = list(
            self._session.scalars(
                select(ModelCall)
                .where(ModelCall.analysis_run_id == analysis_run_id)
                .order_by(ModelCall.created_at.asc(), ModelCall.id.asc())
            ).all()
        )
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if prompt_id is not None:
            rows = [row for row in rows if row.prompt_id == prompt_id]
        if q is not None and q.strip():
            rows = [
                row
                for row in rows
                if _contains_text(
                    [
                        row.model_name,
                        row.provider,
                        row.prompt_id,
                        row.prompt_version,
                        row.error_detail,
                    ],
                    q,
                )
            ]
        if offset > 0:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def list_payload_redaction_candidates(
        self,
        *,
        created_before: datetime,
        limit: int,
    ) -> list[ModelCall]:
        payload_present = or_(
            ModelCall.request_payload_json.is_not(None),
            ModelCall.response_payload_json.is_not(None),
        )
        return list(
            self._session.scalars(
                select(ModelCall)
                .where(ModelCall.analysis_run_id.is_not(None))
                .where(ModelCall.created_at < created_before)
                .where(ModelCall.payloads_redacted_at.is_(None))
                .where(payload_present)
                .order_by(ModelCall.created_at.asc(), ModelCall.id.asc())
                .limit(limit)
            ).all()
        )

    def flush(self) -> None:
        self._session.flush()
