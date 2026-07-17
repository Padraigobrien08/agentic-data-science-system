"""
Input adapters — the seam that makes the platform input-agnostic.

Each adapter turns a scope request into a :class:`~agentic.domain.manifest.DatasetManifest`.
The first-party EDGAR adapter keeps the existing deterministic pipeline working
as a demo, reference template, and regression fixture.
"""

from __future__ import annotations

from .base import AdapterInfo, AdapterRequest, InputAdapter
from .edgar import EdgarInputAdapter
from .registry import AdapterRegistry, build_default_registry, default_registry

__all__ = [
    "AdapterInfo",
    "AdapterRequest",
    "InputAdapter",
    "EdgarInputAdapter",
    "AdapterRegistry",
    "build_default_registry",
    "default_registry",
]
