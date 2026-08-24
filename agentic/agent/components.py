"""
The ten explicit investigation-loop components.

Each is a small deterministic class that consumes typed policy decisions
(:mod:`agentic.agent.policy`) and the deterministic experiment registry
(:mod:`agentic.experiments`). The policy interprets/plans; these components and
the registry compute. Every step records an :class:`AgentDecision` into state.
"""

from __future__ import annotations

import math
import threading
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
from .direction import direction_sign
from .ids import DeterministicIds
from .narrative import AllowedNumbers, verify_narrative
from .policy import (
    AgentPolicy,
    AnalysisIntent,
    CritiqueProposal,
    GoalInterpretation,
    drain_policy_cost,
    narrate_answer,
)

# Intent -> ordered candidate tools (general layer). Order encodes priority.
INTENT_TOOLS: dict[AnalysisIntent, list[str]] = {
    AnalysisIntent.trend: ["analyze_time_series_trend", "detect_change_points", "summarize_distribution"],
    AnalysisIntent.comparison: ["compare_groups", "rank_entities"],
    AnalysisIntent.correlation: ["analyze_correlation", "fit_simple_regression"],
    AnalysisIntent.anomaly: ["detect_outliers", "summarize_distribution"],
    AnalysisIntent.ranking: ["rank_entities", "compare_groups"],
    # Second tool for the same reason as `distribution` above: with only `test_association`
    # available, a goal resolving here could state a rival explanation and never run anything
    # against it. `compare_groups` answers the usual one — that the association is really a
    # difference between the groups themselves.
    AnalysisIntent.association: ["test_association", "compare_groups"],
    # `detect_outliers` belongs here, not only under `anomaly`. "Is a small tail dragging the
    # mean up?" is a distribution question whose rival explanation is literally outliers, and
    # without the tool the planner had nothing to raise against that claim — a real run left
    # it at `proposed` after exhausting both other tools, and the loop correctly refused to
    # conclude while an untested alternative stood.
    AnalysisIntent.distribution: ["summarize_distribution", "profile_dataset", "detect_outliers"],
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


def _quote(statement: str, *, limit: int = 120) -> str:
    """A claim quoted for prose, shortened at a word boundary so it reads as a sentence."""
    text = " ".join(statement.split())
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return f"“{text}”"


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
    return direction_sign(h.statement)


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
                interpretation, metric_names=manifest.metric_names(), dimension_names=dims,
                goal_text=state.objective.objective))
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

    @staticmethod
    def _metric_for(
        hypothesis: Hypothesis | None, interpretation: GoalInterpretation, manifest: DatasetManifest
    ) -> str | None:
        """
        Which metric an experiment should measure, most specific source first.

        The hypothesis wins: an experiment exists to test *a claim*, and a claim already knows
        its own metric. Reading only ``interpretation.metric_hint`` — one value for the whole
        investigation — is why a second hypothesis over a second metric could never be
        investigated by any policy, however well it reasoned.
        """
        if hypothesis is not None and hypothesis.metric_refs:
            return hypothesis.metric_refs[0]
        metrics = manifest.metric_names()
        return interpretation.metric_hint or (metrics[0] if metrics else None)

    def _params_for(
        self,
        tool: str,
        interpretation: GoalInterpretation,
        manifest: DatasetManifest,
        hypothesis: Hypothesis | None = None,
    ) -> dict:
        metrics = manifest.metric_names()
        metric = self._metric_for(hypothesis, interpretation, manifest)
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

    def _executed_pairs(
        self, state: InvestigationState, interpretation: GoalInterpretation, manifest: DatasetManifest
    ) -> set[tuple[str, str | None]]:
        """``(tool, metric)`` combinations already run, resolved the same way they were planned.

        Reads :attr:`InvestigationState.executed_requests` — the results themselves record only
        a tool name, so they cannot say which claim, or which column, an experiment addressed.
        """
        pairs: set[tuple[str, str | None]] = set()
        for request in state.executed_requests:
            hyp = None
            if request.target_hypothesis_ids:
                hyp = state.find_hypothesis(request.target_hypothesis_ids[0])
            pairs.add((request.tool_name, self._metric_for(hyp, interpretation, manifest)))
        return pairs

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
        # Keyed by (tool, metric) rather than tool alone: running one tool against two different
        # metrics answers two different questions, while running it twice against the same
        # metric is the redundancy `executed_tools` was there to prevent.
        seen: set[tuple[str, str | None]] = set()
        done = self._executed_pairs(state, interpretation, manifest)
        n = len(state.pending_experiments) + len(state.completed_experiments) + len(state.failed_experiments)

        # falsification candidates from open critiques (unused tool, targets a hypothesis)
        for c in state.critiques:
            ftool = c.suggested_action
            if not ftool or tracker.tool_at_limit(ftool):
                continue
            challenged = state.find_hypothesis(c.target.id)
            key = (ftool, self._metric_for(challenged, interpretation, manifest))
            if key in done or key in seen:
                continue
            if not self._registry.has(ftool):
                continue
            params = self._params_for(ftool, interpretation, manifest, challenged)
            if not self._registry.get(ftool).validate(params=params, manifest=manifest).ok:
                continue
            out.append(ExperimentRequest(
                id=idgen.make("exp", n + len(out)), tool_name=ftool, parameters=params,
                purpose=f"falsify hypothesis {c.target.id}", definition_id="falsification",
                target_hypothesis_ids=[c.target.id], expected_information_gain=0.95,
                provenance=_prov("investigation_planner")))
            seen.add(key)

        # Every open claim gets candidates, in hypothesis order then tool priority — a pure
        # function of state, never set or dict iteration order, so ids, batching, replay and
        # diff stay deterministic. With a single open hypothesis this yields exactly the list
        # it produced before, in the same order.
        # Claims are grouped by the metric their experiments would measure, because the
        # dedupe key is `(tool, metric)` and two claims about the same metric would otherwise
        # collide: the first took the key, and every later claim silently got nothing and sat
        # at `proposed` forever. That is the normal case, not an edge one — a goal phrased as
        # two competing explanations is two claims about one metric.
        #
        # Grouping rather than duplicating is deliberate. The same tool over the same metric
        # returns the same numbers, so running it twice would buy nothing and double-count
        # the evidence; it runs once and names every claim it bears on, and the evidence
        # updater scores it separately against each.
        #
        # Dict insertion order follows `open_hypotheses()`, so ordering stays a pure function
        # of state — ids, batching, replay and diff remain deterministic.
        grouped: dict[str | None, list[Hypothesis | None]] = {}
        for hypothesis in state.open_hypotheses() or [None]:
            grouped.setdefault(
                self._metric_for(hypothesis, interpretation, manifest), []
            ).append(hypothesis)

        for group_metric, group in grouped.items():
            hyp_targets = [h.id for h in group if h is not None] or ([target] if target else [])
            representative = group[0]
            for prio, tool in enumerate(tools):
                if tracker.tool_at_limit(tool):
                    continue
                key = (tool, group_metric)
                if key in done or key in seen:
                    continue
                if not self._registry.has(tool):
                    continue
                params = self._params_for(tool, interpretation, manifest, representative)
                if not self._registry.get(tool).validate(params=params, manifest=manifest).ok:
                    continue
                gain = round(max(0.3, 0.85 - 0.1 * prio), 4)
                out.append(ExperimentRequest(
                    id=idgen.make("exp", n + len(out)), tool_name=tool, parameters=params,
                    purpose=f"{interpretation.intent.value} analysis via {tool}",
                    target_hypothesis_ids=list(hyp_targets),
                    expected_information_gain=gain,
                    provenance=_prov("investigation_planner")))
                seen.add(key)
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
        self._accept(state, chosen, idgen, choice.rationale or "selected next experiment")
        return chosen

    def select_batch(
        self, state: InvestigationState, candidates: list[ExperimentRequest],
        interpretation: GoalInterpretation, tracker: BudgetTracker, idgen: DeterministicIds,
        *, limit: int,
    ) -> list[ExperimentRequest]:
        """
        Select up to ``limit`` experiments to run together, in execution order.

        The **lead** experiment is chosen by the policy exactly as in :meth:`select` — one
        model call per iteration, unchanged. Any remaining slots are filled deterministically
        from the planner's ranked candidates, which already encode priority order.

        Filling deterministically rather than asking the policy per slot is deliberate: it
        keeps ``AgentPolicy`` a four-method contract, keeps model calls at one per iteration
        (so a wider batch *lowers* cost per experiment), and keeps the batch reproducible.
        The trade-off is that followers are picked without seeing the lead's result — which
        is exactly why the batch is bounded.
        """
        if limit <= 1:
            lead = self.select(state, candidates, interpretation, tracker, idgen)
            return [lead] if lead is not None else []

        lead = self.select(state, candidates, interpretation, tracker, idgen)
        if lead is None:
            return []
        batch = [lead]
        for candidate in candidates:
            if len(batch) >= limit:
                break
            if candidate.id == lead.id or candidate.tool_name in {b.tool_name for b in batch}:
                continue
            self._accept(state, candidate, idgen, "batched alongside the selected experiment")
            batch.append(candidate)
        return batch

    def _accept(
        self, state: InvestigationState, chosen: ExperimentRequest, idgen: DeterministicIds,
        rationale: str,
    ) -> None:
        state.add_experiment_request(chosen)
        state.record_decision(AgentDecision(
            id=idgen.make("dec-sel", len(state.decisions)), decision_type=DecisionType.select_experiment,
            rationale=rationale,
            targets=[EntityRef(kind=EntityKind.experiment_request, id=chosen.id)],
            chosen_option=chosen.tool_name, provenance=_prov("experiment_selector")))


# ---------------------------------------------------------------------------
# 5. ExperimentExecutor
# ---------------------------------------------------------------------------


class LockedArtifactSink(ArtifactSink):
    """
    Serializes emission into a shared sink so a parallel batch can share one safely.

    Only emission is serialized — the analysis itself still runs concurrently. The order
    of records within the shared sink is therefore completion order and is deliberately
    not part of the contract: artifacts are looked up by id, never by position.
    """

    def __init__(self, inner: ArtifactSink) -> None:
        self._inner = inner
        self._lock = threading.Lock()

    def emit_table(self, name: str, frame: pd.DataFrame):
        with self._lock:
            return self._inner.emit_table(name, frame)

    def emit_json(self, name: str, obj):
        with self._lock:
            return self._inner.emit_json(name, obj)

    def emit_chart(self, name: str, spec: dict):
        with self._lock:
            return self._inner.emit_chart(name, spec)


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
        """Run one experiment and fold it into state (the sequential path)."""
        record = self.run(request, manifest, frame)
        self.record(record, request, idgen, state)
        return record

    def run(
        self, request: ExperimentRequest, manifest: DatasetManifest, frame: pd.DataFrame | None,
        *, sink: ArtifactSink | None = None,
    ) -> ExperimentExecutionRecord:
        """
        Run the deterministic tool. **Pure with respect to investigation state**, so a batch
        of experiments can run concurrently; ``sink`` lets each one collect artifacts into its
        own buffer rather than racing on the shared one.

        Tools are read-only over ``frame``; they must not mutate it, or concurrent execution
        would not be safe.
        """
        target = sink if sink is not None else self._artifact_sink
        ctx = ExperimentContext(
            manifest=manifest, frame=frame, raw_params=dict(request.parameters),
            artifact_sink=target if target is not None else InMemoryArtifactSink(),
            request_id=request.id)
        return self._registry.get(request.tool_name).run(ctx)

    def record(
        self, record: ExperimentExecutionRecord, request: ExperimentRequest,
        idgen: DeterministicIds, state: InvestigationState,
    ) -> None:
        """Fold one finished experiment into state. Always called in selection order, so
        result ids stay a pure function of state regardless of completion order."""
        result = record.to_domain_result()
        # deterministic ids for the persisted result/observations
        result.id = idgen.make("res", len(state.completed_experiments) + len(state.failed_experiments))
        request.status = record.status
        state.record_experiment_result(result)

    @property
    def shared_sink(self) -> ArtifactSink | None:
        return self._artifact_sink


# ---------------------------------------------------------------------------
# 6. EvidenceUpdater
# ---------------------------------------------------------------------------


class EvidenceUpdater:
    def update(
        self, state: InvestigationState, record: ExperimentExecutionRecord, request: ExperimentRequest,
        idgen: DeterministicIds,
    ) -> list[Evidence]:
        # Every claim the experiment was raised to test, not just the first.
        #
        # One measurement can bear on two rival explanations at once, and it does not bear on
        # them the same way: `expectation_direction` is a property of the hypothesis, so the
        # slope that supports "this is a sustained change" is the slope that refutes "this is
        # a few extreme quarters". Reading only `target_hypothesis_ids[0]` scored the first
        # claim and left the second with no evidence at all — which is how a rival stayed at
        # `proposed` while every tool in its intent had already run.
        targets: list[str | None] = [
            t for t in request.target_hypothesis_ids if state.find_hypothesis(t) is not None
        ] or [None]
        record_signal = self._signal_sign(record)

        produced: list[Evidence] = []
        for e, target in [(e, t) for e in record.evidence for t in targets]:
            hyp = state.find_hypothesis(target) if target else None
            expected = expectation_direction(hyp) if hyp is not None else None
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
        named = [t for t in targets if t]
        if produced and named:
            # One decision naming every claim the evidence was filed against, so the trace
            # shows a shared experiment as the single act it was rather than one act per claim.
            state.record_decision(AgentDecision(
                id=idgen.make("dec-evd", len(state.decisions)), decision_type=DecisionType.update_evidence,
                rationale=f"recorded {len(produced)} evidence item(s) for {request.tool_name}",
                targets=[EntityRef(kind=EntityKind.hypothesis, id=t) for t in named],
                provenance=_prov("evidence_updater")))
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
        # Score every claim the experiment was raised to test. Reading only the first was the
        # last of three places that did so: the planner then named both claims and the
        # evidence updater filed against both, but the rival was still never scored, so it
        # sat at `proposed` and the loop kept declining with an untested alternative standing.
        for target in request.target_hypothesis_ids or []:
            self._score(state, target, request, idgen)

    def _score(
        self, state: InvestigationState, target: str, request: ExperimentRequest,
        idgen: DeterministicIds,
    ) -> None:
        h = state.find_hypothesis(target)
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
    #: Ceiling applied to both sides of a contradiction. Two claims that cannot both hold
    #: must not sit at high confidence while the conflict is open; capping rather than
    #: zeroing keeps whatever evidence each has, because the conflict says one of them is
    #: wrong, not which one.
    CONTRADICTION_CONFIDENCE_CAP = 0.5

    def __init__(self, policy: AgentPolicy) -> None:
        self._policy = policy

    def challenge(
        self, state: InvestigationState, interpretation: GoalInterpretation, manifest: DatasetManifest,
        executed_tools: set[str], tracker: BudgetTracker, idgen: DeterministicIds,
    ) -> None:
        h = self._claim_to_challenge(state)
        if h is None:
            return
        already = any(c.target.id == h.id for c in state.critiques)
        tools = list(INTENT_TOOLS.get(interpretation.intent, []))
        if is_edgar_manifest(manifest):
            tools = EDGAR_INTENT_TOOLS.get(interpretation.intent, []) + tools
        available = [t for t in tools if t not in executed_tools and self._registry_ok(t)]
        # Every supported claim, so the policy can see that two of them disagree. Nothing
        # else in the loop compares claims to each other: the hypothesis updater scores each
        # one against its own evidence, which is exactly how a claim and its negation both
        # reached `supported`.
        supported_claims = [
            {"id": x.id, "statement": x.statement, "confidence": x.confidence}
            for x in state.hypotheses
            if x.status is HypothesisStatus.supported
        ]
        proposal = _invoke_policy(
            tracker, self._policy,
            lambda: self._policy.critique(
                strongest_claim={"id": h.id, "status": h.status.value, "confidence": h.confidence,
                                 "already_critiqued": already},
                available_tools=available,
                supported_claims=supported_claims))

        if self._record_contradiction(state, proposal, idgen, asked_about=h):
            return

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

    def _record_contradiction(
        self, state: InvestigationState, proposal: CritiqueProposal, idgen: DeterministicIds,
        *, asked_about: Hypothesis,
    ) -> bool:
        """
        Act on a reported conflict between two supported claims. True when one was recorded.

        The model supplies only the judgement that two statements are mutually exclusive.
        Everything that follows is computed here: which claims are affected, what status they
        take, and what confidence they carry. Both sides are weakened rather than one being
        picked, because the conflict establishes that they cannot both hold — not which of
        them is wrong. Choosing a winner on the model's say-so would be the loop asserting a
        finding no evidence supports.
        """
        other_id = proposal.contradicts_hypothesis_id
        # A contradiction is reported independently of an ordinary challenge, and in practice
        # arrives *with* a decline: once the claim has been critiqued and no tools are left,
        # the policy answers `should_challenge: false` with a null target and still names the
        # conflict. Requiring a target here dropped exactly the report this exists to catch.
        # The claim the critic was asked about is the other side of the pair by construction.
        target_id = proposal.target_hypothesis_id or asked_about.id
        if not other_id or other_id == target_id:
            return False

        target = state.find_hypothesis(target_id)
        other = state.find_hypothesis(other_id)
        # Only a live conflict counts. A claim already rejected or weakened is not being
        # asserted, so there is nothing to contradict.
        if target is None or other is None:
            return False
        # Both must still be asserted. This also dedupes: recording weakens the pair, so a
        # later call cannot re-fire on it unless fresh evidence restores both to supported —
        # at which point recording again is the right behaviour.
        if target.status is not HypothesisStatus.supported or other.status is not HypothesisStatus.supported:
            return False

        state.add_critique(Critique(
            id=idgen.make("crit", len(state.critiques)),
            critique_type=CritiqueType.contradiction,
            severity=CritiqueSeverity.major,
            target=EntityRef(kind=EntityKind.hypothesis, id=target.id),
            message=proposal.message or (
                f"'{target.statement}' and '{other.statement}' cannot both hold; "
                f"the evidence gathered so far supports each independently."
            ),
            suggested_action=proposal.falsification_tool,
            provenance=_prov("critic"),
        ))

        for claim in (target, other):
            conflicting = other if claim is target else target
            claim.set_status(HypothesisStatus.weakened)
            claim.set_confidence(round(min(claim.confidence, self.CONTRADICTION_CONFIDENCE_CAP), 4))
            state.record_decision(AgentDecision(
                id=idgen.make("dec-contra", len(state.decisions)),
                decision_type=DecisionType.revise_confidence,
                # The id of the conflicting claim goes in `targets`, where a reader can follow
                # it and a client can link it. A rationale is prose and is read as prose, so
                # naming the claim beats printing its primary key.
                rationale=f"weakened: cannot hold at the same time as {_quote(conflicting.statement)}",
                targets=[
                    EntityRef(kind=EntityKind.hypothesis, id=claim.id),
                    EntityRef(kind=EntityKind.hypothesis, id=conflicting.id),
                ],
                provenance=_prov("critic"),
            ))

        state.add_open_question(OpenQuestion(
            id=idgen.make("q-contra", len(state.open_questions)),
            question=f"Which of these holds, if either: '{target.statement}' or '{other.statement}'?",
            related_hypothesis_ids=[target.id, other.id],
            provenance=_prov("critic"),
        ))
        return True

    @staticmethod
    def _claim_to_challenge(state: InvestigationState) -> Hypothesis | None:
        """
        The claim most worth challenging, or ``None`` when nothing is.

        A ``supported`` claim comes first — guarding against false confidence is the critic's
        primary job, and this is the behaviour the agency suite's ``require_challenge``
        property measures.

        Failing that, a claim carrying **both** supporting and refuting evidence is challenged
        too. Mixed evidence is precisely where a competing explanation is informative: the loop
        has found the outcome moving and something arguing against it, and naming the
        alternative is what tells them apart. Restricting the critic to supported claims meant
        no run that ended inconclusive was ever challenged — the runs that most needed a second
        reading got none.

        A claim with no evidence, or one-sided evidence, is still left alone: there is nothing
        to weigh, so a critique would be a note rather than a challenge.
        """
        supported = [h for h in state.hypotheses if h.status is HypothesisStatus.supported]
        if supported:
            return max(supported, key=lambda x: x.confidence)

        mixed: list[Hypothesis] = []
        for h in state.hypotheses:
            if h.status in (HypothesisStatus.rejected, HypothesisStatus.unresolved):
                continue
            directions = {
                e.direction for e in state.evidence if h.id in e.hypothesis_ids
            }
            if EvidenceDirection.supports in directions and EvidenceDirection.refutes in directions:
                mixed.append(h)
        if not mixed:
            return None
        return max(mixed, key=lambda x: x.confidence)

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
        # Sufficiency means the *investigation* is done, not that one claim landed. Firing on the
        # first supported hypothesis leaves every other claim stranded at `proposed` — the same
        # single-metric bug this phase removes, relocated one step later.
        #
        # The bar is "nothing is still `proposed`", not `is_terminal()`. Only `rejected` is
        # terminal in the transition graph — a supported claim may still be weakened — so
        # requiring terminality would mean requiring every claim to be *rejected*. A claim past
        # `proposed` has had evidence brought to bear on it; one still at `proposed` has had
        # nothing run against it at all.
        if any(h.status is HypothesisStatus.proposed for h in state.hypotheses):
            return False, None

        # A live contradiction is disqualifying on its own. The loop is holding two claims
        # that cannot both be true, so whatever else it has established, it has not
        # established this — and reporting `sufficient_evidence` here would publish a
        # conclusion the run's own record refutes. Run the discriminating experiment if the
        # critic named one and it has not been tried; otherwise say so plainly.
        contradiction = self._unresolved_contradiction(state)
        if contradiction is not None:
            suggested = contradiction.suggested_action or ""
            if suggested and suggested not in executed_tools:
                return False, None
            return True, TerminationReason.insufficient_evidence

        supported = [h for h in state.hypotheses
                     if h.status is HypothesisStatus.supported and h.confidence >= self.SUFFICIENT_CONFIDENCE]
        if supported:
            # Every supported claim must have been challenged, or have no challenge left to run.
            # One claim surviving a falsification says nothing about the others.
            unused = [t for t in intent_tools if t not in executed_tools]
            for h in supported:
                crits = [c for c in state.critiques if c.target.id == h.id]
                tested = any((c.suggested_action or "") in executed_tools for c in crits)
                if not tested and unused:
                    return False, None
            return True, TerminationReason.sufficient_evidence
        return False, None

    @staticmethod
    def _unresolved_contradiction(state: InvestigationState) -> Critique | None:
        for c in state.critiques:
            if c.critique_type is CritiqueType.contradiction and not c.resolved:
                return c
        return None

    def finalize_no_candidates(self, state: InvestigationState, ran_any: bool) -> TerminationReason:
        # Checked before `supported`: running out of experiments does not settle a
        # contradiction, and a third claim standing does not make the conflicting pair go away.
        if self._unresolved_contradiction(state) is not None:
            return TerminationReason.insufficient_evidence
        # Same bar `decide` applies: a claim still at `proposed` has had nothing run against
        # it. Without this the two termination paths disagreed, and running out of candidate
        # experiments could report `sufficient_evidence` with a rival explanation untested —
        # a real run concluded "a genuine change rather than a seasonal artifact" at 0.95
        # while the seasonality claim it raised was never examined. Ruling out an alternative
        # the loop never tested is exactly the overreach this system exists to not commit.
        if any(h.status is HypothesisStatus.proposed for h in state.hypotheses):
            return TerminationReason.insufficient_evidence if ran_any else TerminationReason.no_valid_experiment
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
        self,
        state: InvestigationState,
        reason: TerminationReason,
        idgen: DeterministicIds,
        *,
        policy: object | None = None,
        question: str = "",
        tracker: BudgetTracker | None = None,
    ) -> Conclusion:
        supported = [h for h in state.hypotheses if h.status is HypothesisStatus.supported]
        rejected = [h for h in state.hypotheses if h.status is HypothesisStatus.rejected]
        weakened = [h for h in state.hypotheses if h.status is HypothesisStatus.weakened]

        # any still-active hypothesis is left explicitly unresolved
        for h in state.hypotheses:
            if h.status is HypothesisStatus.active:
                h.set_status(HypothesisStatus.unresolved)

        contradicting = [e.id for e in state.evidence if e.direction is EvidenceDirection.refutes]
        # `unresolved` counts as not-held. It is not a refutation, but reporting a run as
        # "supported" when half its claims could not be determined tells the user their whole
        # question was answered favourably, which is the more misleading of the two errors.
        unresolved = [h for h in state.hypotheses if h.status is HypothesisStatus.unresolved]
        opposed = rejected + weakened + unresolved
        if supported and opposed:
            # Checked before the `supported` branch on purpose. Falling through to it would
            # report a run that found one thing true and another false as simply "supported",
            # dropping the refutation from the headline and averaging its confidence away.
            disposition = ConclusionDisposition.mixed
            conf = round(
                sum(h.confidence for h in supported + opposed) / len(supported + opposed), 4
            )
            statement = (
                "Supported: " + "; ".join(h.statement for h in supported)
                + " | Not supported: " + "; ".join(h.statement for h in opposed)
            )
            hyp_ids = [h.id for h in supported + opposed]
            key_ev = [e.id for e in state.evidence]
        elif supported:
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
            narrative=self._narrate(state, policy, question, disposition, conf, reason, tracker),
            supporting_hypothesis_ids=hyp_ids, key_evidence_ids=key_ev, caveats=caveats,
            open_question_ids=[q.id for q in state.open_questions], provenance=_prov("conclusion_synthesizer"))
        state.set_conclusion(conclusion)
        state.record_decision(AgentDecision(
            id=idgen.make("dec-concl", len(state.decisions)), decision_type=DecisionType.conclude,
            rationale=f"{disposition.value} ({reason.value})",
            targets=[EntityRef(kind=EntityKind.conclusion, id=conclusion.id)], provenance=_prov("conclusion_synthesizer")))
        return conclusion

    @staticmethod
    def _narrate(
        state: InvestigationState,
        policy: object | None,
        question: str,
        disposition: ConclusionDisposition,
        confidence: float,
        reason: TerminationReason,
        tracker: BudgetTracker | None,
    ) -> str | None:
        """
        The finding as prose, when a policy can write one that survives verification.

        The findings handed over are already-computed values, and the check on the way back
        is what matters: a figure the run never recorded discards the whole narrative and
        the caller keeps its deterministic statement. Returning ``None`` is an ordinary
        outcome here, not a failure.
        """
        if policy is None:
            return None

        # Per-claim evidence, split by direction. A writer asked for more than a couple of
        # sentences needs something true to say in them; without this the only material is
        # the claim statements, and the extra length turns into padding or into figures the
        # run never produced.
        # Seeded at zero for every claim, not just the ones with evidence. A claim with
        # nothing against it genuinely has *zero* refuting items, and that is a fact the run
        # holds — leaving it out of the allowed set made "no refuting evidence" unsayable.
        supporting: dict[str, int] = {h.id: 0 for h in state.hypotheses}
        refuting: dict[str, int] = {h.id: 0 for h in state.hypotheses}
        for e in state.evidence:
            bucket = refuting if e.direction is EvidenceDirection.refutes else supporting
            for hid in e.hypothesis_ids:
                if hid in bucket:
                    bucket[hid] += 1

        claims = [
            {
                "statement": h.statement,
                "status": h.status.value,
                "confidence": h.confidence,
                "supporting_evidence": supporting.get(h.id, 0),
                "refuting_evidence": refuting.get(h.id, 0),
            }
            for h in state.hypotheses
        ]
        counts = {
            "hypotheses": len(state.hypotheses),
            "evidence": len(state.evidence),
            "experiments": len(state.completed_experiments),
            "supported": sum(1 for h in state.hypotheses if h.status is HypothesisStatus.supported),
            "open_questions": len(state.open_questions),
        }
        dataset = state.datasets[0] if state.datasets else None
        findings = {
            "disposition": disposition.value,
            "confidence": confidence,
            "claims": claims,
            "counts": counts,
            # What was actually run, and what the run refused to settle. Both are things a
            # reader wants and neither can be inferred from the claims alone.
            "experiments_run": [x.tool_name for x in state.completed_experiments],
            "stopped_because": reason.value,
            "open_questions": [q.question for q in state.open_questions],
            "dataset": (
                {"name": dataset.name, "row_count": dataset.row_count} if dataset else None
            ),
        }

        # Counted like every other policy call. Writing the answer is a real model call that
        # costs real money, and a budget that cannot see it reports a run as cheaper than it
        # was. It is recorded, never gated: the run is already over by the time this happens,
        # so refusing it here would only cost the answer, not save the spend.
        if tracker is not None:
            written = _invoke_policy(tracker, policy, lambda: narrate_answer(  # type: ignore[arg-type]
                policy, question=question, findings=findings))
        else:
            written = narrate_answer(policy, question=question, findings=findings)
        if written is None:
            return None

        # Every figure handed over is a figure the prose may state, and nothing else is.
        allowed = AllowedNumbers().add_many_counts(counts).add_confidence(confidence)
        for h in state.hypotheses:
            allowed.add_confidence(h.confidence)
        allowed.add_many_counts(supporting).add_many_counts(refuting)
        if dataset is not None:
            allowed.add_count(dataset.row_count)
        return verify_narrative(written, allowed)


def make_termination(reason: TerminationReason, state: InvestigationState, idgen: DeterministicIds) -> TerminationDecision:
    return TerminationDecision(
        should_stop=True, reason=reason,
        rationale=f"terminated: {reason.value}", at_iteration=state.budget.iterations_used,
        provenance=_prov("termination_policy"))
