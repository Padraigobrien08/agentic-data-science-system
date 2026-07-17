"""
Backend-owned enums for investigation persistence.

Domain lifecycle values (investigation/hypothesis/experiment status, etc.) are
stored as their string ``.value`` in ``String`` columns and validated at the
domain boundary — mirroring how ``evaluation_case_results`` stores status. Only
persistence-owned classifications live here as SQL enums.
"""

from __future__ import annotations

import enum


class InvestigationOrigin(str, enum.Enum):
    """How an investigation row came to exist."""

    native = "native"
    """Created by the generalized investigation engine (source of truth)."""

    legacy_import = "legacy_import"
    """A representation of an existing EDGAR ``analysis_run`` (run stays source of truth)."""

    imported = "imported"
    """Imported from an external serialized investigation."""


class StateEventType(str, enum.Enum):
    """Append-only state-change event categories."""

    created = "created"
    status_changed = "status_changed"
    dataset_added = "dataset_added"
    hypothesis_added = "hypothesis_added"
    hypothesis_updated = "hypothesis_updated"
    experiment_requested = "experiment_requested"
    experiment_recorded = "experiment_recorded"
    evidence_added = "evidence_added"
    observation_added = "observation_added"
    decision_recorded = "decision_recorded"
    critique_added = "critique_added"
    question_added = "question_added"
    question_resolved = "question_resolved"
    conclusion_set = "conclusion_set"
    terminated = "terminated"
    checkpoint_saved = "checkpoint_saved"
    imported = "imported"
