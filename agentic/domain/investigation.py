"""
Investigation state — the serializable aggregate root of one run.

``InvestigationState`` holds the goal, the bound dataset manifest, and the
evolving sets of hypotheses, experiments, and evidence. It is the single
structured object a run is reproducible from: no critical state lives only in
model context. Mutations are small explicit methods that keep ``updated_at``
and status honest.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import (
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    TerminationReason,
)
from .evidence import Evidence
from .experiment import Experiment
from .hypothesis import Hypothesis
from .manifest import DatasetManifest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvestigationGoal(BaseModel):
    """The user-facing objective that drives execution paths."""

    model_config = {"extra": "forbid"}

    text: str = Field(..., min_length=1, description="User goal, e.g. 'find unusual financial changes'.")
    adapter_id: str = Field(..., description="Input adapter selected for this goal, e.g. 'edgar'.")
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe scope parameters (e.g. entity list, refresh flag) for reproduction.",
    )


class TerminationDecision(BaseModel):
    """A recorded stop decision — sufficient or insufficient evidence are both valid."""

    model_config = {"extra": "forbid"}

    should_stop: bool
    reason: TerminationReason
    rationale: str = Field(..., min_length=1, description="Why the policy decided to stop or continue.")
    at_iteration: int = Field(..., ge=0)
    decided_at: datetime = Field(default_factory=_utc_now)


class InvestigationState(BaseModel):
    """Aggregate root: all persisted structured state for one investigation."""

    model_config = {"extra": "forbid"}

    investigation_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = Field(default="1")
    goal: InvestigationGoal
    status: InvestigationStatus = Field(default=InvestigationStatus.created)
    manifest: DatasetManifest | None = Field(default=None)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    experiments: list[Experiment] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    iteration: int = Field(default=0, ge=0)
    termination: TerminationDecision | None = Field(default=None)
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    # -- mutation helpers (explicit, keep updated_at honest) -----------------

    def _touch(self) -> None:
        self.updated_at = _utc_now()

    def bind_manifest(self, manifest: DatasetManifest) -> None:
        self.manifest = manifest
        self._touch()

    def set_status(self, status: InvestigationStatus) -> None:
        self.status = status
        self._touch()

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        self.hypotheses.append(hypothesis)
        self._touch()
        return hypothesis

    def add_experiment(self, experiment: Experiment) -> Experiment:
        self.experiments.append(experiment)
        self._touch()
        return experiment

    def add_evidence(self, evidence: Evidence) -> Evidence:
        """Attach evidence and link it to any referenced hypotheses."""
        self.evidence.append(evidence)
        for hid in evidence.hypothesis_ids:
            hyp = self.find_hypothesis(hid)
            if hyp is not None and evidence.evidence_id not in hyp.evidence_ids:
                hyp.evidence_ids.append(evidence.evidence_id)
                hyp.touch()
        self._touch()
        return evidence

    def advance_iteration(self) -> int:
        self.iteration += 1
        self._touch()
        return self.iteration

    def record_termination(self, decision: TerminationDecision) -> None:
        self.termination = decision
        self._touch()

    # -- lookups -------------------------------------------------------------

    def find_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        return next((h for h in self.hypotheses if h.hypothesis_id == hypothesis_id), None)

    def find_experiment(self, experiment_id: str) -> Experiment | None:
        return next((e for e in self.experiments if e.experiment_id == experiment_id), None)

    def evidence_for(self, hypothesis_id: str) -> list[Evidence]:
        return [e for e in self.evidence if hypothesis_id in e.hypothesis_ids]

    def open_hypotheses(self) -> list[Hypothesis]:
        """Hypotheses not yet resolved to a terminal status."""
        terminal = {
            HypothesisStatus.supported,
            HypothesisStatus.rejected,
            HypothesisStatus.inconclusive,
        }
        return [h for h in self.hypotheses if h.status not in terminal]

    def pending_experiments(self) -> list[Experiment]:
        """Experiments still awaiting execution."""
        return [e for e in self.experiments if e.status in (ExperimentStatus.planned, ExperimentStatus.running)]
