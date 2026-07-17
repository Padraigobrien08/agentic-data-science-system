"""
Input-agnostic investigation domain.

Pure, typed, JSON-serializable entities that model an agentic data-science
investigation independent of any single data source. These are domain entities,
deliberately separate from persistence models under ``backend/models`` — a
later phase maps them onto storage without coupling the core to SQLAlchemy.
"""

from __future__ import annotations

from .enums import (
    ColumnRole,
    DatasetKind,
    EvidenceDirection,
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    TerminationReason,
)
from .evidence import Evidence, EvidenceRef
from .experiment import Experiment, ExperimentResult, JsonDict
from .hypothesis import Hypothesis
from .investigation import (
    InvestigationGoal,
    InvestigationState,
    TerminationDecision,
)
from .manifest import ColumnSpec, DatasetManifest, DatasetProvenance

__all__ = [
    # enums
    "ColumnRole",
    "DatasetKind",
    "EvidenceDirection",
    "ExperimentStatus",
    "HypothesisStatus",
    "InvestigationStatus",
    "TerminationReason",
    # manifest
    "ColumnSpec",
    "DatasetManifest",
    "DatasetProvenance",
    # entities
    "Hypothesis",
    "Experiment",
    "ExperimentResult",
    "JsonDict",
    "Evidence",
    "EvidenceRef",
    # aggregate
    "InvestigationGoal",
    "InvestigationState",
    "TerminationDecision",
]
