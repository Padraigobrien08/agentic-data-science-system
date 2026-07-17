"""
Input adapter seam.

An input adapter turns a scope request into a :class:`DatasetManifest` the rest
of the platform can analyze without knowing the source. Adapters are the single
extension point for making the system input-agnostic; the deterministic
computation layer stays behind them.

Adapters must be able to describe a dataset **offline** (no network), so
fixture-based, deterministic execution is always possible. Live data fetching
stays in source-specific tooling and is not required to build a manifest.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from agentic.domain.manifest import DatasetManifest


class AdapterRequest(BaseModel):
    """Typed scope request handed to an adapter to build a manifest."""

    model_config = {"extra": "forbid"}

    entities: list[str] = Field(
        default_factory=list,
        description="Requested units of analysis (e.g. tickers); adapter may apply defaults when empty.",
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe adapter options (e.g. offline panel path, refresh flag).",
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
    """
    Base class for input adapters.

    Concrete adapters implement :meth:`describe` and :meth:`build_manifest`.
    ``build_manifest`` must not require network access — it returns a typed,
    truthful description of the dataset (columns, entities, provenance).
    """

    #: Stable adapter identifier used in registries and provenance.
    adapter_id: str = ""

    @abstractmethod
    def describe(self) -> AdapterInfo:
        """Return static metadata for discovery surfaces."""
        raise NotImplementedError

    @abstractmethod
    def build_manifest(self, request: AdapterRequest) -> DatasetManifest:
        """Produce a dataset manifest for the requested scope (offline-safe)."""
        raise NotImplementedError
