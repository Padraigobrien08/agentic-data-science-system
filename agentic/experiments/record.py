"""
Experiment execution record — the serializable audit of one run.

Bundles the deterministic outputs (observations, evidence, metrics, artifacts,
statistics) with identity (input/output fingerprints), status, timing, and
reproducibility. Maps to the domain
:class:`~agentic.domain.experiment.ExperimentResult` via :meth:`to_domain_result`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from agentic.domain.common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from agentic.domain.enums import ExperimentStatus
from agentic.domain.evidence import Evidence
from agentic.domain.experiment import ExperimentError as ExperimentErrorInfo
from agentic.domain.experiment import ExperimentResult
from agentic.domain.observation import Observation
from agentic.domain.provenance import Provenance, ReproducibilityManifest
from agentic.domain.statistics import StatisticalSummary

from .artifacts import ArtifactRecord


class ExperimentExecutionRecord(DomainModel):
    """Serializable record of a single deterministic experiment execution."""

    id: str = Field(default_factory=lambda: new_id("exprec"))
    tool_name: str
    tool_version: str
    request_id: str
    status: ExperimentStatus

    params: dict = Field(default_factory=dict)
    dataset_fingerprint: str | None = Field(default=None)
    input_fingerprint: str | None = Field(default=None)
    output_fingerprint: str | None = Field(default=None)

    observations: list[Observation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    statistics: list[StatisticalSummary] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    diagnostics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    summary: str = Field(default="")

    error: ExperimentErrorInfo | None = Field(default=None)
    provenance: Provenance
    reproducibility: ReproducibilityManifest = Field(default_factory=ReproducibilityManifest)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = Field(default=None)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    def succeeded(self) -> bool:
        return self.status == ExperimentStatus.succeeded

    def to_domain_result(self) -> ExperimentResult:
        """Map to the domain ExperimentResult (ids-only linkage for evidence/artifacts)."""
        return ExperimentResult(
            request_id=self.request_id,
            tool_name=self.tool_name,
            status=self.status,
            observations=list(self.observations),
            produced_evidence_ids=[e.id for e in self.evidence],
            artifact_ids=[a.id for a in self.artifacts],
            metrics=dict(self.metrics),
            summary=self.summary or None,
            error=self.error.detail if self.error else None,
            reproducibility=self.reproducibility,
            provenance=self.provenance,
            started_at=self.started_at,
            finished_at=self.finished_at,
        )
