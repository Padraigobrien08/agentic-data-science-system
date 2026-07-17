"""
Experiments — typed invocations of deterministic tools.

Every experiment has typed inputs and typed outputs. The LLM plans which
experiment to run; the deterministic layer computes it. Numerical results live
in :class:`ExperimentResult`, never in prompt text, so a run is reproducible
from persisted state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, JsonValue

from .enums import ExperimentStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# JSON-safe payloads for typed experiment inputs/outputs (no opaque blobs of prose).
JsonDict = dict[str, JsonValue]


class ExperimentResult(BaseModel):
    """Typed output of one experiment run."""

    model_config = {"extra": "forbid"}

    status: ExperimentStatus = Field(..., description="Terminal status of the run.")
    outputs: JsonDict = Field(
        default_factory=dict,
        description="Structured tool outputs (counts, flags, computed values).",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Named scalar results for quick comparison/termination checks.",
    )
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Role key -> artifact URI/path produced by the tool.",
    )
    summary: str | None = Field(default=None, max_length=1024, description="One-line human summary of the outcome.")
    error: str | None = Field(default=None, description="Failure detail when status is failed.")
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Experiment(BaseModel):
    """
    A planned (and possibly executed) deterministic tool invocation.

    ``tool_name`` names a registered deterministic tool; ``inputs`` are its
    typed, JSON-safe arguments. ``result`` is populated once the tool runs.
    """

    model_config = {"extra": "forbid"}

    experiment_id: str = Field(default_factory=lambda: str(uuid4()))
    hypothesis_id: str | None = Field(
        default=None,
        description="Hypothesis this experiment tests; None for exploratory experiments.",
    )
    tool_name: str = Field(..., min_length=1, description="Registered deterministic tool to invoke.")
    inputs: JsonDict = Field(
        default_factory=dict,
        description="Typed, JSON-safe arguments for the tool.",
    )
    expected_output: str | None = Field(
        default=None,
        max_length=512,
        description="What a decisive result would look like (planning transparency).",
    )
    status: ExperimentStatus = Field(default=ExperimentStatus.planned)
    result: ExperimentResult | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)

    def is_terminal(self) -> bool:
        return self.status in (
            ExperimentStatus.succeeded,
            ExperimentStatus.failed,
            ExperimentStatus.skipped,
        )
