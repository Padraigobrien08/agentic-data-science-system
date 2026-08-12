"""
Deterministic fixture policy for tests.

Rule-based, no LLM. Produces stable typed decisions so integration tests are
deterministic. Intent is keyword-derived from the goal, so execution paths differ
across goals; selection prefers falsification candidates then highest information
gain, so intermediate results steer the loop.
"""

from __future__ import annotations

from .direction import parse_direction
from .policy import (
    AnalysisIntent,
    CritiqueProposal,
    ExperimentChoice,
    GoalInterpretation,
    HypothesisProposal,
    HypothesisProposals,
)

_INTENT_KEYWORDS: list[tuple[AnalysisIntent, tuple[str, ...]]] = [
    (AnalysisIntent.trend, ("trend", "over time", "trajectory", "growth", "increas", "decreas", "declin", "rise", "fall")),
    (AnalysisIntent.comparison, ("compare", "comparison", "between", "versus", " vs ", "difference", "differ", "group")),
    (AnalysisIntent.correlation, ("correlat", "relationship", "predict", "driver", "associated with")),
    (AnalysisIntent.anomaly, ("unusual", "anomal", "outlier", "spike", "abnormal", "irregular")),
    (AnalysisIntent.ranking, ("rank", "top", "best", "worst", "largest", "highest", "lowest", "leading")),
    (AnalysisIntent.association, ("association", "depend", "contingency", "related to")),
    (AnalysisIntent.distribution, ("distribution", "spread", "describe", "summary", "summarise", "summarize")),
]



class FixtureAgentPolicy:
    """A deterministic :class:`~agentic.agent.policy.AgentPolicy`."""

    def interpret_goal(self, goal_text: str, *, capability_summary: dict) -> GoalInterpretation:
        text = f" {goal_text.lower()} "
        intent = AnalysisIntent.general
        for cand, kws in _INTENT_KEYWORDS:
            if any(k in text for k in kws):
                intent = cand
                break
        # Word-boundary parsing shared with the evidence updater, so a metric name that
        # embeds a direction word ("rainfall") cannot flip the interpreted direction.
        direction = parse_direction(text) if intent is AnalysisIntent.trend else None
        metrics = capability_summary.get("metrics") or []
        dims = capability_summary.get("dimensions") or []
        metric_hint = next((m for m in metrics if m.lower() in text), metrics[0] if metrics else None)
        group_hint = next((d for d in dims if d.lower() in text), dims[0] if dims else None)
        return GoalInterpretation(
            intent=intent, metric_hint=metric_hint, group_hint=group_hint, direction=direction,
            rationale=f"keyword intent={intent.value}",
        )

    def generate_hypotheses(
        self, interpretation: GoalInterpretation, *, metric_names: list[str],
        dimension_names: list[str], goal_text: str = "",
    ) -> HypothesisProposals:
        metric = interpretation.metric_hint or (metric_names[0] if metric_names else "value")
        intent = interpretation.intent
        hyps: list[HypothesisProposal] = []
        questions: list[str] = []
        if intent is AnalysisIntent.trend:
            d = interpretation.direction or "up"
            word = "increasing" if d == "up" else "decreasing"
            hyps.append(HypothesisProposal(statement=f"{metric} is {word} over time", metric=metric, direction=d,
                                           rationale="trend goal"))
            questions.append(f"Is the movement in {metric} sustained or a one-off shift?")
        elif intent is AnalysisIntent.comparison:
            hyps.append(HypothesisProposal(statement=f"{metric} differs across groups", metric=metric, direction="none",
                                           rationale="comparison goal"))
            questions.append(f"Which group drives the difference in {metric}?")
        elif intent is AnalysisIntent.correlation:
            hyps.append(HypothesisProposal(statement=f"{metric} is associated with another metric", metric=metric,
                                           direction="none", rationale="correlation goal"))
        elif intent is AnalysisIntent.anomaly:
            hyps.append(HypothesisProposal(statement=f"{metric} contains anomalous values", metric=metric,
                                           direction="none", rationale="anomaly goal"))
            questions.append(f"Are anomalies in {metric} isolated or recurring?")
        elif intent is AnalysisIntent.ranking:
            hyps.append(HypothesisProposal(statement=f"entities differ substantially in {metric}", metric=metric,
                                           direction="none", rationale="ranking goal"))
        elif intent is AnalysisIntent.association:
            hyps.append(HypothesisProposal(statement="the two categorical fields are associated", metric=None,
                                           direction="none", rationale="association goal"))
        else:
            hyps.append(HypothesisProposal(statement=f"{metric} has a describable distribution", metric=metric,
                                           direction="none", rationale="general goal"))
        return HypothesisProposals(hypotheses=hyps, questions=questions)

    def select_experiment(self, *, goal_summary: dict, candidates: list[dict]) -> ExperimentChoice:
        if not candidates:
            return ExperimentChoice(request_index=None, rationale="no candidates")
        # Prefer falsification candidates, then highest expected information gain,
        # then the earliest candidate (deterministic tie-break).
        def key(c: dict):
            return (0 if c.get("falsification") else 1, -float(c.get("expected_information_gain", 0.0)), c["index"])

        best = min(candidates, key=key)
        return ExperimentChoice(request_index=best["index"], rationale="max information gain")

    def critique(self, *, strongest_claim: dict | None, available_tools: list[str]) -> CritiqueProposal:
        if not strongest_claim or not available_tools:
            return CritiqueProposal(should_challenge=False, rationale="nothing to challenge")
        # Challenge a supported, not-yet-challenged claim with an unused falsification tool.
        if strongest_claim.get("status") == "supported" and not strongest_claim.get("already_critiqued"):
            return CritiqueProposal(
                should_challenge=True,
                target_hypothesis_id=strongest_claim.get("id"),
                falsification_tool=available_tools[0],
                message="Test whether the supported claim survives an independent method.",
                rationale="falsify strongest supported claim",
            )
        return CritiqueProposal(should_challenge=False, rationale="strongest claim not yet supported")
