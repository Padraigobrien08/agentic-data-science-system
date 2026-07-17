"""
Observations — raw, pre-interpretation facts noticed during an experiment.

An :class:`Observation` records *what was seen* (a value, an outlier, a gap)
before it is interpreted for or against a hypothesis. Interpretation is the job
of :class:`~agentic.domain.evidence.Evidence`; keeping the two separate makes the
reasoning chain (observation -> evidence -> hypothesis status) inspectable.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ObservationType
from .evidence import SourceReference
from .provenance import Provenance


class Observation(DomainModel):
    """One raw noticing produced by a deterministic tool."""

    id: str = Field(default_factory=lambda: new_id("obs"))
    experiment_result_id: str | None = Field(default=None)
    statement: str = Field(..., min_length=1, description="Plain-language description of what was observed.")
    observation_type: ObservationType = Field(default=ObservationType.value)
    data_reference: SourceReference | None = Field(
        default=None,
        description="Where the observed value lives, for verification.",
    )
    magnitude: float | None = Field(
        default=None,
        description="Optional numeric magnitude (e.g. z-score, delta) — unbounded by design.",
    )
    entity_ref: str | None = Field(default=None, description="Entity the observation concerns, if scoped.")
    metric_ref: str | None = Field(default=None, description="Metric/column the observation concerns, if scoped.")
    provenance: Provenance
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
