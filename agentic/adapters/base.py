"""
Input adapter seam.

An input adapter turns a scope request into a :class:`DatasetManifest` the rest
of the platform can analyze without knowing the source. Adapters are the single
extension point for making the system input-agnostic; the deterministic
computation layer stays behind them.

Each adapter provides three things:

* :meth:`capabilities` — a static :class:`SourceCapabilityDescriptor`.
* :meth:`describe` — human-facing metadata for discovery.
* :meth:`materializer` — a :class:`DatasetMaterializer` for a request.

The base :meth:`build_manifest` runs the materializer through the shared
:class:`DatasetManifestBuilder`, so every adapter emits a manifest with the same
required contents. Materialization must be offline-safe for the fixture path so
deterministic, no-network execution is always possible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from agentic.domain.manifest import DatasetManifest

from .capabilities import SourceCapabilityDescriptor
from .manifest_builder import DatasetManifestBuilder
from .materialize import DatasetMaterializer


class AdapterRequest(BaseModel):
    """Typed scope request handed to an adapter to build a manifest."""

    model_config = {"extra": "forbid"}

    entities: list[str] = Field(
        default_factory=list,
        description="Requested units of analysis (e.g. tickers); adapter may apply defaults when empty.",
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe adapter options (e.g. file path, format, offline panel path).",
    )


class AdapterInfo(BaseModel):
    """Static description of an adapter for discovery/UI."""

    model_config = {"extra": "forbid"}

    adapter_id: str
    version: str = Field(default="1")
    title: str
    description: str
    default_dataset_kind: str


class InputAdapter(ABC):
    """Base class for input adapters."""

    #: Stable adapter identifier used in registries and provenance.
    adapter_id: str = ""
    #: Adapter contract version, recorded on every manifest it builds.
    adapter_version: str = "1"

    @abstractmethod
    def capabilities(self) -> SourceCapabilityDescriptor:
        """Static declaration of supported source types, modalities, and operations."""
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> AdapterInfo:
        """Human-facing metadata for discovery surfaces."""
        raise NotImplementedError

    @abstractmethod
    def materializer(self, request: AdapterRequest) -> DatasetMaterializer:
        """Return a materializer for the requested scope (offline-safe for fixtures)."""
        raise NotImplementedError

    def _manifest_builder(self) -> DatasetManifestBuilder:
        return DatasetManifestBuilder()

    def build_manifest(self, request: AdapterRequest) -> DatasetManifest:
        """Materialize and profile the request into a full dataset manifest."""
        materialized = self.materializer(request).materialize()
        return self._manifest_builder().build(
            materialized,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )
