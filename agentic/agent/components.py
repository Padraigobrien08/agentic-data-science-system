"""
The ten explicit investigation-loop components.

Each is a small deterministic class that consumes typed policy decisions
(:mod:`agentic.agent.policy`) and the deterministic experiment registry
(:mod:`agentic.experiments`). The policy interprets/plans; these components and
the registry compute. Every step records an :class:`AgentDecision` into state.
"""

from __future__ import annotations

import math
from typing import Callable, TypeVar

import pandas as pd

from agentic.domain import (
    AgentDecision,
    Conclusion,
    ConclusionDisposition,
    Critique,
    DecisionType,
    EntityKind,
    EntityRef,
    Evidence,
    EvidenceDirection,
    ExperimentRequest,
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    OpenQuestion,
    TerminationDecision,
    TerminationReason,
)
from agentic.domain.enums import CritiqueSeverity, CritiqueType, ProvenanceSource
from agentic.domain.manifest import DatasetManifest
from agentic.domain.provenance import Provenance
from agentic.experiments import ArtifactSink, ExperimentContext, ExperimentRegistry, InMemoryArtifactSink
from agentic.experiments.record import ExperimentExecutionRecord

from .budget import BudgetTracker
from .ids import DeterministicIds
from .policy import AgentPolicy, AnalysisIntent, GoalInterpretation, drain_policy_cost

# Intent -> ordered candidate tools (general layer). Order encodes priority.
INTENT_TOOLS: dict[AnalysisIntent, list[str]] = {
    AnalysisIntent.trend: ["analyze_time_series_trend", "detect_change_points", "summarize_distribution"],
    AnalysisIntent.comparison: ["compare_groups", "rank_entities"],
    AnalysisIntent.correlation: ["analyze_correlation", "fit_simple_regression"],
    AnalysisIntent.anomaly: ["detect_outliers", "summarize_distribution"],
    AnalysisIntent.ranking: ["rank_entities", "compare_groups"],
    AnalysisIntent.association: ["test_association"],
    AnalysisIntent.distribution: ["summarize_distribution", "profile_dataset"],
    AnalysisIntent.profile: ["profile_dataset", "summarize_distribution"],
    AnalysisIntent.general: ["profile_dataset", "summarize_distribution"],
}

# EDGAR domain tools added when the dataset is an EDGAR panel.
EDGAR_INTENT_TOOLS: dict[AnalysisIntent, list[str]] = {
    AnalysisIntent.anomaly: ["edgar_revenue_growth_analysis", "edgar_margin_quality_analysis"],
    AnalysisIntent.trend: ["edgar_trend_break_analysis"],
    AnalysisIntent.comparison: ["edgar_peer_comparison"],
}

_T = TypeVar("_T")

_UP_WORDS = ("increasing", "up", "grow", "rise", "higher")
_DOWN_WORDS = ("decreasing", "down", "declin", "fall", "drop", "lower", "deteriorat")


def _invoke_policy(tracker: BudgetTracker, policy: AgentPolicy, call: Callable[[], _T]) -> _T:
    """
    Run one policy decision against the run's budget: count it before the call (so a
    policy that raises is still counted) and attribute its cost after, whether or not
    it raised. Policies that don't track cost contribute zero.
    """
    tracker.record_model_call()
    try:
        return call()
    finally:
        tracker.record_model_cost(drain_policy_cost(policy))


def _prov(agent_id: str) -> Provenance:
    return Provenance(source=ProvenanceSource.agent_llm, agent_id=agent_id)


def _sign(x: float | None) -> int:
    if x is None or not math.isfinite(x) or abs(x) < 1e-9:
        return 0
    return 1 if x > 0 else -1


def is_edgar_manifest(manifest: DatasetManifest) -> bool:
    if manifest.source_identity is not None and manifest.source_identity.adapter_id == "edgar":
        return True
    names = {c.name for c in manifest.columns}
    return {"cik", "period"}.issubset(names)


def expectation_direction(h: Hypothesis) -> int | None:
    """+1 (up), -1 (down), or None (non-directional) parsed from the statement."""
    s = h.statement.lower()
    if any(w in s for w in _UP_WORDS):
        return 1
    if any(w in s for w in _DOWN_WORDS):
        return -1
    return None


# ---------------------------------------------------------------------------
# 1. GoalInterpreter
# ---------------------------------------------------------------------------


class GoalInterpreter:
    def __init__(self, policy: AgentPolicy) -> None:
        self._policy = policy

    def interpret(self, goal_text: str, manifest: DatasetManifest, tracker: BudgetTracker) -> GoalInterpretation:
        summary = {"metrics": manifest.metric_names(),
                   "dimensions": [c.name for c in manifest.columns if c.role.value == "dimension"]}
        return _invoke_policy(
            tracker, self._policy,
            lambda: self._policy.interpret_goal(goal_text, capability_summary=summary))


# ---------------------------------------------------------------------------
# 2. HypothesisGenerator
# ---------------------------------------------------------------------------


class HypothesisGenerator:
    def __init__(self, policy: AgentPolicy) -> None:
        self._policy = policy

    def generate(
        self, interpretation: GoalInterpretation, state: InvestigationState,
        manifest: DatasetManifest, idgen: DeterministicIds, tracker: BudgetTracker,
    ) -> None:
        dims = [c.name for c in manifest.columns if c.role.value == "dimension"]
        proposals = _invoke_policy(
            tracker, self._policy,
            lambda: self._policy.generate_hypotheses(
                interpretation, metric_names=manifest.metric_names(), dimension_names=dims))
        for i, p in enumerate(proposals.hypotheses):
            h = Hypothesis(
                id=idgen.make("hyp", i), statement=p.statement, rationale=p.rationale,
                metric_refs=[p.metric] if p.metric else [], provenance=_prov("hypothesis_generator"),
            )
            state.add_hypothesis(h)
            state.record_decision(AgentDecision(
                id=idgen.make("dec-hyp", i), decision_type=DecisionType.propose_hypothesis,
                rationale=p.rationale or "proposed from goal",
                targets=[EntityRef(kind=EntityKind.hypothesis, id=h.id)], provenance=_prov("hypothesis_generator")))
        for j, q in enumerate(proposals.questions):
            state.add_open_question(OpenQuestion(
                id=idgen.make("q", j), question=q,
                related_hypothesis_ids=[h.id for h in state.hypotheses], provenance=_prov("hypothesis_generator")))


# ---------------------------------------------------------------------------
# 3. InvestigationPlanner  (builds validated candidate experiments)
# ---------------------------------------------------------------------------


class InvestigationPlanner:
    def __init__(self, registry: ExperimentRegistry) -> None:
        self._registry = registry

    def _params_for(self, tool: str, interpretation: GoalInterpretation, manifest: DatasetManifest) -> dict:
        metrics = manifest.metric_names()
        metric = interpretation.metric_hint or (metrics[0] if metrics else None)
        dims = [c.name for c in manifest.columns if c.role.value == "dimension"]
        group = interpretation.group_hint or (dims[0] if dims else None)
        entity = manifest.entity_id_column().name if manifest.entity_id_column() else None
        if tool in ("summarize_distribution", "detect_outliers"):
            return {"column": metric} if metric else {}
        if tool == "analyze_time_series_trend":
            return {"value_column": metric} if metric else {}
        if tool == "detect_change_points":
            return {"value_column": metric} if metric else {}
        if tool == "compare_groups":
            return {"value_column": metric, "group_column": group} if metric and group else {}
        if tool == "rank_entities":
            p = {"metric_column": metric} if metric else {}
            if entity:
                p["entity_column"] = entity
            return p
        if tool == "fit_simple_regression":
            return {"x_column": metrics[0], "y_column": metrics[1]} if len(metrics) >= 2 else {}
        if tool == "test_association":
            return {"column_a": dims[0], "column_b": dims[1]} if len(dims) >= 2 else {}
        return {}  # profile_dataset, analyze_correlation, edgar_* take no/auto params

    def _target_hypothesis(self, state: InvestigationState, metric: str | None) -> str | None:
        for h in state.open_hypotheses():
            if not h.metric_refs or (metric and metric in h.metric_refs):
                return h.id
        return state.hypotheses[0].id if state.hypotheses else None

    def candidates(
        self, state: InvestigationState, interpretation: GoalInterpretation,
        manifest: DatasetManifest, executed_tools: set[str], tracker: BudgetTracker, idgen: DeterministicIds,
    ) -> list[ExperimentRequest]:
        metric = interpretation.metric_hint or (manifest.metric_names()[0] if manifest.metric_names() else None)
        target = self._target_hypothesis(state, metric)
        tools = list(INTENT_TOOLS.get(interpretation.intent, INTENT_TOOLS[AnalysisIntent.general]))
        if is_edgar_manifest(manifest):
            tools = EDGAR_INTENT_TOOLS.get(interpretation.intent, []) + tools

        out: list[ExperimentRequest] = []
        seen: set[str] = set()
        n = len(state.pending_experiments) + len(state.completed_experiments) + len(state.failed_experiments)

        # falsification candidates from open critiques (unused tool, targets a hypothesis)
        for c in state.critiques:
            ftool = c.suggested_action
            if not ftool or ftool in executed_tools or ftool in seen or tracker.tool_at_limit(ftool):
                continue
            if not self._registry.has(ftool):
                continue
            params = self._params_for(ftool, interpretation, manifest)
            if not self._registry.get(ftool).validate(params=params, manifest=manifest).ok:
                continue
            out.append(ExperimentRequest(
                id=idgen.make("exp", n + len(out)), tool_name=ftool, parameters=params,
                purpose=f"falsify hypothesis {c.target.id}", definition_id="falsification",
                target_hypothesis_ids=[c.target.id], expected_information_gain=0.95,
                provenance=_prov("investigation_planner")))
            seen.add(ftool)

        for prio, tool in enumerate(tools):
            if tool in executed_tools or tool in seen or tracker.tool_at_limit(tool):
                continue
            if not self._registry.has(tool):
                continue
            params = self._params_for(tool, interpretation, manifest)
            if not self._registry.get(tool).validate(params=params, manifest=manifest).ok:
                continue
            gain = round(max(0.3, 0.85 - 0.1 * prio), 4)
            out.append(ExperimentRequest(
                id=idgen.make("exp", n + len(out)), tool_name=tool, parameters=params,
                purpose=f"{interpretation.intent.value} analysis via {tool}",
                target_hypothesis_ids=[target] if target else [], expected_information_gain=gain,
                provenance=_prov("investigation_planner")))
            seen.add(tool)
        return out


# ---------------------------------------------------------------------------
# 4. ExperimentSelector
# ---------------------------------------------------------------------------


class ExperimentSelector:
    def __init__(self, policy: AgentPolicy) -> None:
        self._policy = policy

    def select(
        self, state: InvestigationState, candidates: list[ExperimentRequest],
        interpretation: GoalInterpretation, tracker: BudgetTracker, idgen: DeterministicIds,
    ) -> ExperimentRequest | None:
        if not candidates:
            return None
        summaries = [
            {"index": i, "tool_name": c.tool_name, "purpose": c.purpose,
             "expected_information_gain": c.expected_information_gain,
             "falsification": c.definition_id == "falsification"}
            for i, c in enumerate(candidates)
        ]
        choice = _invoke_policy(
            tracker, self._policy,
            lambda: self._policy.select_experiment(
                goal_summary={"intent": interpretation.intent.value}, candidates=summaries))
        if choice.request_index is None or not (0 <= choice.request_index < len(candidates)):
            return None
        chosen = candidates[choice.request_index]
        state.add_experiment_request(chosen)
        state.record_decision(AgentDecision(
            id=idgen.make("dec-sel", len(state.decisions)), decision_type=DecisionType.select_experiment,
            rationale=choice.rationale or "selected next experiment", iteration=state.budget.iterations_used,
            targets=[EntityRef(kind=EntityKind.experiment_request, id=chosen.id)],
            chosen_option=chosen.tool_name, provenance=_prov("experiment_selector")))
        return chosen


# ---------------------------------------------------------------------------
# 5. ExperimentExecutor
# ---------------------------------------------------------------------------


class ExperimentExecutor:
    def __init__(self, registry: ExperimentRegistry, *, artifact_sink: ArtifactSink | None = None) -> None:
        self._registry = registry
        # When a shared sink is supplied (e.g. by the backend), every experiment emits into
        # it so the emitted bytes survive the loop and can be ingested + linked afterwards.
        # When absent, each experiment gets a throwaway sink (unchanged in-process behavior).
        self._artifact_sink = artifact_sink

    def execute(
        self, request: ExperimentRequest, manifest: DatasetManifest, frame: pd.DataFrame | None,
        idgen: DeterministicIds, state: InvestigationState,
    ) -> ExperimentExecutionRecord:
        sink = self._artifact_sink if self._artifact_sink is not None else InMemoryArtifactSink()
        ctx = ExperimentContext(
            manifest=manifest, frame=frame, raw_params=dict(request.parameters),
            artifact_sink=sink, request_id=request.id)
        record = self._registry.get(request.tool_name).run(ctx)
        result = record.to_domain_result()
        # deterministic ids for the persisted result/observations
        result.id = idgen.make("res", len(state.completed_experiments) + len(state.failed_experiments))
        request.status = record.status
        state.record_experiment_result(result)
        return record


# ---------------------------------------------------------------------------
# 6. EvidenceUpdater
# ---------------------------------------------------------------------------


class EvidenceUpdater:
    def update(
        self, state: InvestigationState, record: ExperimentExecutionRecord, request: ExperimentRequest,
        idgen: DeterministicIds,
    ) -> list[Evidence]:
        target = request.target_hypothesis_ids[0] if request.target_hypothesis_ids else None
        hyp = state.find_hypothesis(target) if target else None
        expected = expectation_direction(hyp) if hyp is not None else None
        record_signal = self._signal_sign(record)

        produced: list[Evidence] = []
        for i, e in enumerate(record.evidence):
            if expected is not None:
                # Prefer the evidence item's own directional statistic (e.g. per-entity
                # slope), so opposing signals in one experiment yield contradictory evidence.
                signal = self._evidence_sign(e)
                if signal == 0:
                    signal = record_signal
                if signal == 0:
                    direction = EvidenceDirection.neutral
                elif signal * expected > 0:
                    direction = EvidenceDirection.supports
                else:
                    direction = EvidenceDirection.refutes
            else:
                direction = EvidenceDirection.supports if e.direction == EvidenceDirection.supports else EvidenceDirection.neutral
            ev = Evidence(
                id=idgen.make("evd", len(state.evidence)), evidence_type=e.evidence_type,
                source_reference=e.source_reference, experiment_result_id=None,
                hypothesis_ids=[target] if target else [], claim=e.claim, direction=direction,
                strength=e.strength, reliability=e.reliability, coverage=e.coverage,
                statistics=e.statistics, provenance=_prov("evidence_updater"))
            state.add_evidence(ev)
            produced.append(ev)
        if produced and target:
            state.record_decision(AgentDecision(
                id=idgen.make("dec-evd", len(state.decisions)), decision_type=DecisionType.update_evidence,
                rationale=f"recorded {len(produced)} evidence item(s) for {request.tool_name}",
                targets=[EntityRef(kind=EntityKind.hypothesis, id=target)], provenance=_prov("evidence_updater")))
        return produced

    @staticmethod
    def _evidence_sign(e: Evidence) -> int:
        if e.statistics is not None:
            for key in ("slope", "shift", "mean_diff"):
                if key in e.statistics.diagnostics:
                    return _sign(e.statistics.diagnostics[key])
        return 0

    @staticmethod
    def _signal_sign(record: ExperimentExecutionRecord) -> int:
        for key in ("slope", "mean_slope", "shift", "mean_diff", "effect_size"):
            if key in record.metrics:
                return _sign(record.metrics[key])
        for s in record.statistics:
            for key in ("slope", "shift", "mean_diff"):
                if key in s.diagnostics:
                    return _sign(s.diagnostics[key])
        return 0


# ---------------------------------------------------------------------------
# 7. HypothesisUpdater
# ---------------------------------------------------------------------------


class HypothesisUpdater:
    SUPPORT_THRESHOLD = 0.5

    def update(self, state: InvestigationState, request: ExperimentRequest, idgen: DeterministicIds) -> None:
        target = request.target_hypothesis_ids[0] if request.target_hypothesis_ids else None
        h = state.find_hypothesis(target) if target else None
        if h is None or h.is_terminal():
            return
        if h.status is HypothesisStatus.proposed:
            h.set_status(HypothesisStatus.active)

        ev = state.evidence_for(h.id)
        supports = [e for e in ev if e.direction is EvidenceDirection.supports]
        refutes = [e for e in ev if e.direction is EvidenceDirection.refutes]
        s_str = max((e.strength for e in supports), default=0.0)
        r_str = max((e.strength for e in refutes), default=0.0)

        if supports and refutes:
            h.set_status(HypothesisStatus.weakened)
            h.set_confidence(round(max(0.25, 0.5 + 0.2 * (s_str - r_str)), 4))
        elif supports and not refutes:
            if s_str >= self.SUPPORT_THRESHOLD:
                h.set_status(HypothesisStatus.supported)
                h.set_confidence(round(min(0.95, 0.55 + s_str / 2), 4))
            else:
                h.set_confidence(round(0.45 + s_str / 4, 4))
        elif refutes and not supports:
            if r_str >= self.SUPPORT_THRESHOLD:
                h.set_status(HypothesisStatus.rejected)
                h.set_confidence(round(max(0.05, 0.4 - r_str / 2), 4))
            else:
                h.set_status(HypothesisStatus.weakened)
                h.set_confidence(round(max(0.2, 0.45 - r_str / 4), 4))
        state.record_decision(AgentDecision(
            id=idgen.make("dec-rev", len(state.decisions)), decision_type=DecisionType.revise_confidence,
            rationale=f"{h.status.value} (support={len(supports)}, refute={len(refutes)})",
            targets=[EntityRef(kind=EntityKind.hypothesis, id=h.id)], provenance=_prov("hypothesis_updater")))

        # follow-up question when evidence is present but weak
        if h.status is HypothesisStatus.active and 0.0 < s_str < self.SUPPORT_THRESHOLD:
            state.add_open_question(OpenQuestion(
                id=idgen.make("q-follow", len(state.open_questions)),
                question=f"Stronger evidence needed for: {h.statement}",
                related_hypothesis_ids=[h.id], provenance=_prov("hypothesis_updater")))


# ---------------------------------------------------------------------------
# 8. Critic
# ---------------------------------------------------------------------------


class Critic:
    def __init__(self, policy: AgentPolicy) -> None:
        self._policy = policy

    def challenge(
        self, state: InvestigationState, interpretation: GoalInterpretation, manifest: DatasetManifest,
        executed_tools: set[str], tracker: BudgetTracker, idgen: DeterministicIds,
    ) -> None:
        supported = [h for h in state.hypotheses if h.status is HypothesisStatus.supported]
        if not supported:
            return
        h = max(supported, key=lambda x: x.confidence)
        already = any(c.target.id == h.id for c in state.critiques)
        tools = list(INTENT_TOOLS.get(interpretation.intent, []))
        if is_edgar_manifest(manifest):
            tools = EDGAR_INTENT_TOOLS.get(interpretation.intent, []) + tools
        available = [t for t in tools if t not in executed_tools and self._registry_ok(t)]
        proposal = _invoke_policy(
            tracker, self._policy,
            lambda: self._policy.critique(
                strongest_claim={"id": h.id, "status": h.status.value, "confidence": h.confidence,
                                 "already_critiqued": already},
                available_tools=available))
        if not proposal.should_challenge or not proposal.target_hypothesis_id or not proposal.falsification_tool:
            return
        state.add_critique(Critique(
            id=idgen.make("crit", len(state.critiques)), critique_type=CritiqueType.competing_explanation,
            severity=CritiqueSeverity.major, target=EntityRef(kind=EntityKind.hypothesis, id=proposal.target_hypothesis_id),
            message=proposal.message, suggested_action=proposal.falsification_tool, provenance=_prov("critic")))
        state.record_decision(AgentDecision(
            id=idgen.make("dec-crit", len(state.decisions)), decision_type=DecisionType.request_critique,
            rationale=proposal.rationale or "challenge strongest claim",
            targets=[EntityRef(kind=EntityKind.hypothesis, id=proposal.target_hypothesis_id)],
            chosen_option=proposal.falsification_tool, provenance=_prov("critic")))

    def _registry_ok(self, _tool: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# 9. TerminationPolicy
# ---------------------------------------------------------------------------


class TerminationPolicy:
    SUFFICIENT_CONFIDENCE = 0.6

    def decide(
        self, state: InvestigationState, tracker: BudgetTracker, iterations: int, *,
        executed_tools: set[str], intent_tools: list[str], user_stop: bool,
    ) -> tuple[bool, TerminationReason | None]:
        if user_stop or tracker.user_stop_requested:
            return True, TerminationReason.user_stop
        if tracker.safety_violated(iterations):
            return True, TerminationReason.safety_constraint
        if tracker.repeated_failure():
            return True, TerminationReason.repeated_failure
        if tracker.budget_exhausted():
            return True, TerminationReason.budget_exhausted
        supported = [h for h in state.hypotheses
                     if h.status is HypothesisStatus.supported and h.confidence >= self.SUFFICIENT_CONFIDENCE]
        if supported:
            h = supported[0]
            crits = [c for c in state.critiques if c.target.id == h.id]
            unused = [t for t in intent_tools if t not in executed_tools]
            tested = any((c.suggested_action or "") in executed_tools for c in crits)
            if tested or not unused:
                return True, TerminationReason.sufficient_evidence
        return False, None

    def finalize_no_candidates(self, state: InvestigationState, ran_any: bool) -> TerminationReason:
        supported = [h for h in state.hypotheses
                     if h.status is HypothesisStatus.supported and h.confidence >= self.SUFFICIENT_CONFIDENCE]
        if supported:
            return TerminationReason.sufficient_evidence
        if ran_any:
            return TerminationReason.insufficient_evidence
        return TerminationReason.no_valid_experiment


# ---------------------------------------------------------------------------
# 10. ConclusionSynthesizer
# ---------------------------------------------------------------------------


class ConclusionSynthesizer:
    def synthesize(
        self, state: InvestigationState, reason: TerminationReason, idgen: DeterministicIds,
    ) -> Conclusion:
        supported = [h for h in state.hypotheses if h.status is HypothesisStatus.supported]
        rejected = [h for h in state.hypotheses if h.status is HypothesisStatus.rejected]
        weakened = [h for h in state.hypotheses if h.status is HypothesisStatus.weakened]

        # any still-active hypothesis is left explicitly unresolved
        for h in state.hypotheses:
            if h.status is HypothesisStatus.active:
                h.set_status(HypothesisStatus.unresolved)

        contradicting = [e.id for e in state.evidence if e.direction is EvidenceDirection.refutes]
        if supported:
            disposition = ConclusionDisposition.supported
            conf = round(sum(h.confidence for h in supported) / len(supported), 4)
            statement = "; ".join(h.statement for h in supported)
            hyp_ids = [h.id for h in supported]
            key_ev = [e.id for e in state.evidence if e.direction is EvidenceDirection.supports]
        elif rejected and not weakened:
            disposition = ConclusionDisposition.refuted
            conf = 0.6
            statement = "Rejected: " + "; ".join(h.statement for h in rejected)
            hyp_ids = [h.id for h in rejected]
            key_ev = contradicting
        elif weakened:
            disposition = ConclusionDisposition.inconclusive
            conf = 0.4
            statement = "Mixed evidence for: " + "; ".join(h.statement for h in weakened)
            hyp_ids = [h.id for h in weakened]
            key_ev = [e.id for e in state.evidence]
        else:
            disposition = ConclusionDisposition.insufficient_evidence
            conf = 0.2
            statement = "Insufficient evidence to resolve the investigation goal."
            hyp_ids = [h.id for h in state.hypotheses]
            key_ev = []

        caveats = [f"termination: {reason.value}"]
        if contradicting:
            caveats.append(f"{len(contradicting)} contradicting evidence item(s) preserved")
        if state.unresolved_questions():
            caveats.append(f"{len(state.unresolved_questions())} open question(s) remain")

        conclusion = Conclusion(
            id=idgen.make("concl", 0), statement=statement, disposition=disposition, confidence=conf,
            supporting_hypothesis_ids=hyp_ids, key_evidence_ids=key_ev, caveats=caveats,
            open_question_ids=[q.id for q in state.open_questions], provenance=_prov("conclusion_synthesizer"))
        state.set_conclusion(conclusion)
        state.record_decision(AgentDecision(
            id=idgen.make("dec-concl", len(state.decisions)), decision_type=DecisionType.conclude,
            rationale=f"{disposition.value} ({reason.value})",
            targets=[EntityRef(kind=EntityKind.conclusion, id=conclusion.id)], provenance=_prov("conclusion_synthesizer")))
        return conclusion


def make_termination(reason: TerminationReason, state: InvestigationState, idgen: DeterministicIds) -> TerminationDecision:
    return TerminationDecision(
        should_stop=True, reason=reason,
        rationale=f"terminated: {reason.value}", at_iteration=state.budget.iterations_used,
        provenance=_prov("termination_policy"))
