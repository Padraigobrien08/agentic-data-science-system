"""
Deterministic fixture policy for tests.

Rule-based, no LLM. Produces stable typed decisions so integration tests are
deterministic. Intent is keyword-derived from the goal, so execution paths differ
across goals; selection prefers falsification candidates then highest information
gain, so intermediate results steer the loop.
"""

from __future__ import annotations

from .direction import parse_direction, parse_extreme
from .policy import (
    AnalysisIntent,
    ChallengeReason,
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
    (AnalysisIntent.ranking, ("rank", "top", "best", "worst", "weakest", "strongest", "largest",
                              "highest", "lowest", "smallest", "leading")),
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
        #
        # A ranking goal reads its *superlative* instead of its movement words: "which region
        # is weakest" asks for the bottom of the ordering, and `rank_entities` reports the top
        # unless something says otherwise. Leaving this null answered every such goal with the
        # strongest entity — a true statement about the opposite question.
        direction = None
        if intent is AnalysisIntent.trend:
            direction = parse_direction(text)
        elif intent is AnalysisIntent.ranking:
            direction = parse_extreme(text)
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

    #: What a rule engine can honestly say for each reason it may be asked. Keyed so the
    #: policy answers the question it was actually asked rather than checking a status and
    #: inferring one — the critic now asks about claims that never reach `supported`.
    _CHALLENGE_MESSAGE: dict[ChallengeReason, tuple[str, str]] = {
        ChallengeReason.false_confidence: (
            "Test whether the supported claim survives an independent method.",
            "falsify strongest supported claim",
        ),
        ChallengeReason.conflicting_evidence: (
            "Evidence points both ways. Test whether an independent method separates them.",
            "resolve conflicting evidence",
        ),
        ChallengeReason.undiscriminating_evidence: (
            "Every measurement so far was neutral. Test whether another method discriminates.",
            "measurements are not separating anything",
        ),
        ChallengeReason.unexplained_refutation: (
            "Evidence refutes this claim. Test it by an independent method before dropping it.",
            "refuted by one method; confirm before it is dropped",
        ),
    }

    def critique(
        self,
        *,
        strongest_claim: dict | None,
        available_tools: list[str],
        # Accepted for protocol conformance and deliberately unused: deciding that two
        # statements are mutually exclusive is a judgement, and a rule engine that guessed at
        # it would report contradictions this policy cannot actually detect. Leaving it None
        # also keeps the published agency scores comparable across this change.
        supported_claims: list[dict] | None = None,
    ) -> CritiqueProposal:
        if not strongest_claim or not available_tools:
            return CritiqueProposal(should_challenge=False, rationale="nothing to challenge")
        # One challenge per claim. The critic runs every iteration, and the widened gate keeps
        # qualifying the same claim until its evidence changes shape, so without this the rule
        # engine would raise the same critique repeatedly and burn the budget on it.
        if strongest_claim.get("already_critiqued"):
            return CritiqueProposal(should_challenge=False, rationale="already challenged")
        reason = ChallengeReason(
            strongest_claim.get("challenge_reason") or ChallengeReason.false_confidence.value)
        message, rationale = self._CHALLENGE_MESSAGE[reason]
        return CritiqueProposal(
            should_challenge=True,
            target_hypothesis_id=strongest_claim.get("id"),
            falsification_tool=available_tools[0],
            message=message,
            rationale=rationale,
        )
