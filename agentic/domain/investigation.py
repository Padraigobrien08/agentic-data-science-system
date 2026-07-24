"""
Investigation aggregate — the serializable working memory of one run.

``InvestigationState`` is the evolving structured state (hypotheses, experiments,
evidence, observations, questions, decisions, critiques, conclusion, budget,
termination). ``Investigation`` is the durable root that owns identity and
lifecycle status and wraps the state. A run is reproducible from these objects:
no critical state lives only in model context.

Mutations are small explicit methods that keep ``updated_at`` and links honest.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .conclusion import Conclusion
from .decisions import AgentDecision, Critique
from .enums import (
    ALLOWED_INVESTIGATION_TRANSITIONS,
    EvidenceDirection,
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    TerminationReason,
)
from .evidence import Evidence
from .experiment import ExperimentRequest, ExperimentResult
from .hypothesis import Hypothesis
from .manifest import DatasetReference
from .observation import Observation
from .provenance import Provenance, ReproducibilityManifest
from .questions import OpenQuestion


class IllegalInvestigationTransition(ValueError):
    """Raised when an investigation status change is not permitted."""


class InvestigationGoal(DomainModel):
    """The user-facing objective that drives execution paths."""

    id: str = Field(default_factory=lambda: new_id("goal"))
    objective: str = Field(..., min_length=1, description="What the investigation is trying to answer.")
    adapter_id: str | None = Field(default=None, description="Input adapter selected for the goal, if bound.")
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe scope parameters (e.g. entity list, refresh flag) for reproduction.",
    )
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class BudgetState(DomainModel):
    """Resource budget and consumption for termination decisions."""

    max_experiments: int | None = Field(default=None, ge=0)
    experiments_used: int = Field(default=0, ge=0)
    max_iterations: int | None = Field(default=None, ge=0)
    iterations_used: int = Field(default=0, ge=0)
    max_tokens: int | None = Field(default=None, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    max_wall_seconds: float | None = Field(default=None, ge=0.0)
    wall_seconds_used: float = Field(default=0.0, ge=0.0)
    max_cost_usd: float | None = Field(default=None, ge=0.0)
    cost_used_usd: float = Field(default=0.0, ge=0.0)

    def is_exhausted(self) -> bool:
        """True if any capped dimension has been reached."""
        checks = (
            (self.max_experiments, self.experiments_used),
            (self.max_iterations, self.iterations_used),
            (self.max_tokens, self.tokens_used),
            (self.max_wall_seconds, self.wall_seconds_used),
            (self.max_cost_usd, self.cost_used_usd),
        )
        return any(cap is not None and used >= cap for cap, used in checks)


class TerminationDecision(DomainModel):
    """A recorded stop/continue decision — sufficient or insufficient are both valid."""

    should_stop: bool
    reason: TerminationReason
    rationale: str = Field(..., min_length=1)
    at_iteration: int = Field(..., ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: Provenance | None = Field(default=None)
    decided_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class InvestigationState(DomainModel):
    """All evolving structured state for one investigation (serializable working memory)."""

    objective: InvestigationGoal
    datasets: list[DatasetReference] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    pending_experiments: list[ExperimentRequest] = Field(default_factory=list)
    completed_experiments: list[ExperimentResult] = Field(default_factory=list)
    failed_experiments: list[ExperimentResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    decisions: list[AgentDecision] = Field(default_factory=list)
    critiques: list[Critique] = Field(default_factory=list)
    current_conclusion: Conclusion | None = Field(default=None)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall investigation confidence (0..1).")
    budget: BudgetState = Field(default_factory=BudgetState)
    termination: TerminationDecision | None = Field(default=None)
    version: str = Field(default=DOMAIN_SCHEMA_VERSION, description="State schema version.")

    # -- mutation helpers ----------------------------------------------------

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        self.hypotheses.append(hypothesis)
        return hypothesis

    def add_observation(self, observation: Observation) -> Observation:
        self.observations.append(observation)
        return observation

    def add_experiment_request(self, request: ExperimentRequest) -> ExperimentRequest:
        self.pending_experiments.append(request)
        return request

    def record_experiment_result(self, result: ExperimentResult) -> ExperimentResult:
        """File a result under completed/failed and drop the matching pending request."""
        self.pending_experiments = [
            r for r in self.pending_experiments if r.id != result.request_id
        ]
        if result.status == ExperimentStatus.failed:
            self.failed_experiments.append(result)
        else:
            self.completed_experiments.append(result)
        self.budget.experiments_used += 1
        for obs in result.observations:
            self.observations.append(obs)
        return result

    def add_evidence(self, evidence: Evidence) -> Evidence:
        """Attach evidence and link it to referenced hypotheses by direction."""
        self.evidence.append(evidence)
        for hid in evidence.hypothesis_ids:
            hyp = self.find_hypothesis(hid)
            if hyp is None:
                continue
            if evidence.direction == EvidenceDirection.refutes:
                hyp.link_contradicting_evidence(evidence.id)
            elif evidence.direction == EvidenceDirection.supports:
                hyp.link_supporting_evidence(evidence.id)
        return evidence

    def add_open_question(self, question: OpenQuestion) -> OpenQuestion:
        self.open_questions.append(question)
        return question

    def record_decision(self, decision: AgentDecision) -> AgentDecision:
        self.decisions.append(decision)
        return decision

    def add_critique(self, critique: Critique) -> Critique:
        self.critiques.append(critique)
        return critique

    def set_conclusion(self, conclusion: Conclusion) -> None:
        self.current_conclusion = conclusion

    def record_termination(self, decision: TerminationDecision) -> None:
        self.termination = decision

    def advance_iteration(self) -> int:
        self.budget.iterations_used += 1
        return self.budget.iterations_used

    # -- lookups -------------------------------------------------------------

    def find_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        return next((h for h in self.hypotheses if h.id == hypothesis_id), None)

    def evidence_for(self, hypothesis_id: str) -> list[Evidence]:
        return [e for e in self.evidence if hypothesis_id in e.hypothesis_ids]

    def open_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if not h.is_terminal()]

    def unresolved_questions(self) -> list[OpenQuestion]:
        from .enums import OpenQuestionStatus

        return [q for q in self.open_questions if q.status == OpenQuestionStatus.open]


class Investigation(DomainModel):
    """Durable root: identity, lifecycle status, and the working state."""

    id: str = Field(default_factory=lambda: new_id("inv"))
    status: InvestigationStatus = Field(default=InvestigationStatus.created)
    state: InvestigationState
    reproducibility: ReproducibilityManifest | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)

    def _touch(self) -> None:
        self.updated_at = utc_now()

    def can_transition_to(self, target: InvestigationStatus) -> bool:
        return target == self.status or target in ALLOWED_INVESTIGATION_TRANSITIONS[self.status]

    def set_status(self, target: InvestigationStatus) -> None:
        """Advance lifecycle status, enforcing the legal transition graph."""
        if not self.can_transition_to(target):
            raise IllegalInvestigationTransition(
                f"cannot transition investigation from {self.status.value} to {target.value}"
            )
        if target != self.status:
            self.status = target
            self._touch()

    def is_terminal(self) -> bool:
        return not ALLOWED_INVESTIGATION_TRANSITIONS[self.status]

    @classmethod
    def start(cls, goal: InvestigationGoal) -> "Investigation":
        """Construct a fresh investigation in ``created`` status around a goal."""
        return cls(state=InvestigationState(objective=goal))
