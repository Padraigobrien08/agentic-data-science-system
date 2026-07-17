"""
Evidence and its verifiable references.

Every material claim links to evidence. An :class:`Evidence` record ties a
hypothesis to a concrete, locatable result with an explicit direction and
bounded quality scores (strength / reliability / coverage), so the report
synthesizer can never assert something the run did not observe.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import EvidenceDirection, EvidenceType, PayloadKind, ReferenceKind
from .provenance import Provenance
from .statistics import StatisticalSummary


class SourceReference(DomainModel):
    """A precise, typed pointer to where evidence originates or can be verified."""

    kind: ReferenceKind
    ref: str = Field(..., min_length=1, description="Identifier/path/uri of the target.")
    locator: str | None = Field(
        default=None,
        description="Optional sub-locator (row filter, cell address, column) for exact-jump verification.",
    )


class PayloadReference(DomainModel):
    """A typed pointer to the concrete numeric payload behind evidence."""

    kind: PayloadKind
    ref: str = Field(..., min_length=1)
    locator: str | None = Field(default=None)
    media_type: str | None = Field(default=None, description="e.g. text/csv, application/json.")


class Evidence(DomainModel):
    """One observation, interpreted with respect to hypotheses."""

    id: str = Field(default_factory=lambda: new_id("evd"))
    evidence_type: EvidenceType
    source_reference: SourceReference
    experiment_result_id: str | None = Field(
        default=None,
        description="Experiment result that produced this evidence, when applicable.",
    )
    hypothesis_ids: list[str] = Field(
        default_factory=list,
        description="Hypotheses this evidence bears on (linkage target for the evidence updater).",
    )
    claim: str = Field(..., min_length=1, description="What this evidence asserts, in plain language.")
    direction: EvidenceDirection
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How strongly the observation bears on the claim (0..1).",
    )
    reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Trust in the measurement/source (0..1).",
    )
    coverage: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fraction of the relevant scope the evidence spans (0..1).",
    )
    payload_reference: PayloadReference | None = Field(
        default=None,
        description="Typed pointer to the underlying numeric payload.",
    )
    artifact_ids: list[str] = Field(default_factory=list)
    statistics: StatisticalSummary | None = Field(
        default=None,
        description="Statistical backing (effect size, uncertainty, sample size) when applicable.",
    )
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
