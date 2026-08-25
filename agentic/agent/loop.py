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

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field

import pandas as pd

from agentic.domain import (
    ExperimentRequest,
    Investigation,
    InvestigationGoal,
    InvestigationState,
    InvestigationStatus,
    TerminationReason,
)
from agentic.domain.manifest import DatasetManifest
from agentic.experiments import ArtifactSink, ExperimentRegistry, build_default_registry
from agentic.experiments.record import ExperimentExecutionRecord

from .budget import BudgetTracker, LoopBudget, SafetyLimits
from .clock import Clock, MonotonicClock
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
    LockedArtifactSink,
    TerminationPolicy,
    is_edgar_manifest,
    make_termination,
)
from .fixture_policy import FixtureAgentPolicy
from .ids import DeterministicIds
from .observer import (
    NULL_OBSERVER,
    AgentObserver,
    ComponentCompleted,
    ExperimentObserved,
    HypothesisTransitioned,
    InvestigationEnded,
    InvestigationStarted,
    IterationEnded,
    IterationStarted,
    LoopComponent,
    ModelCallObserved,
    TerminationObserved,
)
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
    # Observation is off by default; the backend injects a real observer that turns
    # these events into spans, structured logs, and metrics.
    observer: AgentObserver = NULL_OBSERVER
    # Injected so elapsed-time budgets and component timings stay deterministic in tests.
    clock: Clock = field(default_factory=MonotonicClock)

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
                         store=store, max_new_experiments=max_new_experiments, user_stop=user_stop,
                         resumed=False)

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
                         store=store, max_new_experiments=max_new_experiments, user_stop=user_stop,
                         resumed=True)

    # -- core loop -----------------------------------------------------------

    def _run(
        self, inv: Investigation, *, goal_text: str, manifest: DatasetManifest, frame: pd.DataFrame | None,
        tracker: BudgetTracker, store: InvestigationStore, max_new_experiments: int | None, user_stop: bool,
        resumed: bool,
    ) -> Investigation:
        idgen = DeterministicIds(inv.id)
        state = inv.state
        started_at = self.clock.monotonic()
        self.observer.on_investigation_start(InvestigationStarted(
            investigation_id=inv.id, goal_text=goal_text, adapter_id=state.objective.adapter_id,
            dataset_name=manifest.name, resumed=resumed))

        try:
            with self._timed(inv.id, LoopComponent.goal_interpreter, tracker):
                interpretation = self._interpreter.interpret(goal_text, manifest, tracker)
        except AgentPolicyError:
            return self._fail_safe(inv, state, idgen, store, TerminationReason.error, tracker, started_at)

        # initial phase runs once (skipped on resume)
        if not state.hypotheses:
            try:
                with self._timed(inv.id, LoopComponent.hypothesis_generator, tracker):
                    self._generator.generate(interpretation, state, manifest, idgen, tracker)
            except AgentPolicyError:
                return self._fail_safe(inv, state, idgen, store, TerminationReason.error, tracker, started_at)
            inv.set_status(InvestigationStatus.planning)
            inv.set_status(InvestigationStatus.running)
            store.save(inv)
        elif inv.status is InvestigationStatus.created:
            inv.set_status(InvestigationStatus.planning)
            inv.set_status(InvestigationStatus.running)

        intent_tools = self._intent_tools(interpretation.intent, manifest)
        experiments_this_call = 0

        while state.termination is None:
            iteration = state.budget.iterations_used
            iteration_started_at = self.clock.monotonic()
            # Refresh elapsed before the limit check so time-based budgets and safety
            # caps are evaluated against real wall time.
            tracker.elapsed_seconds = iteration_started_at - started_at
            self.observer.on_iteration_start(IterationStarted(investigation_id=inv.id, iteration=iteration))

            executed_tools = {r.tool_name for r in [*state.completed_experiments, *state.failed_experiments]}
            with self._timed(inv.id, LoopComponent.termination_policy):
                stop, reason = self._termination.decide(
                    state, tracker, iteration,
                    executed_tools=executed_tools, intent_tools=intent_tools, user_stop=user_stop)
            if stop:
                return self._finalize(inv, state, idgen, store, reason, tracker, started_at)

            if max_new_experiments is not None and experiments_this_call >= max_new_experiments:
                store.save(inv)
                self._emit_end(inv, state, tracker, started_at, partial=True)
                return inv  # partial (not terminal); resumable

            batch_limit = self._batch_limit(tracker, max_new_experiments, experiments_this_call)
            try:
                with self._timed(inv.id, LoopComponent.planner):
                    candidates = self._planner.candidates(state, interpretation, manifest, executed_tools, tracker, idgen)
                with self._timed(inv.id, LoopComponent.selector, tracker):
                    batch = self._selector.select_batch(
                        state, candidates, interpretation, tracker, idgen, limit=batch_limit)
            except AgentPolicyError:
                return self._fail_safe(inv, state, idgen, store, TerminationReason.error, tracker, started_at)

            if not batch:
                reason = self._termination.finalize_no_candidates(state, ran_any=tracker.experiments_used > 0)
                return self._finalize(inv, state, idgen, store, reason, tracker, started_at)

            with self._timed(inv.id, LoopComponent.executor):
                outcomes = self._run_batch(batch, manifest, frame)

            any_succeeded = False
            for chosen, record, execution_seconds in outcomes:
                failed = record.status.value == "failed"
                tracker.record_experiment(chosen.tool_name, failed=failed)
                experiments_this_call += 1
                # Folded strictly in selection order, so result ids and evidence remain a pure
                # function of state regardless of the order the batch finished in.
                self._executor.record(record, chosen, idgen, state)

                evidence_produced = 0
                if not failed:
                    any_succeeded = True
                    with self._timed(inv.id, LoopComponent.evidence_updater):
                        evidence_produced = len(self._evidence.update(state, record, chosen, idgen))
                    # Snapshot before/after so genuine status changes are observable without
                    # the components themselves needing to know about observation.
                    before = {h.id: h.status for h in state.hypotheses}
                    with self._timed(inv.id, LoopComponent.hypothesis_updater):
                        self._hypotheses.update(state, chosen, idgen)
                    self._emit_hypothesis_transitions(inv.id, before, state)

                self.observer.on_experiment(ExperimentObserved(
                    investigation_id=inv.id, tool_name=chosen.tool_name, status=record.status.value,
                    duration_seconds=execution_seconds, evidence_produced=evidence_produced))

            if any_succeeded:
                try:
                    with self._timed(inv.id, LoopComponent.critic, tracker):
                        self._critic.challenge(state, interpretation, manifest,
                                               executed_tools | {b.tool_name for b in batch},
                                               tracker, idgen)
                except AgentPolicyError:
                    return self._fail_safe(inv, state, idgen, store, TerminationReason.error, tracker, started_at)

            state.advance_iteration()
            store.save(inv)
            self.observer.on_iteration_end(IterationEnded(
                investigation_id=inv.id, iteration=iteration,
                duration_seconds=self.clock.monotonic() - iteration_started_at))

        self._emit_end(inv, state, tracker, started_at)
        return inv

    # -- batch execution -----------------------------------------------------

    @staticmethod
    def _batch_limit(
        tracker: BudgetTracker, max_new_experiments: int | None, experiments_this_call: int,
    ) -> int:
        """How many experiments this iteration may start, respecting every active bound.

        A batch must never overshoot ``max_experiments`` or the caller's
        ``max_new_experiments`` window, so the width is clamped by whatever budget is left.
        """
        limit = max(1, tracker.budget.max_parallel_experiments)
        remaining_budget = tracker.budget.max_experiments - tracker.experiments_used
        limit = min(limit, max(1, remaining_budget))
        if max_new_experiments is not None:
            remaining_call = max_new_experiments - experiments_this_call
            limit = min(limit, max(1, remaining_call))
        return limit

    def _run_batch(
        self, batch: list[ExperimentRequest], manifest: DatasetManifest, frame: pd.DataFrame | None,
    ) -> list[tuple[ExperimentRequest, ExperimentExecutionRecord, float]]:
        """
        Run a selected batch and return outcomes **in selection order**, each with its own
        measured duration.

        A single-experiment batch takes the sequential path verbatim — no threads, no shared
        sink wrapper — so the default configuration behaves exactly as it did before batching
        existed. Wider batches run concurrently; the deterministic tools are pure over the
        frame, and the shared artifact sink is serialized behind a lock.
        """
        if len(batch) == 1:
            request = batch[0]
            started = self.clock.monotonic()
            record = self._executor.run(request, manifest, frame)
            return [(request, record, self.clock.monotonic() - started)]

        shared = self._executor.shared_sink
        sink = LockedArtifactSink(shared) if shared is not None else None

        def _run(request: ExperimentRequest) -> tuple[ExperimentExecutionRecord, float]:
            started = self.clock.monotonic()
            record = self._executor.run(request, manifest, frame, sink=sink)
            return record, self.clock.monotonic() - started

        with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix="agentic-exp") as pool:
            # Results are collected by index, not completion, so ordering is deterministic.
            futures = [pool.submit(_run, request) for request in batch]
            outcomes = []
            for request, future in zip(batch, futures):
                record, duration = future.result()
                outcomes.append((request, record, duration))
        return outcomes

    # -- observation helpers -------------------------------------------------

    @contextmanager
    def _timed(
        self, investigation_id: str, component: LoopComponent, tracker: BudgetTracker | None = None,
    ) -> Iterator[None]:
        """
        Time one component invocation and report it, including on failure.

        When ``tracker`` is supplied the component is model-backed: the tracker is
        diffed across the call to report model calls and their cost, so the components
        themselves stay free of observation concerns.
        """
        started = self.clock.monotonic()
        calls_before = tracker.model_calls_used if tracker is not None else 0
        cost_before = tracker.cost_used_usd if tracker is not None else 0.0
        error: str | None = None
        try:
            yield
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            self.observer.on_component_completed(ComponentCompleted(
                investigation_id=investigation_id, component=component,
                duration_seconds=self.clock.monotonic() - started, error=error))
            if tracker is not None and tracker.model_calls_used > calls_before:
                self.observer.on_model_call(ModelCallObserved(
                    investigation_id=investigation_id, component=component,
                    cost_usd=tracker.cost_used_usd - cost_before))

    def _emit_hypothesis_transitions(
        self, investigation_id: str, before: dict[str, object], state: InvestigationState,
    ) -> None:
        for h in state.hypotheses:
            prior = before.get(h.id)
            if prior is not None and prior != h.status:
                self.observer.on_hypothesis_transition(HypothesisTransitioned(
                    investigation_id=investigation_id, hypothesis_id=h.id,
                    from_status=prior, to_status=h.status))  # type: ignore[arg-type]

    def _emit_end(
        self, inv: Investigation, state: InvestigationState, tracker: BudgetTracker,
        started_at: float, *, partial: bool = False,
    ) -> None:
        tracker.elapsed_seconds = self.clock.monotonic() - started_at
        self.observer.on_investigation_end(InvestigationEnded(
            investigation_id=inv.id, status=inv.status,
            termination_reason=state.termination.reason if state.termination is not None else None,
            iterations=state.budget.iterations_used,
            experiments_completed=len(state.completed_experiments),
            experiments_failed=len(state.failed_experiments),
            hypotheses=len(state.hypotheses), evidence=len(state.evidence),
            elapsed_seconds=tracker.elapsed_seconds, cost_usd=tracker.cost_used_usd,
            model_calls=tracker.model_calls_used, partial=partial))

    # -- helpers -------------------------------------------------------------

    def _intent_tools(self, intent: AnalysisIntent, manifest: DatasetManifest) -> list[str]:
        tools = list(INTENT_TOOLS.get(intent, INTENT_TOOLS[AnalysisIntent.general]))
        if is_edgar_manifest(manifest):
            tools = EDGAR_INTENT_TOOLS.get(intent, []) + tools
        return tools

    def _finalize(self, inv: Investigation, state: InvestigationState, idgen: DeterministicIds,
                  store: InvestigationStore, reason: TerminationReason,
                  tracker: BudgetTracker, started_at: float) -> Investigation:
        with self._timed(inv.id, LoopComponent.conclusion_synthesizer):
            self._synth.synthesize(
                state, reason, idgen,
                policy=self.policy, question=state.objective.objective, tracker=tracker,
            )
        state.record_termination(make_termination(reason, state, idgen))
        inv.set_status(_TERMINAL_STATUS.get(reason, InvestigationStatus.exhausted))
        store.save(inv)
        self.observer.on_termination(TerminationObserved(
            investigation_id=inv.id, reason=reason, iterations=state.budget.iterations_used))
        self._emit_end(inv, state, tracker, started_at)
        return inv

    def _fail_safe(self, inv: Investigation, state: InvestigationState, idgen: DeterministicIds,
                   store: InvestigationStore, reason: TerminationReason,
                   tracker: BudgetTracker, started_at: float) -> Investigation:
        """Malformed model output / internal error -> terminate safely with a conclusion."""
        if state.termination is None:
            with self._timed(inv.id, LoopComponent.conclusion_synthesizer):
                self._synth.synthesize(
                    state, reason, idgen,
                    policy=self.policy, question=state.objective.objective, tracker=tracker,
                )
            state.record_termination(make_termination(reason, state, idgen))
        if inv.status not in (InvestigationStatus.converged, InvestigationStatus.exhausted, InvestigationStatus.failed):
            # created -> planning -> running -> failed (respect the transition graph)
            if inv.status is InvestigationStatus.created:
                inv.set_status(InvestigationStatus.planning)
            if inv.status is InvestigationStatus.planning:
                inv.set_status(InvestigationStatus.running)
            inv.set_status(InvestigationStatus.failed)
        store.save(inv)
        self.observer.on_termination(TerminationObserved(
            investigation_id=inv.id, reason=reason, iterations=state.budget.iterations_used))
        self._emit_end(inv, state, tracker, started_at)
        return inv


def run_investigation(goal_text: str, *, manifest: DatasetManifest, frame: pd.DataFrame | None = None, **kwargs) -> Investigation:
    """Convenience: run a fresh investigation to termination with default components."""
    return InvestigationLoop().start(goal_text, manifest=manifest, frame=frame, **kwargs)
