"""
The adaptive investigation loop.

Wires the ten components, the deterministic experiment registry, and a checkpoint
store into a genuinely adaptive loop: goal interpretation and dataset capabilities
decide which experiments are candidates; intermediate results steer selection,
follow-ups, and critique; hypotheses are supported/weakened/rejected/left
unresolved; and the run stops for an explicit, typed reason before a conclusion is
synthesized. It is resumable: continuing a checkpointed run reproduces the same
subsequent state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from agentic.domain import (
    Investigation,
    InvestigationGoal,
    InvestigationState,
    InvestigationStatus,
    TerminationReason,
)
from agentic.domain.manifest import DatasetManifest
from agentic.experiments import ArtifactSink, ExperimentRegistry, build_default_registry

from .budget import BudgetTracker, LoopBudget, SafetyLimits
from .components import (
    EDGAR_INTENT_TOOLS,
    INTENT_TOOLS,
    ConclusionSynthesizer,
    Critic,
    EvidenceUpdater,
    ExperimentExecutor,
    ExperimentSelector,
    GoalInterpreter,
    HypothesisGenerator,
    HypothesisUpdater,
    InvestigationPlanner,
    TerminationPolicy,
    is_edgar_manifest,
    make_termination,
)
from .fixture_policy import FixtureAgentPolicy
from .ids import DeterministicIds
from .policy import AgentPolicy, AgentPolicyError, AnalysisIntent
from .store import InvestigationStore, NullInvestigationStore

_TERMINAL_STATUS = {
    TerminationReason.sufficient_evidence: InvestigationStatus.converged,
    TerminationReason.error: InvestigationStatus.failed,
    TerminationReason.safety_constraint: InvestigationStatus.failed,
}


@dataclass
class InvestigationLoop:
    """Runs an adaptive investigation over one manifest + materialized frame."""

    registry: ExperimentRegistry = field(default_factory=build_default_registry)
    policy: AgentPolicy = field(default_factory=FixtureAgentPolicy)
    # Optional shared sink: when set, every experiment emits into it so the emitted
    # artifact bytes survive the run and can be ingested + linked to their results.
    artifact_sink: ArtifactSink | None = None

    def __post_init__(self) -> None:
        self._interpreter = GoalInterpreter(self.policy)
        self._generator = HypothesisGenerator(self.policy)
        self._planner = InvestigationPlanner(self.registry)
        self._selector = ExperimentSelector(self.policy)
        self._executor = ExperimentExecutor(self.registry, artifact_sink=self.artifact_sink)
        self._evidence = EvidenceUpdater()
        self._hypotheses = HypothesisUpdater()
        self._critic = Critic(self.policy)
        self._termination = TerminationPolicy()
        self._synth = ConclusionSynthesizer()

    # -- public API ----------------------------------------------------------

    def start(
        self, goal_text: str, *, manifest: DatasetManifest, frame: pd.DataFrame | None = None,
        adapter_id: str = "generic", budget: LoopBudget | None = None, safety: SafetyLimits | None = None,
        store: InvestigationStore | None = None, seed: str | None = None,
        max_new_experiments: int | None = None, user_stop: bool = False,
    ) -> Investigation:
        goal = InvestigationGoal(objective=goal_text, adapter_id=adapter_id)
        inv = Investigation.start(goal)
        if seed is not None:
            inv.id = seed
        if manifest.dataset_reference_id is None:
            from agentic.domain import DatasetReference
            inv.state.datasets.append(DatasetReference(name=manifest.name, locator=manifest.fingerprint or manifest.name,
                                                       manifest=manifest))
        store = store or NullInvestigationStore()
        store.create(inv)
        tracker = BudgetTracker(budget=budget or LoopBudget(), safety=safety or SafetyLimits())
        return self._run(inv, goal_text=goal_text, manifest=manifest, frame=frame, tracker=tracker,
                         store=store, max_new_experiments=max_new_experiments, user_stop=user_stop)

    def resume(
        self, investigation: Investigation, *, goal_text: str, manifest: DatasetManifest,
        frame: pd.DataFrame | None = None, budget: LoopBudget | None = None,
        safety: SafetyLimits | None = None, store: InvestigationStore | None = None,
        max_new_experiments: int | None = None, user_stop: bool = False,
    ) -> Investigation:
        store = store or NullInvestigationStore()
        tracker = BudgetTracker(budget=budget or LoopBudget(), safety=safety or SafetyLimits())
        # rebuild resource counters from persisted state (resume-safe)
        tracker.experiments_used = len(investigation.state.completed_experiments) + len(investigation.state.failed_experiments)
        for r in [*investigation.state.completed_experiments, *investigation.state.failed_experiments]:
            tracker.tool_uses[r.tool_name] = tracker.tool_uses.get(r.tool_name, 0) + 1
        return self._run(investigation, goal_text=goal_text, manifest=manifest, frame=frame, tracker=tracker,
                         store=store, max_new_experiments=max_new_experiments, user_stop=user_stop)

    # -- core loop -----------------------------------------------------------

    def _run(
        self, inv: Investigation, *, goal_text: str, manifest: DatasetManifest, frame: pd.DataFrame | None,
        tracker: BudgetTracker, store: InvestigationStore, max_new_experiments: int | None, user_stop: bool,
    ) -> Investigation:
        idgen = DeterministicIds(inv.id)
        state = inv.state
        try:
            interpretation = self._interpreter.interpret(goal_text, manifest, tracker)
        except AgentPolicyError:
            return self._fail_safe(inv, state, idgen, store, TerminationReason.error)

        # initial phase runs once (skipped on resume)
        if not state.hypotheses:
            try:
                self._generator.generate(interpretation, state, manifest, idgen, tracker)
            except AgentPolicyError:
                return self._fail_safe(inv, state, idgen, store, TerminationReason.error)
            inv.set_status(InvestigationStatus.planning)
            inv.set_status(InvestigationStatus.running)
            store.save(inv)
        elif inv.status is InvestigationStatus.created:
            inv.set_status(InvestigationStatus.planning)
            inv.set_status(InvestigationStatus.running)

        intent_tools = self._intent_tools(interpretation.intent, manifest)
        experiments_this_call = 0

        while state.termination is None:
            executed_tools = {r.tool_name for r in [*state.completed_experiments, *state.failed_experiments]}
            stop, reason = self._termination.decide(
                state, tracker, state.budget.iterations_used,
                executed_tools=executed_tools, intent_tools=intent_tools, user_stop=user_stop)
            if stop:
                return self._finalize(inv, state, idgen, store, reason)

            if max_new_experiments is not None and experiments_this_call >= max_new_experiments:
                store.save(inv)
                return inv  # partial (not terminal); resumable

            try:
                candidates = self._planner.candidates(state, interpretation, manifest, executed_tools, tracker, idgen)
                chosen = self._selector.select(state, candidates, interpretation, tracker, idgen)
            except AgentPolicyError:
                return self._fail_safe(inv, state, idgen, store, TerminationReason.error)

            if chosen is None:
                reason = self._termination.finalize_no_candidates(state, ran_any=tracker.experiments_used > 0)
                return self._finalize(inv, state, idgen, store, reason)

            record = self._executor.execute(chosen, manifest, frame, idgen, state)
            failed = record.status.value == "failed"
            tracker.record_experiment(chosen.tool_name, failed=failed)
            experiments_this_call += 1

            if not failed:
                self._evidence.update(state, record, chosen, idgen)
                self._hypotheses.update(state, chosen, idgen)
                try:
                    self._critic.challenge(state, interpretation, manifest,
                                           executed_tools | {chosen.tool_name}, tracker, idgen)
                except AgentPolicyError:
                    return self._fail_safe(inv, state, idgen, store, TerminationReason.error)

            state.advance_iteration()
            store.save(inv)

        return inv

    # -- helpers -------------------------------------------------------------

    def _intent_tools(self, intent: AnalysisIntent, manifest: DatasetManifest) -> list[str]:
        tools = list(INTENT_TOOLS.get(intent, INTENT_TOOLS[AnalysisIntent.general]))
        if is_edgar_manifest(manifest):
            tools = EDGAR_INTENT_TOOLS.get(intent, []) + tools
        return tools

    def _finalize(self, inv: Investigation, state: InvestigationState, idgen: DeterministicIds,
                  store: InvestigationStore, reason: TerminationReason) -> Investigation:
        self._synth.synthesize(state, reason, idgen)
        state.record_termination(make_termination(reason, state, idgen))
        inv.set_status(_TERMINAL_STATUS.get(reason, InvestigationStatus.exhausted))
        store.save(inv)
        return inv

    def _fail_safe(self, inv: Investigation, state: InvestigationState, idgen: DeterministicIds,
                   store: InvestigationStore, reason: TerminationReason) -> Investigation:
        """Malformed model output / internal error -> terminate safely with a conclusion."""
        if state.termination is None:
            self._synth.synthesize(state, reason, idgen)
            state.record_termination(make_termination(reason, state, idgen))
        if inv.status not in (InvestigationStatus.converged, InvestigationStatus.exhausted, InvestigationStatus.failed):
            # created -> planning -> running -> failed (respect the transition graph)
            if inv.status is InvestigationStatus.created:
                inv.set_status(InvestigationStatus.planning)
            if inv.status is InvestigationStatus.planning:
                inv.set_status(InvestigationStatus.running)
            inv.set_status(InvestigationStatus.failed)
        store.save(inv)
        return inv


def run_investigation(goal_text: str, *, manifest: DatasetManifest, frame: pd.DataFrame | None = None, **kwargs) -> Investigation:
    """Convenience: run a fresh investigation to termination with default components."""
    return InvestigationLoop().start(goal_text, manifest=manifest, frame=frame, **kwargs)
