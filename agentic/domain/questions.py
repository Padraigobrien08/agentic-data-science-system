"""
Open questions — unresolved threads the agent is tracking.

An :class:`OpenQuestion` is explicit, persisted state: it keeps "what we still
don't know" out of model context and makes the termination policy's
"insufficient evidence" decision auditable.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import OpenQuestionStatus
from .provenance import Provenance


class OpenQuestion(DomainModel):
    """A tracked, answerable question raised during an investigation."""

    id: str = Field(default_factory=lambda: new_id("q"))
    question: str = Field(..., min_length=1)
    status: OpenQuestionStatus = Field(default=OpenQuestionStatus.open)
    priority: int = Field(default=0, description="Higher = more important to resolve.")
    related_hypothesis_ids: list[str] = Field(default_factory=list)
    answered_by_evidence_ids: list[str] = Field(default_factory=list)
    answer: str | None = Field(default=None, max_length=1024)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    def resolve(self, answer: str, *, evidence_ids: list[str] | None = None) -> None:
        self.status = OpenQuestionStatus.answered
        self.answer = answer
        if evidence_ids:
            for eid in evidence_ids:
                if eid not in self.answered_by_evidence_ids:
                    self.answered_by_evidence_ids.append(eid)
        self.updated_at = utc_now()

    def drop(self) -> None:
        self.status = OpenQuestionStatus.dropped
        self.updated_at = utc_now()
