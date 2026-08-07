"""
Backend implementation of the agentic loop's observability seam.

Turns the typed events emitted by :class:`agentic.agent.observer.AgentObserver`
into the three signals the rest of the platform already speaks:

* **Traces** — a span tree ``agent.investigation → agent.iteration.N →
  agent.component.{name}``, nested under whatever span the run driver is already in,
  so an investigation reads as a flame graph of the agent deciding.
* **Structured logs** — one event per notable decision, with the investigation and
  run bound as context. Component-level events log at debug (ten per iteration).
* **Metrics** — the ``edgar_agent_*`` families in :mod:`backend.observability.metrics`.

The loop treats observation as best-effort and does not guard hook calls, so every
hook here is wrapped: a tracing or metrics failure degrades observability rather than
failing an investigation.

Component spans are created retroactively from the event's measured duration
(``start_time = end - duration``) because the loop reports component completion rather
than yielding a context manager — this keeps ``agentic/`` free of any tracing dependency.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog
from opentelemetry import trace

from agentic.agent.observer import (
    AgentObserver,
    ComponentCompleted,
    ExperimentObserved,
    HypothesisTransitioned,
    InvestigationEnded,
    InvestigationStarted,
    IterationEnded,
    IterationStarted,
    ModelCallObserved,
    TerminationObserved,
)
from backend.observability.metrics import (
    AGENT_COMPONENT_DURATION_SECONDS,
    AGENT_COMPONENT_ERRORS_TOTAL,
    AGENT_COST_USD_TOTAL,
    AGENT_EXPERIMENT_DURATION_SECONDS,
    AGENT_EXPERIMENTS_TOTAL,
    AGENT_HYPOTHESIS_TRANSITIONS_TOTAL,
    AGENT_INVESTIGATION_DURATION_SECONDS,
    AGENT_INVESTIGATION_ITERATIONS,
    AGENT_INVESTIGATIONS_TOTAL,
    AGENT_MODEL_CALLS_TOTAL,
    AGENT_TERMINATIONS_TOTAL,
)
from backend.observability.tracing import get_tracer

log = structlog.get_logger(__name__)

_F = TypeVar("_F", bound=Callable[..., None])

#: Goal text is free-form user input; cap it so spans and logs stay bounded.
_GOAL_ATTR_MAX = 256


def _never_raises(fn: _F) -> _F:
    """Observation must never fail a run (the loop does not guard hook calls)."""

    @functools.wraps(fn)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        try:
            fn(self, *args, **kwargs)
        except Exception:  # noqa: BLE001 - boundary: observability must not break execution
            log.warning("agent_observer_hook_failed", hook=fn.__name__, exc_info=True)

    return wrapper  # type: ignore[return-value]


class BackendAgentObserver(AgentObserver):
    """
    Traces, logs, and metrics for one investigation loop call.

    Not thread-safe and not reusable across concurrent investigations: the run driver
    constructs one per ``start``/``resume`` call, matching the loop's synchronous shape.
    """

    def __init__(self, *, analysis_run_id: str | None = None) -> None:
        self._tracer = get_tracer("backend.agentic.loop")
        self._analysis_run_id = analysis_run_id
        self._investigation_span: trace.Span | None = None
        self._iteration_span: trace.Span | None = None
        self._log = log.bind(analysis_run_id=analysis_run_id) if analysis_run_id else log

    # -- span plumbing -------------------------------------------------------

    def _parent_context(self) -> Any:
        """Component spans hang off the current iteration, else the investigation."""
        parent = self._iteration_span or self._investigation_span
        return trace.set_span_in_context(parent) if parent is not None else None

    def _retro_span(
        self, name: str, duration_seconds: float, attributes: dict[str, Any], *, error: str | None = None,
    ) -> None:
        """A span for work that already happened, sized from its measured duration."""
        end_ns = time.time_ns()
        start_ns = end_ns - max(0, int(duration_seconds * 1_000_000_000))
        span = self._tracer.start_span(
            name, context=self._parent_context(), start_time=start_ns, attributes=attributes,
        )
        # Status must be set while the span is still open.
        if error is not None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        span.end(end_time=end_ns)

    def _close_iteration_span(self) -> None:
        if self._iteration_span is not None:
            self._iteration_span.end()
            self._iteration_span = None

    # -- investigation lifecycle --------------------------------------------

    @_never_raises
    def on_investigation_start(self, event: InvestigationStarted) -> None:
        self._investigation_span = self._tracer.start_span(
            "agent.investigation",
            attributes={
                "agent.investigation.id": event.investigation_id,
                "agent.adapter.id": event.adapter_id,
                "agent.dataset.name": event.dataset_name or "",
                "agent.goal": event.goal_text[:_GOAL_ATTR_MAX],
                "agent.resumed": event.resumed,
            },
        )
        self._log.info(
            "agent_investigation_started",
            investigation_id=event.investigation_id,
            adapter_id=event.adapter_id,
            dataset=event.dataset_name,
            resumed=event.resumed,
        )

    @_never_raises
    def on_investigation_end(self, event: InvestigationEnded) -> None:
        # The loop returns from inside an iteration when it terminates, so the last
        # iteration span is still open. Close it first, or its children (notably the
        # conclusion synthesizer) are never exported.
        self._close_iteration_span()
        status = event.status.value
        reason = event.termination_reason.value if event.termination_reason is not None else "none"

        # A partial call is a resumable pause, not a terminal outcome: it must not be
        # counted as an investigation reaching a terminal status.
        if not event.partial:
            AGENT_INVESTIGATIONS_TOTAL.labels(status=status, termination_reason=reason).inc()
            AGENT_INVESTIGATION_ITERATIONS.observe(event.iterations)
        AGENT_INVESTIGATION_DURATION_SECONDS.labels(status=status).observe(event.elapsed_seconds)

        if self._investigation_span is not None:
            self._investigation_span.set_attributes({
                "agent.status": status,
                "agent.termination.reason": reason,
                "agent.iterations": event.iterations,
                "agent.experiments.completed": event.experiments_completed,
                "agent.experiments.failed": event.experiments_failed,
                "agent.hypotheses": event.hypotheses,
                "agent.evidence": event.evidence,
                "agent.model_calls": event.model_calls,
                "agent.cost_usd": event.cost_usd,
                "agent.partial": event.partial,
            })
            self._investigation_span.end()
            self._investigation_span = None

        self._log.info(
            "agent_investigation_ended",
            investigation_id=event.investigation_id,
            status=status,
            termination_reason=reason,
            iterations=event.iterations,
            experiments_completed=event.experiments_completed,
            experiments_failed=event.experiments_failed,
            hypotheses=event.hypotheses,
            evidence=event.evidence,
            model_calls=event.model_calls,
            cost_usd=round(event.cost_usd, 6),
            elapsed_seconds=round(event.elapsed_seconds, 3),
            partial=event.partial,
        )

    # -- iterations ----------------------------------------------------------

    @_never_raises
    def on_iteration_start(self, event: IterationStarted) -> None:
        self._iteration_span = self._tracer.start_span(
            f"agent.iteration.{event.iteration}",
            context=(trace.set_span_in_context(self._investigation_span)
                     if self._investigation_span is not None else None),
            attributes={"agent.iteration": event.iteration},
        )

    @_never_raises
    def on_iteration_end(self, event: IterationEnded) -> None:
        self._close_iteration_span()
        self._log.debug(
            "agent_iteration_completed",
            investigation_id=event.investigation_id,
            iteration=event.iteration,
            duration_seconds=round(event.duration_seconds, 4),
        )

    # -- components ----------------------------------------------------------

    @_never_raises
    def on_component_completed(self, event: ComponentCompleted) -> None:
        component = event.component.value
        AGENT_COMPONENT_DURATION_SECONDS.labels(component=component).observe(event.duration_seconds)

        attributes: dict[str, Any] = {"agent.component": component}
        if event.error is not None:
            attributes["agent.error_type"] = event.error
            AGENT_COMPONENT_ERRORS_TOTAL.labels(component=component, error_type=event.error).inc()

        self._retro_span(f"agent.component.{component}", event.duration_seconds, attributes,
                         error=event.error)
        if event.error is not None:
            self._log.warning(
                "agent_component_failed",
                investigation_id=event.investigation_id,
                component=component,
                error_type=event.error,
            )
        else:
            self._log.debug(
                "agent_component_completed",
                investigation_id=event.investigation_id,
                component=component,
                duration_seconds=round(event.duration_seconds, 4),
            )

    # -- experiments, hypotheses, model calls, termination -------------------

    @_never_raises
    def on_experiment(self, event: ExperimentObserved) -> None:
        AGENT_EXPERIMENTS_TOTAL.labels(tool_name=event.tool_name, status=event.status).inc()
        AGENT_EXPERIMENT_DURATION_SECONDS.labels(tool_name=event.tool_name).observe(event.duration_seconds)
        self._log.info(
            "agent_experiment_executed",
            investigation_id=event.investigation_id,
            tool_name=event.tool_name,
            status=event.status,
            evidence_produced=event.evidence_produced,
            duration_seconds=round(event.duration_seconds, 4),
        )

    @_never_raises
    def on_hypothesis_transition(self, event: HypothesisTransitioned) -> None:
        AGENT_HYPOTHESIS_TRANSITIONS_TOTAL.labels(
            from_status=event.from_status.value, to_status=event.to_status.value
        ).inc()
        self._log.info(
            "agent_hypothesis_transition",
            investigation_id=event.investigation_id,
            hypothesis_id=event.hypothesis_id,
            from_status=event.from_status.value,
            to_status=event.to_status.value,
        )

    @_never_raises
    def on_model_call(self, event: ModelCallObserved) -> None:
        component = event.component.value
        AGENT_MODEL_CALLS_TOTAL.labels(component=component).inc()
        if event.cost_usd > 0:
            AGENT_COST_USD_TOTAL.labels(component=component).inc(event.cost_usd)

    @_never_raises
    def on_termination(self, event: TerminationObserved) -> None:
        AGENT_TERMINATIONS_TOTAL.labels(reason=event.reason.value).inc()
        self._log.info(
            "agent_terminated",
            investigation_id=event.investigation_id,
            reason=event.reason.value,
            iterations=event.iterations,
        )
