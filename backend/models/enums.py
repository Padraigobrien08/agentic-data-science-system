"""Stored enum values — string-backed for SQLite and PostgreSQL portability."""

from __future__ import annotations

import enum


class AnalysisRunStatus(str, enum.Enum):
    """Terminal and in-flight states for an orchestrated analysis run."""

    pending = "pending"
    running = "running"
    success = "success"
    partial_success = "partial_success"
    no_data = "no_data"
    error = "error"
    cancelled = "cancelled"


class RunStepStatus(str, enum.Enum):
    """Per-step execution state (planner step / executor step)."""

    pending = "pending"
    running = "running"
    success = "success"
    skipped = "skipped"
    no_data = "no_data"
    error = "error"


class ToolCallMcpStatus(str, enum.Enum):
    """MCP envelope status (``ToolResponseEnvelope.status``)."""

    success = "success"
    no_data = "no_data"
    error = "error"


class ArtifactKind(str, enum.Enum):
    """Broad artifact classification for storage and UI routing."""

    tabular = "tabular"
    document = "document"
    binary = "binary"
    json = "json"
    other = "other"


class EvaluationRunStatus(str, enum.Enum):
    """Benchmark suite run lifecycle (aligned with evaluation ``EvaluationStatus`` where possible)."""

    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"


class ModelCallStatus(str, enum.Enum):
    """LLM / model invocation lifecycle (reserved for future agent runtime)."""

    pending = "pending"
    running = "running"
    success = "success"
    error = "error"
    cancelled = "cancelled"
