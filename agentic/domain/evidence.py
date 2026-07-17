"""
Evidence — the link between claims and their support.

Every material claim must link to evidence. An :class:`Evidence` record ties a
hypothesis to a concrete, locatable result (an experiment output, an artifact
row, a computed value) with an explicit direction and strength, so the report
synthesizer can never assert something the run did not observe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import EvidenceDirection


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceRef(BaseModel):
    """A precise pointer to where evidence can be verified."""

    model_config = {"extra": "forbid"}

    kind: str = Field(..., description="Locator kind, e.g. 'artifact', 'experiment', 'manifest_column'.")
    ref: str = Field(..., description="Identifier/path/uri for the locator target.")
    locator: str | None = Field(
        default=None,
        description="Optional sub-locator, e.g. a row filter or cell address for exact-jump verification.",
    )


class Evidence(BaseModel):
    """One observation bearing on a hypothesis."""

    model_config = {"extra": "forbid"}

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    hypothesis_ids: list[str] = Field(
        default_factory=list,
        description="Hypotheses this evidence bears on.",
    )
    claim: str = Field(..., min_length=1, description="What this evidence asserts, in plain language.")
    direction: EvidenceDirection = Field(..., description="Whether it supports, refutes, or is neutral.")
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How strongly the observation bears on the claim (0..1).",
    )
    experiment_id: str | None = Field(
        default=None,
        description="Experiment that produced this evidence, when applicable.",
    )
    refs: list[EvidenceRef] = Field(
        default_factory=list,
        description="Verifiable locators backing the claim.",
    )
    created_at: datetime = Field(default_factory=_utc_now)
