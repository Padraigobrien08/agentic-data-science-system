"""
Conclusion — the current best answer, always linked to evidence.

A :class:`Conclusion` is the investigation's standing interpretation. It may be
revised as evidence accrues; a disposition of ``inconclusive`` /
``insufficient_evidence`` is a valid, honest outcome.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ConclusionDisposition
from .provenance import Provenance


class Conclusion(DomainModel):
    """The current, evidence-linked answer to the investigation's objective."""

    id: str = Field(default_factory=lambda: new_id("concl"))
    statement: str = Field(..., min_length=1)
    disposition: ConclusionDisposition
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_hypothesis_ids: list[str] = Field(default_factory=list)
    key_evidence_ids: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    open_question_ids: list[str] = Field(default_factory=list)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
