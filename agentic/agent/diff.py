"""
Structural comparison of two investigations.

Answers the question a replay exists to ask: *did this change alter the analysis?* —
where "change" is a different model, prompt, policy, budget, or tool registry.

The comparison is deliberately conclusion-first. A run that reaches the same answer by a
different route is a far weaker signal than one that reaches a different answer, so the
top-level :class:`DiffVerdict` separates those cases instead of reporting an undifferentiated
list of deltas.

Pure domain code: no infrastructure, no persistence, no model access.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from agentic.domain import Investigation
from agentic.domain.common import DomainModel


class DiffVerdict(str, Enum):
    """The headline answer, ordered from weakest to strongest signal of change."""

    identical = "identical"
    """Same conclusion, same termination, same experiments in the same order."""

    same_conclusion = "same_conclusion"
    """The answer and termination reason match, but the route to them differed."""

    diverged = "diverged"
    """The conclusion, its disposition, or the termination reason changed."""


class ConclusionSnapshot(DomainModel):
    """The parts of a conclusion that matter when comparing two runs."""

    statement: str = ""
    disposition: str | None = None
    confidence: float = 0.0
    key_evidence_count: int = 0

    @classmethod
    def of(cls, investigation: Investigation) -> "ConclusionSnapshot":
        conclusion = investigation.state.current_conclusion
        if conclusion is None:
            return cls()
        return cls(
            statement=conclusion.statement,
            disposition=conclusion.disposition.value,
            confidence=round(conclusion.confidence, 6),
            key_evidence_count=len(conclusion.key_evidence_ids),
        )


class HypothesisDelta(DomainModel):
    """How one hypothesis fared differently across the two runs."""

    hypothesis_id: str
    baseline_status: str | None = None
    candidate_status: str | None = None
    baseline_confidence: float | None = None
    candidate_confidence: float | None = None
    statement_changed: bool = False

    @property
    def status_changed(self) -> bool:
        return self.baseline_status != self.candidate_status


class InvestigationDiff(DomainModel):
    """Typed, serializable comparison of a baseline investigation and a replay of it."""

    baseline_id: str
    candidate_id: str
    verdict: DiffVerdict

    baseline_status: str
    candidate_status: str

    baseline_termination: str | None = None
    candidate_termination: str | None = None

    baseline_conclusion: ConclusionSnapshot
    candidate_conclusion: ConclusionSnapshot

    #: Ordered tool names, so a reordering is visible and not just a set difference.
    baseline_tools: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    tools_only_in_baseline: list[str] = Field(default_factory=list)
    tools_only_in_candidate: list[str] = Field(default_factory=list)
    experiment_order_changed: bool = False

    hypothesis_deltas: list[HypothesisDelta] = Field(default_factory=list)

    baseline_iterations: int = 0
    candidate_iterations: int = 0
    baseline_evidence_count: int = 0
    candidate_evidence_count: int = 0

    #: Entity ids that differ between the two runs.
    #:
    #: Compared because they were not, and the omission hid a real defect: goal, dataset,
    #: manifest, observation, artifact and reproducibility ids were minted with ``uuid4`` and
    #: differed on every run, while this diff looked only at tools, conclusions, terminations
    #: and hypothesis statuses. ``test_replay_under_identical_conditions_is_identical``
    #: therefore passed against a system whose "deterministic ids" were nothing of the kind.
    #: A verdict of ``identical`` now means identical.
    identity_drift: list[str] = Field(default_factory=list)

    @property
    def conclusion_changed(self) -> bool:
        return self.baseline_conclusion != self.candidate_conclusion

    @property
    def termination_changed(self) -> bool:
        return self.baseline_termination != self.candidate_termination

    @property
    def changed_hypotheses(self) -> list[HypothesisDelta]:
        return [d for d in self.hypothesis_deltas if d.status_changed]

    def summary(self) -> str:
        """One line suitable for a log, a CLI, or a PR comment."""
        if self.verdict is DiffVerdict.identical:
            return "identical: same conclusion, termination, and experiment sequence"
        if self.verdict is DiffVerdict.same_conclusion:
            parts = []
            if self.experiment_order_changed or self.tools_only_in_candidate or self.tools_only_in_baseline:
                parts.append("different experiments")
            if self.changed_hypotheses:
                parts.append(f"{len(self.changed_hypotheses)} hypothesis status change(s)")
            if self.identity_drift:
                parts.append(f"{', '.join(self.identity_drift)} ids differ")
            detail = ", ".join(parts) or "different internal path"
            return f"same conclusion via a different route ({detail})"
        reasons = []
        if self.baseline_conclusion.disposition != self.candidate_conclusion.disposition:
            reasons.append(
                f"disposition {self.baseline_conclusion.disposition} → {self.candidate_conclusion.disposition}"
            )
        elif self.baseline_conclusion.statement != self.candidate_conclusion.statement:
            reasons.append("conclusion statement changed")
        if self.termination_changed:
            reasons.append(f"termination {self.baseline_termination} → {self.candidate_termination}")
        return "diverged: " + ("; ".join(reasons) or "conclusion changed")


def _tools(investigation: Investigation) -> list[str]:
    results = investigation.state.completed_experiments + investigation.state.failed_experiments
    return [r.tool_name for r in results]


def _identity(investigation: Investigation) -> dict[str, list[str]]:
    """Every id a reproducible run is expected to reproduce, grouped by what it names."""
    state = investigation.state
    results = state.completed_experiments + state.failed_experiments
    return {
        "goal": [state.objective.id],
        "dataset": [d.id for d in state.datasets],
        "manifest": [d.manifest.manifest_id for d in state.datasets if d.manifest is not None],
        "hypothesis": [h.id for h in state.hypotheses],
        "evidence": [e.id for e in state.evidence],
        "experiment": [r.id for r in results],
        "observation": [o.id for o in state.observations],
        "artifact": [a for r in results for a in r.artifact_ids],
        "reproducibility": [r.reproducibility.id for r in results],
    }


def _identity_drift(baseline: Investigation, candidate: Investigation) -> list[str]:
    """The kinds of id that differ, named rather than enumerated — one line per kind."""
    base, cand = _identity(baseline), _identity(candidate)
    return [kind for kind in sorted(base) if base[kind] != cand.get(kind, [])]


def _termination(investigation: Investigation) -> str | None:
    decision = investigation.state.termination
    return decision.reason.value if decision is not None else None


def _hypothesis_deltas(baseline: Investigation, candidate: Investigation) -> list[HypothesisDelta]:
    """
    Match hypotheses by id.

    Ids are deterministic per seed (``{seed}-hyp-{index}``), so a replay of the same
    investigation lines its hypotheses up positionally even when the policy proposes
    different statements — which is exactly the case worth surfacing.
    """
    base = {h.id: h for h in baseline.state.hypotheses}
    cand = {h.id: h for h in candidate.state.hypotheses}
    deltas: list[HypothesisDelta] = []
    for hypothesis_id in sorted(base.keys() | cand.keys()):
        b = base.get(hypothesis_id)
        c = cand.get(hypothesis_id)
        deltas.append(HypothesisDelta(
            hypothesis_id=hypothesis_id,
            baseline_status=b.status.value if b else None,
            candidate_status=c.status.value if c else None,
            baseline_confidence=round(b.confidence, 6) if b else None,
            candidate_confidence=round(c.confidence, 6) if c else None,
            statement_changed=bool(b and c and b.statement != c.statement),
        ))
    return deltas


def diff_investigations(baseline: Investigation, candidate: Investigation) -> InvestigationDiff:
    """Compare two investigations and classify how far apart they are."""
    baseline_tools = _tools(baseline)
    candidate_tools = _tools(candidate)
    baseline_set = set(baseline_tools)
    candidate_set = set(candidate_tools)

    baseline_conclusion = ConclusionSnapshot.of(baseline)
    candidate_conclusion = ConclusionSnapshot.of(candidate)
    baseline_termination = _termination(baseline)
    candidate_termination = _termination(candidate)

    conclusion_changed = baseline_conclusion != candidate_conclusion
    termination_changed = baseline_termination != candidate_termination
    order_changed = baseline_tools != candidate_tools
    drift = _identity_drift(baseline, candidate)

    if conclusion_changed or termination_changed:
        verdict = DiffVerdict.diverged
    elif order_changed or baseline.status is not candidate.status or drift:
        # Identity drift is a route difference, not a different answer: the run reached the
        # same conclusion by the same tools, but did not reproduce. Reporting that as
        # `identical` is what let non-deterministic ids sit undetected behind a green test.
        verdict = DiffVerdict.same_conclusion
    else:
        verdict = DiffVerdict.identical

    deltas = _hypothesis_deltas(baseline, candidate)
    if verdict is DiffVerdict.identical and any(d.status_changed for d in deltas):
        # The answer and the experiment sequence match, but a claim landed differently —
        # still a route difference, not an identical run.
        verdict = DiffVerdict.same_conclusion

    return InvestigationDiff(
        baseline_id=baseline.id,
        candidate_id=candidate.id,
        verdict=verdict,
        baseline_status=baseline.status.value,
        candidate_status=candidate.status.value,
        baseline_termination=baseline_termination,
        candidate_termination=candidate_termination,
        baseline_conclusion=baseline_conclusion,
        candidate_conclusion=candidate_conclusion,
        baseline_tools=baseline_tools,
        candidate_tools=candidate_tools,
        tools_only_in_baseline=sorted(baseline_set - candidate_set),
        tools_only_in_candidate=sorted(candidate_set - baseline_set),
        experiment_order_changed=order_changed,
        hypothesis_deltas=deltas,
        identity_drift=drift,
        baseline_iterations=baseline.state.budget.iterations_used,
        candidate_iterations=candidate.state.budget.iterations_used,
        baseline_evidence_count=len(baseline.state.evidence),
        candidate_evidence_count=len(candidate.state.evidence),
    )
