"""
Experiment tool descriptor — the self-describing contract of a tool.

Every tool declares its name, version, purpose, supported modalities, required
capabilities, parameter/output schemas, cost estimate, determinism flag, artifact
types, and known limitations. The descriptor is serializable and is what the
registry and catalog surface.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from agentic.domain.common import DomainModel
from agentic.domain.enums import Modality
from agentic.domain.experiment import CostEstimate

from .capability import ExperimentCapability


class ArtifactType(str, Enum):
    """Kinds of deterministic artifact an experiment may emit."""

    table = "table"
    json = "json"
    chart_spec = "chart_spec"
    summary = "summary"


class OutputField(DomainModel):
    """One declared output field (observation/evidence/metric key)."""

    name: str
    kind: str = Field(description="observation | evidence | metric | artifact | statistic")
    description: str = ""


class ExperimentToolDescriptor(DomainModel):
    """Self-describing, serializable contract for one deterministic experiment tool."""

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    supported_input_modalities: list[Modality]
    required_capabilities: ExperimentCapability
    parameter_schema: dict = Field(
        default_factory=dict,
        description="JSON schema of the parameter model.",
    )
    output_schema: list[OutputField] = Field(default_factory=list)
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    deterministic: bool = Field(default=True)
    artifact_types: list[ArtifactType] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
