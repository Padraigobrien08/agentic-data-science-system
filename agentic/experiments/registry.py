"""
Experiment registry.

A dependency-injectable registry mapping ``tool_name`` -> :class:`ExperimentTool`.
The default registry is populated with the general analytical tools plus the
first-party EDGAR domain tools; callers may build an empty registry and register
their own.
"""

from __future__ import annotations

from .base import ExperimentTool
from .descriptor import ExperimentToolDescriptor
from .errors import UnknownExperimentError


class ExperimentRegistry:
    """Maps ``tool_name`` -> registered :class:`ExperimentTool`."""

    def __init__(self) -> None:
        self._tools: dict[str, ExperimentTool] = {}

    def register(self, tool: ExperimentTool, *, replace: bool = False) -> None:
        name = tool.descriptor().name
        if not name:
            raise ValueError("tool descriptor name must be non-empty")
        if name in self._tools and not replace:
            raise ValueError(f"experiment '{name}' already registered")
        self._tools[name] = tool

    def get(self, name: str) -> ExperimentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._tools)) or "<none>"
            raise UnknownExperimentError(f"unknown experiment '{name}'", detail=f"registered: {known}") from exc

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def descriptors(self) -> list[ExperimentToolDescriptor]:
        return [self._tools[n].descriptor() for n in self.names()]


def build_default_registry() -> ExperimentRegistry:
    """Registry seeded with the general and EDGAR experiment tools."""
    from .tools.edgar_tools import edgar_tools
    from .tools.general_tools import general_tools

    registry = ExperimentRegistry()
    for tool in general_tools():
        registry.register(tool)
    for tool in edgar_tools():
        registry.register(tool)
    return registry


_DEFAULT_REGISTRY: ExperimentRegistry | None = None


def default_registry() -> ExperimentRegistry:
    """Process-wide default registry (lazily constructed)."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY
