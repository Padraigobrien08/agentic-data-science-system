"""
Provenance and reproducibility — first-class across the domain.

Every agent-produced entity carries :class:`Provenance` so a decision can be
traced to the agent/model/rule/tool that made it. :class:`ReproducibilityManifest`
captures the frozen context (code, prompts, model config, seeds, environment)
needed to reproduce an experiment or an entire run from persisted state.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ProvenanceSource


class Provenance(DomainModel):
    """Who/what produced an entity, with enough audit detail to trace it."""

    source: ProvenanceSource
    agent_id: str | None = Field(default=None, description="Logical agent that produced this, e.g. 'planner'.")
    model_call_id: str | None = Field(default=None, description="Recorded model-call row id (LLM output).")
    prompt_id: str | None = Field(default=None, description="Prompt registry id, when LLM-produced.")
    prompt_version: str | None = Field(default=None, description="Prompt/template version, when LLM-produced.")
    tool_name: str | None = Field(default=None, description="Deterministic tool that produced this, if any.")
    tool_version: str | None = Field(default=None, description="Version of that tool.")
    rule_ids: list[str] = Field(default_factory=list, description="Deterministic rule ids that fired.")
    created_by: str | None = Field(default=None, description="Human/user id when human-sourced.")
    note: str | None = Field(default=None, max_length=512)
    recorded_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    @classmethod
    def system(cls, note: str | None = None) -> "Provenance":
        """Convenience constructor for system/bootstrap-produced entities."""
        return cls(source=ProvenanceSource.system, note=note)


class ModelConfigSnapshot(DomainModel):
    """Frozen model configuration for reproducibility."""

    provider: str
    model_name: str
    temperature: float | None = Field(default=None, ge=0.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1)


class EnvironmentInfo(DomainModel):
    """Runtime environment captured for reproducibility."""

    python_version: str | None = None
    platform: str | None = None
    package_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Name -> version for dependencies that affect determinism.",
    )


class ReproducibilityManifest(DomainModel):
    """
    Everything needed to reproduce an experiment or run from persisted state.

    Attached to experiment requests/results and (optionally) to an investigation
    so a completed run can be re-executed deterministically.
    """

    id: str = Field(default_factory=lambda: new_id("repro"))
    code_version: str | None = Field(default=None, description="Git commit / build id of the computation layer.")
    tool_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic tool name -> version.",
    )
    prompt_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Prompt id -> version used in the run.",
    )
    model_config_snapshot: ModelConfigSnapshot | None = Field(default=None)
    random_seed: int | None = Field(default=None, description="Seed pinned for deterministic execution.")
    dataset_reference_ids: list[str] = Field(
        default_factory=list,
        description="Datasets the run/experiment consumed.",
    )
    parameters_hash: str | None = Field(
        default=None,
        description="Stable hash of typed parameters for exact-match reproduction.",
    )
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo)
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
