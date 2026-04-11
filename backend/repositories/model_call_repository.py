"""Persistence for :class:`~backend.models.model_call.ModelCall`."""

from __future__ import annotations

from uuid import UUID

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

    def flush(self) -> None:
        self._session.flush()
