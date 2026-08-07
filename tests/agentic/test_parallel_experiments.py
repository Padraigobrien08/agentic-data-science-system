"""
Bounded parallel experiments within one loop iteration.

The loop can run several selected experiments concurrently, but the guarantee that
matters is that concurrency changes *when* work happens, never *what the state becomes*:
results are folded strictly in selection order, so ids, evidence, and hypothesis updates
stay a pure function of state no matter what order the batch finished in.

``max_parallel_experiments`` defaults to 1, so every existing run stays byte-for-byte
sequential unless it opts in.
"""

from __future__ import annotations

import threading
import time

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent import (
    InMemoryInvestigationStore,
    InvestigationLoop,
    LoopBudget,
    RecordingObserver,
)
from agentic.agent.observer import ExperimentObserved, InvestigationEnded, IterationStarted
from agentic.domain.enums import ColumnRole, ExperimentStatus

GOAL = "revenue is increasing over time"


def _frame(n: int = 8) -> pd.DataFrame:
    periods = [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)]
    return pd.DataFrame({"entity": ["A"] * n, "period": periods,
                         "revenue": [10.0 + 5.0 * i for i in range(n)]})


def _case():
    df = _frame()
    manifest = InMemoryDatasetAdapter(
        frame=df, time_field="period", entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest())
    return df, manifest


def _run(*, parallel: int = 1, seed: str = "par", observer=None, **budget_kwargs):
    df, manifest = _case()
    loop = InvestigationLoop(observer=observer) if observer else InvestigationLoop()
    return loop.start(
        GOAL, manifest=manifest, frame=df, seed=seed,
        budget=LoopBudget(max_parallel_experiments=parallel, **budget_kwargs),
        store=InMemoryInvestigationStore())


def _executed(inv) -> list[str]:
    return [r.tool_name for r in inv.state.completed_experiments + inv.state.failed_experiments]


def _fingerprint(inv) -> dict:
    """The parts of investigation state that must not depend on execution timing."""
    return {
        "tools": _executed(inv),
        "result_ids": [r.id for r in inv.state.completed_experiments + inv.state.failed_experiments],
        "evidence": [(e.id, e.claim, e.direction.value) for e in inv.state.evidence],
        "hypotheses": [(h.id, h.status.value, round(h.confidence, 6)) for h in inv.state.hypotheses],
        "termination": inv.state.termination.reason.value,
        "status": inv.status.value,
    }


# -- the default is unchanged ------------------------------------------------


def test_default_budget_is_sequential() -> None:
    assert LoopBudget().max_parallel_experiments == 1


def test_sequential_run_uses_no_worker_threads(monkeypatch) -> None:
    """A single-experiment batch must take the plain path — no pool, no sink wrapper."""
    created: list[object] = []
    import agentic.agent.loop as loop_module

    real_pool = loop_module.ThreadPoolExecutor

    def _spy(*args, **kwargs):
        created.append(kwargs)
        return real_pool(*args, **kwargs)

    monkeypatch.setattr(loop_module, "ThreadPoolExecutor", _spy)
    _run(parallel=1)
    assert created == [], "the sequential path must not spin up a thread pool"


# -- ordering is independent of completion order -----------------------------


def test_results_fold_in_selection_order_not_completion_order() -> None:
    """
    The core guarantee. Experiments are delayed so the batch finishes in reverse order;
    state must still reflect selection order.
    """
    df, manifest = _case()
    loop = InvestigationLoop()
    real_run = loop._executor.run
    # Delays keyed by tool name, not by call order: which thread starts first is undefined,
    # so a counter read inside the workers would itself be racy.
    delay_by_tool = {
        "analyze_time_series_trend": 0.15,
        "detect_change_points": 0.05,
        "summarize_distribution": 0.0,
    }
    order_finished: list[str] = []
    guard = threading.Lock()

    def _delayed_run(request, manifest_, frame_, *, sink=None):
        time.sleep(delay_by_tool.get(request.tool_name, 0.0))
        record = real_run(request, manifest_, frame_, sink=sink)
        with guard:
            order_finished.append(request.tool_name)
        return record

    loop._executor.run = _delayed_run  # type: ignore[method-assign]
    inv = loop.start(GOAL, manifest=manifest, frame=df, seed="order",
                     budget=LoopBudget(max_parallel_experiments=3, max_experiments=3),
                     store=InMemoryInvestigationStore())

    executed = _executed(inv)
    assert len(executed) >= 2
    # Completion is ordered by the injected delays, ascending.
    expected_completion = sorted(order_finished, key=lambda t: delay_by_tool.get(t, 0.0))
    assert order_finished == expected_completion, f"delays did not order completion: {order_finished}"
    # The delays must actually have reordered completion, or this proves nothing.
    assert order_finished != executed, (
        f"completion order was not shuffled; state={executed} finished={order_finished}"
    )
    # ...yet state follows selection order, which is the guarantee under test.
    assert executed == sorted(executed, key=lambda t: -delay_by_tool.get(t, 0.0)), (
        f"state order {executed} must follow selection order, not completion {order_finished}"
    )


def test_parallel_runs_are_reproducible() -> None:
    """Run-to-run determinism: same config, same resulting state."""
    first = _run(parallel=3, seed="repro")
    second = _run(parallel=3, seed="repro")
    assert _fingerprint(first) == _fingerprint(second)


def test_observer_reports_experiments_in_selection_order() -> None:
    observer = RecordingObserver()
    inv = _run(parallel=3, seed="obs", observer=observer)
    reported = [e.tool_name for e in observer.of_type(ExperimentObserved)]
    assert reported == _executed(inv)


# -- concurrency actually happens --------------------------------------------


def test_a_batch_runs_concurrently() -> None:
    """Wall time for the batch must be well below the sum of its parts."""
    df, manifest = _case()
    loop = InvestigationLoop()
    real_run = loop._executor.run
    sleep_s = 0.2
    concurrent = []
    active = {"n": 0}
    guard = threading.Lock()

    def _slow_run(request, manifest_, frame_, *, sink=None):
        with guard:
            active["n"] += 1
            concurrent.append(active["n"])
        time.sleep(sleep_s)
        try:
            return real_run(request, manifest_, frame_, sink=sink)
        finally:
            with guard:
                active["n"] -= 1

    loop._executor.run = _slow_run  # type: ignore[method-assign]
    started = time.perf_counter()
    loop.start(GOAL, manifest=manifest, frame=df, seed="conc",
               budget=LoopBudget(max_parallel_experiments=3, max_experiments=3),
               store=InMemoryInvestigationStore())
    elapsed = time.perf_counter() - started

    assert max(concurrent) > 1, "experiments did not overlap"
    assert elapsed < sleep_s * len(concurrent), (
        f"elapsed {elapsed:.2f}s suggests serial execution of {len(concurrent)} experiments"
    )


# -- batching respects every bound -------------------------------------------


def test_batch_never_overshoots_the_experiment_budget() -> None:
    inv = _run(parallel=5, max_experiments=2, seed="cap")
    assert len(_executed(inv)) <= 2


def test_batch_never_overshoots_the_partial_run_window() -> None:
    df, manifest = _case()
    inv = InvestigationLoop().start(
        GOAL, manifest=manifest, frame=df, seed="window",
        budget=LoopBudget(max_parallel_experiments=5), max_new_experiments=2,
        store=InMemoryInvestigationStore())
    assert len(_executed(inv)) <= 2
    assert not inv.is_terminal(), "a bounded call stays resumable"


def test_a_wider_batch_runs_several_tools_in_one_iteration() -> None:
    """Count experiments per iteration directly, rather than inferring it from totals."""
    observer = RecordingObserver()
    _run(parallel=3, seed="wide", observer=observer)

    per_iteration: list[int] = []
    for event in observer.events:
        if isinstance(event, IterationStarted):
            per_iteration.append(0)
        elif isinstance(event, ExperimentObserved) and per_iteration:
            per_iteration[-1] += 1

    assert max(per_iteration) > 1, f"no iteration ran a batch; per-iteration counts {per_iteration}"


def test_sequential_config_runs_exactly_one_experiment_per_iteration() -> None:
    observer = RecordingObserver()
    _run(parallel=1, seed="one-each", observer=observer)

    per_iteration: list[int] = []
    for event in observer.events:
        if isinstance(event, IterationStarted):
            per_iteration.append(0)
        elif isinstance(event, ExperimentObserved) and per_iteration:
            per_iteration[-1] += 1

    assert set(per_iteration) <= {0, 1}, f"sequential mode batched: {per_iteration}"


def test_no_tool_repeats_within_a_batch() -> None:
    inv = _run(parallel=4, seed="norepeat")
    executed = _executed(inv)
    assert len(set(executed)) == len(executed), f"tools repeated: {executed}"


def test_resume_matches_an_uninterrupted_batched_run() -> None:
    """
    Resume determinism is a core loop invariant; batching must not weaken it. A run
    interrupted mid-batch and resumed must reach the same state as one that ran straight
    through with the same batch width.
    """
    df, manifest = _case()
    budget = LoopBudget(max_parallel_experiments=3)

    full = InvestigationLoop().start(
        GOAL, manifest=manifest, frame=df, seed="resume-batch",
        budget=budget, store=InMemoryInvestigationStore())

    store = InMemoryInvestigationStore()
    partial = InvestigationLoop().start(
        GOAL, manifest=manifest, frame=df, seed="resume-batch",
        budget=budget, store=store, max_new_experiments=2)
    assert partial.state.termination is None, "the partial call must stop mid-run"

    resumed = InvestigationLoop().resume(
        store.load(partial.id), goal_text=GOAL, manifest=manifest, frame=df,
        budget=budget, store=store)

    assert _fingerprint(resumed) == _fingerprint(full)


# -- the cost argument for batching ------------------------------------------


def test_wider_batches_cost_fewer_model_calls_per_experiment() -> None:
    """
    One selector call covers the whole batch, so widening it lowers model calls per
    experiment. This is the reason batching is worth its adaptivity trade-off.
    """
    sequential = RecordingObserver()
    batched = RecordingObserver()
    seq = _run(parallel=1, seed="cost", observer=sequential, max_experiments=4)
    par = _run(parallel=4, seed="cost", observer=batched, max_experiments=4)

    seq_end = sequential.of_type(InvestigationEnded)[-1]
    par_end = batched.of_type(InvestigationEnded)[-1]
    seq_ratio = seq_end.model_calls / max(1, len(_executed(seq)))
    par_ratio = par_end.model_calls / max(1, len(_executed(par)))
    assert par_ratio < seq_ratio, (
        f"batching should lower model calls per experiment: {par_ratio} vs {seq_ratio}"
    )


# -- failures inside a batch --------------------------------------------------


@pytest.mark.parametrize("parallel", [1, 3])
def test_a_raising_tool_behaves_the_same_batched_or_not(parallel: int) -> None:
    """
    Registry tools report failure through their record; *raising* is an internal error.
    Batching must not change how that surfaces — it propagates in both modes, so a bug in
    a tool can never be quietly swallowed by the thread pool.
    """
    df, manifest = _case()
    loop = InvestigationLoop()
    real_run = loop._executor.run

    def _boom(request, manifest_, frame_, *, sink=None):
        raise RuntimeError("tool exploded")

    loop._executor.run = _boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="tool exploded"):
        loop.start(GOAL, manifest=manifest, frame=df, seed=f"boom-{parallel}",
                   budget=LoopBudget(max_parallel_experiments=parallel, max_experiments=3),
                   store=InMemoryInvestigationStore())
    assert real_run is not None  # the real executor was never needed


#: Selected deterministically for this goal/fixture, so keying a test failure off the tool
#: name is stable — unlike a call counter, which races when the batch runs concurrently.
FAILING_TOOL = "detect_change_points"


def test_a_tool_reporting_failure_is_recorded_without_stopping_the_batch() -> None:
    """A record with status=failed is normal loop vocabulary and must fold like any other."""
    df, manifest = _case()
    loop = InvestigationLoop()
    real_run = loop._executor.run

    def _one_failure(request, manifest_, frame_, *, sink=None):
        # Keyed by tool name, not by call order: which thread runs first is not defined.
        record = real_run(request, manifest_, frame_, sink=sink)
        if request.tool_name == FAILING_TOOL:
            record.status = ExperimentStatus.failed
        return record

    loop._executor.run = _one_failure  # type: ignore[method-assign]
    inv = loop.start(GOAL, manifest=manifest, frame=df, seed="mixed",
                     budget=LoopBudget(max_parallel_experiments=3, max_experiments=3),
                     store=InMemoryInvestigationStore())

    failed = [r.tool_name for r in inv.state.failed_experiments]
    assert failed == [FAILING_TOOL], f"the failed experiment must be recorded, got {failed}"
    assert inv.state.completed_experiments, "its batch-mates must still have folded in"
    assert inv.is_terminal()
