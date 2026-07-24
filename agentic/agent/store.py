"""
Investigation store abstraction for loop persistence.

The loop checkpoints after every iteration through an :class:`InvestigationStore`.
:class:`InMemoryInvestigationStore` keeps checkpoints in memory (tests); a
SQLAlchemy-backed adapter lives in ``backend.services.investigation_store`` and
bridges to the persistence layer without the loop depending on the backend.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentic.domain import Investigation


@runtime_checkable
class InvestigationStore(Protocol):
    def create(self, investigation: Investigation) -> None: ...

    def save(self, investigation: Investigation) -> None: ...

    def load(self, investigation_id: str) -> Investigation: ...


class InMemoryInvestigationStore:
    """Deterministic in-memory checkpoint store (latest snapshot per id)."""

    def __init__(self) -> None:
        self._snapshots: dict[str, dict] = {}
        self.save_count = 0

    def create(self, investigation: Investigation) -> None:
        self.save(investigation)

    def save(self, investigation: Investigation) -> None:
        self._snapshots[investigation.id] = investigation.model_dump(mode="json")
        self.save_count += 1

    def load(self, investigation_id: str) -> Investigation:
        return Investigation.model_validate(self._snapshots[investigation_id])


class NullInvestigationStore:
    """No-op store for runs that do not need checkpointing."""

    def create(self, investigation: Investigation) -> None:  # noqa: D401
        return None

    def save(self, investigation: Investigation) -> None:
        return None

    def load(self, investigation_id: str) -> Investigation:  # pragma: no cover - not resumable
        raise KeyError(investigation_id)
