"""
Wire shapes for replaying a persisted investigation and diffing the outcome.

Projected from ``agentic.agent.diff.InvestigationDiff`` rather than serialising it directly.
The domain model is free to change with the loop; the committed OpenAPI contract
(``docs/api/openapi.json``, enforced in CI) should not shift as a side effect of that — a
contract that moves whenever an internal model moves is not a contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agentic.agent.replay import ReplayResult


class ReplayConclusionView(BaseModel):
    statement: str = ""
    disposition: str | None = None
    confidence: float = 0.0
    key_evidence_count: int = 0


class ReplayHypothesisDelta(BaseModel):
    hypothesis_id: str
    baseline_status: str | None = None
    candidate_status: str | None = None
    baseline_confidence: float | None = None
    candidate_confidence: float | None = None
    status_changed: bool = False
    statement_changed: bool = False


class ReplayDiffView(BaseModel):
    """
    The comparison, conclusion-first.

    ``verdict`` is the answer to the question a replay is asked: ``identical``,
    ``same_conclusion`` (the analysis held, the route to it changed) or ``diverged`` (the
    answer itself changed). Reaching the same conclusion by a different path is a materially
    different result from reaching a different conclusion, so they are not collapsed.
    """

    verdict: str = Field(description="identical | same_conclusion | diverged")
    summary: str = Field(description="One line suitable for a log, a CLI, or a PR comment.")

    baseline_id: str
    candidate_id: str
    baseline_status: str
    candidate_status: str
    baseline_termination: str | None = None
    candidate_termination: str | None = None

    baseline_conclusion: ReplayConclusionView
    candidate_conclusion: ReplayConclusionView

    #: Ordered, so a reordering is visible rather than collapsing into a set difference.
    baseline_tools: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    tools_only_in_baseline: list[str] = Field(default_factory=list)
    tools_only_in_candidate: list[str] = Field(default_factory=list)
    experiment_order_changed: bool = False

    hypothesis_deltas: list[ReplayHypothesisDelta] = Field(default_factory=list)

    baseline_iterations: int = 0
    candidate_iterations: int = 0
    baseline_evidence_count: int = 0
    candidate_evidence_count: int = 0


class ReplayResponse(BaseModel):
    investigation_id: str
    analysis_run_id: str
    diff: ReplayDiffView
    same_dataset: bool = Field(
        description=(
            "False when the candidate ran against data other than the baseline's, in which "
            "case a divergence cannot be attributed to the policy change alone."
        ),
    )
    notes: list[str] = Field(default_factory=list)
    candidate_persisted: bool = Field(
        default=False,
        description=(
            "Always false. The candidate is deliberately not stored — sharing a store with "
            "the baseline would overwrite the very run being compared against."
        ),
    )


def build_replay_response(
    result: ReplayResult, *, investigation_id: str, analysis_run_id: str
) -> ReplayResponse:
    d = result.diff
    return ReplayResponse(
        investigation_id=investigation_id,
        analysis_run_id=analysis_run_id,
        same_dataset=result.same_dataset,
        notes=list(result.notes),
        diff=ReplayDiffView(
            verdict=d.verdict.value,
            summary=d.summary(),
            baseline_id=d.baseline_id,
            candidate_id=d.candidate_id,
            baseline_status=d.baseline_status,
            candidate_status=d.candidate_status,
            baseline_termination=d.baseline_termination,
            candidate_termination=d.candidate_termination,
            baseline_conclusion=ReplayConclusionView(**d.baseline_conclusion.model_dump()),
            candidate_conclusion=ReplayConclusionView(**d.candidate_conclusion.model_dump()),
            baseline_tools=list(d.baseline_tools),
            candidate_tools=list(d.candidate_tools),
            tools_only_in_baseline=list(d.tools_only_in_baseline),
            tools_only_in_candidate=list(d.tools_only_in_candidate),
            experiment_order_changed=d.experiment_order_changed,
            hypothesis_deltas=[
                ReplayHypothesisDelta(
                    hypothesis_id=h.hypothesis_id,
                    baseline_status=h.baseline_status,
                    candidate_status=h.candidate_status,
                    baseline_confidence=h.baseline_confidence,
                    candidate_confidence=h.candidate_confidence,
                    status_changed=h.status_changed,
                    statement_changed=h.statement_changed,
                )
                for h in d.hypothesis_deltas
            ],
            baseline_iterations=d.baseline_iterations,
            candidate_iterations=d.candidate_iterations,
            baseline_evidence_count=d.baseline_evidence_count,
            candidate_evidence_count=d.candidate_evidence_count,
        ),
    )
