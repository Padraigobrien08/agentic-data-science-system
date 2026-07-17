"""
Experiments — typed invocations of deterministic tools.

Three entities separate concerns cleanly:

* :class:`ExperimentDefinition` — a reusable template for a kind of experiment
  (which tool, its purpose, preconditions).
* :class:`ExperimentRequest` — a concrete, planned experiment with typed
  parameters, target hypotheses, a cost estimate, expected information gain, and
  reproducibility metadata.
* :class:`ExperimentResult` — the typed outcome (observations, produced evidence,
  metrics, artifacts, error).

The LLM plans which experiment to run; the deterministic layer computes it.
Numerical results live in the typed result, never in prompt text.

``parameters`` is the one deliberate JSON-map field: tool arguments are
tool-specific and mirror the existing orchestration ``tool_input`` contract.
Values are constrained to JSON-safe primitives.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, JsonValue

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ExperimentStatus
from .observation import Observation  # noqa: F401  (re-exported for convenience)
from .provenance import Provenance, ReproducibilityManifest

#: JSON-safe experiment parameter payload (tool-specific arguments).
ExperimentParameters = dict[str, JsonValue]


class Precondition(DomainModel):
    """A typed requirement that must hold before an experiment can run."""

    kind: str = Field(
        ...,
        description="Precondition kind, e.g. 'dataset_available', 'column_role_present', 'hypothesis_active'.",
    )
    description: str = Field(..., min_length=1)
    ref: str | None = Field(default=None, description="Target id/name the precondition concerns.")


class CostEstimate(DomainModel):
    """Estimated resource cost of running an experiment (all fields optional)."""

    compute_seconds: float | None = Field(default=None, ge=0.0)
    network_calls: int | None = Field(default=None, ge=0)
    token_estimate: int | None = Field(default=None, ge=0)
    monetary_cost_usd: float | None = Field(default=None, ge=0.0)


class ExperimentError(DomainModel):
    """Structured failure detail for an experiment result."""

    code: str
    message: str
    detail: str | None = Field(default=None)
    exc_type: str | None = Field(default=None)


class ExperimentDefinition(DomainModel):
    """Reusable template describing a kind of deterministic experiment."""

    id: str = Field(default_factory=lambda: new_id("expdef"))
    tool_name: str = Field(..., min_length=1, description="Registered deterministic tool this runs.")
    title: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1, description="What running this is expected to establish.")
    default_parameters: ExperimentParameters = Field(default_factory=dict)
    preconditions: list[Precondition] = Field(default_factory=list)
    produces_evidence_types: list[str] = Field(
        default_factory=list,
        description="EvidenceType values this experiment can yield.",
    )
    provenance: Provenance
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class ExperimentRequest(DomainModel):
    """A concrete, planned experiment ready to hand to the deterministic tool layer."""

    id: str = Field(default_factory=lambda: new_id("expreq"))
    definition_id: str | None = Field(default=None)
    tool_name: str = Field(..., min_length=1, description="Deterministic tool name.")
    parameters: ExperimentParameters = Field(default_factory=dict, description="Typed, JSON-safe tool arguments.")
    purpose: str = Field(..., min_length=1, description="Expected purpose of this run.")
    target_hypothesis_ids: list[str] = Field(default_factory=list)
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    expected_information_gain: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Planner's estimate of how decisive this experiment is (0..1).",
    )
    preconditions: list[Precondition] = Field(default_factory=list)
    reproducibility: ReproducibilityManifest = Field(default_factory=ReproducibilityManifest)
    status: ExperimentStatus = Field(default=ExperimentStatus.planned)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class ExperimentResult(DomainModel):
    """Typed outcome of one experiment run."""

    id: str = Field(default_factory=lambda: new_id("expres"))
    request_id: str = Field(..., description="ExperimentRequest this result answers.")
    tool_name: str = Field(..., min_length=1)
    status: ExperimentStatus
    observations: list[Observation] = Field(default_factory=list)
    produced_evidence_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Named scalar results for comparison/termination checks.",
    )
    summary: str | None = Field(default=None, max_length=1024)
    error: ExperimentError | None = Field(default=None)
    reproducibility: ReproducibilityManifest = Field(default_factory=ReproducibilityManifest)
    provenance: Provenance
    started_at: datetime | None = None
    finished_at: datetime | None = None
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    def succeeded(self) -> bool:
        return self.status == ExperimentStatus.succeeded
