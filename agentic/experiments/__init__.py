"""
Deterministic experiment system.

An experiment is a typed analytical operation that accepts declared dataset
capabilities and typed parameters, performs deterministic computation, returns
structured observations and evidence, and emits reproducible artifacts. No tool
relies on an LLM for numerical output.

See ``docs/experiments/experiment-contract.md`` and
``docs/experiments/tool-catalog.md``. Nothing here is wired into production
orchestration yet.
"""

from __future__ import annotations

from .artifacts import (
    ArtifactRecord,
    ArtifactSink,
    DirectoryArtifactSink,
    InMemoryArtifactSink,
)
from .base import BaseExperimentTool, ExperimentOutcome, ExperimentTool
from .capability import (
    ExperimentCapability,
    ExperimentValidationResult,
    ValidationIssue,
    check_capability,
)
from .context import ExperimentContext
from .descriptor import ArtifactType, ExperimentToolDescriptor, OutputField
from .errors import (
    CapabilityError,
    ExperimentError,
    ExperimentExecutionError,
    ExperimentValidationError,
    ParameterError,
    UnknownExperimentError,
)
from .record import ExperimentExecutionRecord
from .registry import ExperimentRegistry, build_default_registry, default_registry

__all__ = [
    # protocol / base
    "ExperimentTool",
    "BaseExperimentTool",
    "ExperimentOutcome",
    # registry
    "ExperimentRegistry",
    "build_default_registry",
    "default_registry",
    # capability / validation
    "ExperimentCapability",
    "ExperimentValidationResult",
    "ValidationIssue",
    "check_capability",
    # context / record / descriptor
    "ExperimentContext",
    "ExperimentExecutionRecord",
    "ExperimentToolDescriptor",
    "OutputField",
    "ArtifactType",
    # artifacts
    "ArtifactRecord",
    "ArtifactSink",
    "InMemoryArtifactSink",
    "DirectoryArtifactSink",
    # errors
    "ExperimentError",
    "ExperimentValidationError",
    "CapabilityError",
    "ParameterError",
    "ExperimentExecutionError",
    "UnknownExperimentError",
]
