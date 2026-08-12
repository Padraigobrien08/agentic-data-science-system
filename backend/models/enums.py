"""Stored enum values — string-backed for SQLite and PostgreSQL portability."""

from __future__ import annotations

import enum


class AnalysisRunStatus(str, enum.Enum):
    """Terminal and in-flight states for an orchestrated analysis run."""

    pending = "pending"
    queued = "queued"
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


class RunExecutionJobStatus(str, enum.Enum):
    """DB-backed queue row for background pipeline execution."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ModelCallStatus(str, enum.Enum):
    """LLM / model invocation lifecycle (reserved for future agent runtime)."""

    pending = "pending"
    running = "running"
    success = "success"
    error = "error"
    cancelled = "cancelled"


class UserAccessTier(str, enum.Enum):
    """
    What a user is allowed to spend model budget on.

    Ordered by cost, cheapest first. ``guest`` is an auto-provisioned throwaway account and is
    pinned to the deterministic engine regardless of the ``agentic_engine_enabled`` flag;
    ``standard`` is a self-registered account (deterministic engine, narrative phases only);
    ``adaptive`` is unlocked by the invite code and may run the agentic investigation loop.

    See ``docs/decisions/2026-08-11-showcase-direction.md`` (D3, S0).
    """

    guest = "guest"
    standard = "standard"
    adaptive = "adaptive"


class ChatMessageRole(str, enum.Enum):
    """Author of a durable chat message."""

    user = "user"
    assistant = "assistant"
    system = "system"


class ChatMessageStatus(str, enum.Enum):
    """Lifecycle of a chat message (assistant turns start ``pending``)."""

    pending = "pending"
    complete = "complete"
    error = "error"
