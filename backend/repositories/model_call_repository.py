"""Persistence for :class:`~backend.models.model_call.ModelCall`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models.model_call import ModelCall


class ModelCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: ModelCall) -> ModelCall:
        self._session.add(row)
        return row

    def get(self, model_call_id: UUID) -> ModelCall | None:
        return self._session.get(ModelCall, model_call_id)

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
