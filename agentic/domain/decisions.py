"""
Agent decisions and critiques — agency as persisted structured state.

An :class:`AgentDecision` records *why* the run did what it did (which experiment
was chosen, which hypothesis was spawned) as a first-class, serializable entity —
not a log line. A :class:`Critique` records a challenge to the current reasoning
(insufficient evidence, a competing explanation), enabling adversarial review.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import CritiqueSeverity, CritiqueType, DecisionType, EntityKind
from .provenance import Provenance


class EntityRef(DomainModel):
    """A typed cross-entity reference (kind + id)."""

    kind: EntityKind
    id: str = Field(..., min_length=1)


class AgentDecision(DomainModel):
    """One recorded decision the agent made, with rationale and targets."""

    id: str = Field(default_factory=lambda: new_id("dec"))
    decision_type: DecisionType
    rationale: str = Field(..., min_length=1)
    iteration: int = Field(default=0, ge=0, description="Loop iteration the decision was made in.")
    targets: list[EntityRef] = Field(
        default_factory=list,
        description="Entities this decision created or acted upon.",
    )
    chosen_option: str | None = Field(default=None, description="The option selected, if a choice was made.")
    alternatives_considered: list[str] = Field(default_factory=list)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class Critique(DomainModel):
    """A challenge to a hypothesis, evidence, experiment, or conclusion."""

    id: str = Field(default_factory=lambda: new_id("crit"))
    critique_type: CritiqueType
    severity: CritiqueSeverity = Field(default=CritiqueSeverity.minor)
    target: EntityRef = Field(..., description="What is being critiqued.")
    #: The other side of a ``contradiction``. A conflict is between *two* claims, and storing
    #: only the one being critiqued meant nothing downstream could tell whether the pair had
    #: since been separated by evidence — which is why ``resolved`` was never once set to True.
    conflicts_with_id: str | None = Field(default=None)
    message: str = Field(..., min_length=1)
    suggested_action: str | None = Field(default=None, max_length=512)
    #: Whether the challenge has been answered. For a contradiction this is *derived* from the
    #: claims themselves — see :func:`agentic.agent.components.reconcile_contradictions` —
    #: rather than being a flag someone has to remember to set.
    resolved: bool = Field(default=False)
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
