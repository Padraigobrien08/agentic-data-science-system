"""
Input-agnostic investigation domain.

Pure, typed, JSON-serializable entities that model an agentic data-science
investigation independent of any single data source. These are domain entities,
deliberately separate from persistence models under ``backend/models`` — a later
phase maps them onto storage without coupling the core to SQLAlchemy.

See ``docs/architecture/investigation-domain-model.md`` for responsibilities,
state ownership, persistence boundaries, lifecycle, invariants, and extension
points. Nothing here is wired into production orchestration yet.
"""

from __future__ import annotations

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .conclusion import Conclusion
from .decisions import AgentDecision, Critique, EntityRef
from .enums import (
    ALLOWED_HYPOTHESIS_TRANSITIONS,
    ALLOWED_INVESTIGATION_TRANSITIONS,
    ColumnRole,
    ConclusionDisposition,
    CritiqueSeverity,
    CritiqueType,
    DataSourceKind,
    DatasetKind,
    DecisionType,
    EntityKind,
    EvidenceDirection,
    EvidenceType,
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    ObservationType,
    OpenQuestionStatus,
    PayloadKind,
    ProvenanceSource,
    ReferenceKind,
    TerminationReason,
)
from .evidence import Evidence, PayloadReference, SourceReference
from .experiment import (
    CostEstimate,
    ExperimentDefinition,
    ExperimentError,
    ExperimentParameters,
    ExperimentRequest,
    ExperimentResult,
    Precondition,
)
from .hypothesis import Hypothesis, IllegalHypothesisTransition
from .investigation import (
    BudgetState,
    IllegalInvestigationTransition,
    Investigation,
    InvestigationGoal,
    InvestigationState,
    TerminationDecision,
)
from .manifest import (
    ColumnSpec,
    DatasetManifest,
    DatasetProvenance,
    DatasetReference,
    DataSource,
)
from .observation import Observation
from .provenance import (
    EnvironmentInfo,
    ModelConfigSnapshot,
    Provenance,
    ReproducibilityManifest,
)
from .questions import OpenQuestion

__all__ = [
    # common
    "DOMAIN_SCHEMA_VERSION",
    "DomainModel",
    "new_id",
    "utc_now",
    # enums
    "ALLOWED_HYPOTHESIS_TRANSITIONS",
    "ALLOWED_INVESTIGATION_TRANSITIONS",
    "ColumnRole",
    "ConclusionDisposition",
    "CritiqueSeverity",
    "CritiqueType",
    "DataSourceKind",
    "DatasetKind",
    "DecisionType",
    "EntityKind",
    "EvidenceDirection",
    "EvidenceType",
    "ExperimentStatus",
    "HypothesisStatus",
    "InvestigationStatus",
    "ObservationType",
    "OpenQuestionStatus",
    "PayloadKind",
    "ProvenanceSource",
    "ReferenceKind",
    "TerminationReason",
    # provenance & reproducibility
    "Provenance",
    "ReproducibilityManifest",
    "ModelConfigSnapshot",
    "EnvironmentInfo",
    # datasets
    "DataSource",
    "DatasetReference",
    "DatasetManifest",
    "DatasetProvenance",
    "ColumnSpec",
    # hypotheses
    "Hypothesis",
    "IllegalHypothesisTransition",
    # evidence & observations
    "Evidence",
    "SourceReference",
    "PayloadReference",
    "Observation",
    # experiments
    "ExperimentDefinition",
    "ExperimentRequest",
    "ExperimentResult",
    "ExperimentError",
    "ExperimentParameters",
    "Precondition",
    "CostEstimate",
    # questions, decisions, critiques, conclusion
    "OpenQuestion",
    "AgentDecision",
    "Critique",
    "EntityRef",
    "Conclusion",
    # aggregate
    "Investigation",
    "InvestigationGoal",
    "InvestigationState",
    "BudgetState",
    "TerminationDecision",
    "IllegalInvestigationTransition",
]
