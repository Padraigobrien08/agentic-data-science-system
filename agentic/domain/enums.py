"""
Explicit enums for the input-agnostic investigation domain.

The generalized platform represents agent decisions as persisted structured
state rather than free-form status strings. Every lifecycle value below is an
explicit enum so orchestration decisions stay inspectable and serializable
(see the project's "definition of agency").
"""

from __future__ import annotations

from enum import Enum


class DatasetKind(str, Enum):
    """Shape of a dataset described by a :class:`DatasetManifest`."""

    tabular_panel = "tabular_panel"
    """Wide entity x period table (the EDGAR financial panel is this kind)."""

    timeseries = "timeseries"
    cross_section = "cross_section"
    event_log = "event_log"
    document_set = "document_set"
    other = "other"


class ColumnRole(str, Enum):
    """Semantic role of a column, independent of its storage dtype."""

    entity_id = "entity_id"
    """Unit of analysis identifier (e.g. ticker)."""

    time_index = "time_index"
    """Ordering/period axis (e.g. fiscal period)."""

    metric = "metric"
    """Numeric measurement an experiment may analyze."""

    dimension = "dimension"
    """Categorical descriptor used for grouping/labeling."""

    identifier = "identifier"
    """Secondary key or provenance id (e.g. CIK)."""

    derived = "derived"
    """Value computed from other columns by the deterministic layer."""


class InvestigationStatus(str, Enum):
    """Lifecycle of an :class:`InvestigationState` aggregate."""

    created = "created"
    planning = "planning"
    running = "running"
    awaiting_evidence = "awaiting_evidence"
    converged = "converged"
    exhausted = "exhausted"
    failed = "failed"


class HypothesisStatus(str, Enum):
    """
    Whether accumulated evidence supports a hypothesis.

    Agency requires that hypotheses can be supported, weakened, or rejected,
    so these are first-class persisted transitions rather than log lines.
    """

    proposed = "proposed"
    under_investigation = "under_investigation"
    supported = "supported"
    weakened = "weakened"
    rejected = "rejected"
    inconclusive = "inconclusive"


class ExperimentStatus(str, Enum):
    """Lifecycle of a single typed experiment."""

    planned = "planned"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class EvidenceDirection(str, Enum):
    """How a piece of evidence bears on a hypothesis."""

    supports = "supports"
    refutes = "refutes"
    neutral = "neutral"


class TerminationReason(str, Enum):
    """
    Why an investigation stopped.

    Both sufficient and insufficient evidence are valid terminal outcomes;
    failure and uncertainty are explicit, not implicit.
    """

    sufficient_evidence = "sufficient_evidence"
    insufficient_evidence = "insufficient_evidence"
    max_iterations = "max_iterations"
    no_progress = "no_progress"
    error = "error"
    user_stop = "user_stop"
