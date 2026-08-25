"""
Hypotheses — the falsifiable claims an investigation tests.

A hypothesis is persisted structured state whose status is advanced by evidence
through validated transitions (:data:`ALLOWED_HYPOTHESIS_TRANSITIONS`).
Confidence is an explicit bounded field so "supported"/"weakened"/"rejected"
are inspectable, not implied by prose.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ALLOWED_HYPOTHESIS_TRANSITIONS, HypothesisStatus
from .provenance import Provenance


class IllegalHypothesisTransition(ValueError):
    """Raised when a hypothesis status change is not permitted."""


class Hypothesis(DomainModel):
    """One testable claim within an investigation."""

    id: str = Field(default_factory=lambda: new_id("hyp"))
    statement: str = Field(..., min_length=1, description="Falsifiable claim in plain language.")
    rationale: str = Field(default="", description="Why this is worth testing.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Current belief (0..1).")
    status: HypothesisStatus = Field(default=HypothesisStatus.proposed)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(
        default_factory=list,
        description="Manifest column names this hypothesis concerns.",
    )
    entity_refs: list[str] = Field(
        default_factory=list,
        description="Entities (e.g. tickers) this hypothesis concerns; empty means dataset-wide.",
    )
    parent_hypothesis_id: str | None = Field(
        default=None,
        description="Set when this hypothesis was spawned to refine/compete with another.",
    )
    mutually_exclusive_with: list[str] = Field(
        default_factory=list,
        description=(
            "Claims that cannot hold at the same time as this one. Set when the goal itself "
            "poses them as alternatives ('is it X, or is it Y?'), so the rivalry is known "
            "before any evidence arrives rather than depending on a model noticing it later."
        ),
    )
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    # -- mutation (explicit, validated) -------------------------------------

    def _touch(self) -> None:
        self.updated_at = utc_now()

    def can_transition_to(self, target: HypothesisStatus) -> bool:
        return target == self.status or target in ALLOWED_HYPOTHESIS_TRANSITIONS[self.status]

    def set_status(self, target: HypothesisStatus) -> None:
        """Advance status, enforcing the legal transition graph."""
        if not self.can_transition_to(target):
            raise IllegalHypothesisTransition(
                f"cannot transition hypothesis from {self.status.value} to {target.value}"
            )
        if target != self.status:
            self.status = target
            self._touch()

    def set_confidence(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        self.confidence = value
        self._touch()

    def link_supporting_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.supporting_evidence_ids:
            self.supporting_evidence_ids.append(evidence_id)
            self._touch()

    def link_contradicting_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.contradicting_evidence_ids:
            self.contradicting_evidence_ids.append(evidence_id)
            self._touch()

    def is_terminal(self) -> bool:
        return not ALLOWED_HYPOTHESIS_TRANSITIONS[self.status]
