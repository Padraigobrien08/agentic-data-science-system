"""
Experiment execution context.

The transient bundle a tool receives: the dataset manifest and materialized data,
the raw parameters, an artifact sink, and provenance/reproducibility. It holds
live pandas objects, so it is a dataclass and is never serialized.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from agentic.domain.common import new_id
from agentic.domain.enums import ProvenanceSource
from agentic.domain.manifest import DatasetManifest
from agentic.domain.provenance import Provenance, ReproducibilityManifest

from .artifacts import ArtifactSink, InMemoryArtifactSink


@dataclass
class ExperimentContext:
    """Inputs handed to a tool's ``run``."""

    manifest: DatasetManifest
    raw_params: dict = field(default_factory=dict)
    frame: pd.DataFrame | None = None
    documents: list | None = None
    artifact_sink: ArtifactSink = field(default_factory=InMemoryArtifactSink)
    provenance: Provenance | None = None
    reproducibility: ReproducibilityManifest | None = None
    request_id: str = field(default_factory=lambda: new_id("expreq"))

    def tool_provenance(self, tool_name: str, tool_version: str) -> Provenance:
        """Provenance for a deterministic tool result (never LLM-sourced)."""
        if self.provenance is not None:
            return self.provenance
        return Provenance(
            source=ProvenanceSource.deterministic_tool,
            tool_name=tool_name,
            tool_version=tool_version,
        )
