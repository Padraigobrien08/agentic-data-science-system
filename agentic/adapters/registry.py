"""
Adapter registry.

A tiny, dependency-injectable registry so callers can select an input adapter
by id at runtime. The default registry is populated lazily with the first-party
EDGAR adapter, but callers may construct an empty :class:`AdapterRegistry` and
register their own adapters (e.g. in tests).
"""

from __future__ import annotations

from .base import InputAdapter


class AdapterRegistry:
    """Maps ``adapter_id`` -> :class:`InputAdapter` instance."""

    def __init__(self) -> None:
        self._adapters: dict[str, InputAdapter] = {}

    def register(self, adapter: InputAdapter, *, replace: bool = False) -> None:
        adapter_id = adapter.adapter_id
        if not adapter_id:
            raise ValueError("adapter.adapter_id must be a non-empty string")
        if adapter_id in self._adapters and not replace:
            raise ValueError(f"adapter '{adapter_id}' already registered")
        self._adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> InputAdapter:
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            known = ", ".join(sorted(self._adapters)) or "<none>"
            raise KeyError(f"unknown adapter '{adapter_id}' (registered: {known})") from exc

    def has(self, adapter_id: str) -> bool:
        return adapter_id in self._adapters

    def ids(self) -> list[str]:
        return sorted(self._adapters)


def build_default_registry() -> AdapterRegistry:
    """Registry seeded with first-party adapters (EDGAR + local tabular)."""
    from .edgar import EDGARAdapter
    from .tabular import LocalTabularAdapter

    registry = AdapterRegistry()
    registry.register(EDGARAdapter())
    registry.register(LocalTabularAdapter())
    return registry


_DEFAULT_REGISTRY: AdapterRegistry | None = None


def default_registry() -> AdapterRegistry:
    """Process-wide default registry (lazily constructed)."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY
