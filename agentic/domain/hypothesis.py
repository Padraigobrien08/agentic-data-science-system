"""
Hypotheses — the questions an investigation tests.

A hypothesis is persisted structured state whose status is advanced by
evidence. Confidence is an explicit numeric field so "supported", "weakened",
and "rejected" transitions are inspectable rather than implied by prose.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import HypothesisStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Hypothesis(BaseModel):
    """One testable claim within an :class:`InvestigationState`."""

    model_config = {"extra": "forbid"}

    hypothesis_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str = Field(..., min_length=1, description="Falsifiable claim in plain language.")
    status: HypothesisStatus = Field(default=HypothesisStatus.proposed)
    rationale: str | None = Field(default=None, max_length=1024, description="Why this is worth testing.")
    metric_refs: list[str] = Field(
        default_factory=list,
        description="Manifest column names this hypothesis concerns.",
    )
    entity_refs: list[str] = Field(
        default_factory=list,
        description="Entities (e.g. tickers) this hypothesis concerns; empty means dataset-wide.",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence records attached to this hypothesis.",
    )
    prior_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Belief before evidence (0..1).",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Current belief after attached evidence (0..1).",
    )
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def touch(self) -> None:
        self.updated_at = _utc_now()
