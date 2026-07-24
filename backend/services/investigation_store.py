"""
SQLAlchemy-backed investigation store for the adaptive loop.

Bridges the loop's :class:`~agentic.agent.store.InvestigationStore` protocol to
:class:`~backend.repositories.investigation_repository.SqlAlchemyInvestigationRepository`,
so a live run checkpoints into the durable persistence layer. The loop itself
never imports the backend — this adapter satisfies its structural protocol.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from agentic.domain import Investigation
from backend.models.enums_investigation import StateEventType
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository


class SqlAlchemyInvestigationStore:
    """Persists loop checkpoints through the investigation repository."""

    def __init__(self, session: Session, *, project_id: UUID | None = None, user_id: UUID | None = None) -> None:
        self._session = session
        self._repo = SqlAlchemyInvestigationRepository(session)
        self._project_id = project_id
        self._user_id = user_id

    def create(self, investigation: Investigation) -> None:
        self._repo.create(investigation, project_id=self._project_id, initiated_by_user_id=self._user_id)
        self._session.commit()

    def save(self, investigation: Investigation) -> None:
        row = self._repo.get_by_domain_id(investigation.id)
        if row is None:
            self._repo.create(investigation, project_id=self._project_id, initiated_by_user_id=self._user_id)
        else:
            self._repo.save_state(row.id, investigation, event_type=StateEventType.checkpoint_saved)
        self._session.commit()

    def load(self, investigation_id: str) -> Investigation:
        row = self._repo.get_by_domain_id(investigation_id)
        if row is None:
            raise KeyError(investigation_id)
        return self._repo.load_domain(row.id)
