"""
The agent observability seam.

:class:`InvestigationLoop` emits typed events at every decision boundary — run
start/end, each iteration, each of the ten components, experiment execution,
hypothesis transitions, and termination. The default observer is a no-op, so
``agentic`` keeps the zero-infrastructure-dependency purity required by
``docs/architecture/domain-boundaries.md``: nothing here imports structlog,
OpenTelemetry, or prometheus_client.

The backend subclasses :class:`AgentObserver` and overrides only the hooks it
cares about, translating events into spans, structured logs, and metrics.

Component and status labels are enums rather than free strings so downstream
metric label cardinality stays bounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from agentic.domain import HypothesisStatus, InvestigationStatus, TerminationReason


class LoopComponent(str, Enum):
    """The ten explicit loop components (see ``docs/agent/investigation-loop.md``)."""

    goal_interpreter = "goal_interpreter"
    hypothesis_generator = "hypothesis_generator"
    planner = "planner"
    selector = "selector"
    executor = "executor"
    evidence_updater = "evidence_updater"
    hypothesis_updater = "hypothesis_updater"
    critic = "critic"
    termination_policy = "termination_policy"
    conclusion_synthesizer = "conclusion_synthesizer"


# -- events ------------------------------------------------------------------


@dataclass(frozen=True)
class InvestigationStarted:
    investigation_id: str
    goal_text: str
    adapter_id: str
    dataset_name: str | None
    resumed: bool


@dataclass(frozen=True)
class InvestigationEnded:
    investigation_id: str
    status: InvestigationStatus
    termination_reason: TerminationReason | None
    iterations: int
    experiments_completed: int
    experiments_failed: int
    hypotheses: int
    evidence: int
    elapsed_seconds: float
    cost_usd: float
    model_calls: int
    #: True when the call returned without a terminal decision (bounded by
    #: ``max_new_experiments``) and the investigation remains resumable.
    partial: bool = False


@dataclass(frozen=True)
class IterationStarted:
    investigation_id: str
    iteration: int


@dataclass(frozen=True)
class IterationEnded:
    investigation_id: str
    iteration: int
    duration_seconds: float


@dataclass(frozen=True)
class ComponentCompleted:
    investigation_id: str
    component: LoopComponent
    duration_seconds: float
    #: Exception type name when the component raised, else ``None``.
    error: str | None = None


@dataclass(frozen=True)
class ExperimentObserved:
    investigation_id: str
    tool_name: str
    status: str
    duration_seconds: float
    evidence_produced: int = 0


@dataclass(frozen=True)
class HypothesisTransitioned:
    investigation_id: str
    hypothesis_id: str
    from_status: HypothesisStatus
    to_status: HypothesisStatus


@dataclass(frozen=True)
class TerminationObserved:
    investigation_id: str
    reason: TerminationReason
    iterations: int


@dataclass(frozen=True)
class ModelCallObserved:
    investigation_id: str
    component: LoopComponent
    cost_usd: float


# -- observer ----------------------------------------------------------------


class AgentObserver:
    """
    No-op observer. Subclass and override the hooks you need; every method has a
    default implementation so subclasses never have to implement the full surface.

    Implementations MUST NOT raise: the loop treats observation as best-effort and
    does not guard individual hook calls.
    """

    def on_investigation_start(self, event: InvestigationStarted) -> None:
        """Called once per ``start``/``resume`` call, before any component runs."""

    def on_investigation_end(self, event: InvestigationEnded) -> None:
        """Called once per call, including partial (resumable) and failed exits."""

    def on_iteration_start(self, event: IterationStarted) -> None: ...

    def on_iteration_end(self, event: IterationEnded) -> None: ...

    def on_component_completed(self, event: ComponentCompleted) -> None:
        """Called for every component invocation, including ones that raised."""

    def on_experiment(self, event: ExperimentObserved) -> None: ...

    def on_hypothesis_transition(self, event: HypothesisTransitioned) -> None: ...

    def on_termination(self, event: TerminationObserved) -> None: ...

    def on_model_call(self, event: ModelCallObserved) -> None: ...


NULL_OBSERVER = AgentObserver()
"""Process-wide default; observation is off unless an observer is injected."""


@dataclass
class RecordingObserver(AgentObserver):
    """Collects every event in order. For tests and local inspection."""

    events: list[object] = field(default_factory=list)

    def _record(self, event: object) -> None:
        self.events.append(event)

    on_investigation_start = _record  # type: ignore[assignment]
    on_investigation_end = _record  # type: ignore[assignment]
    on_iteration_start = _record  # type: ignore[assignment]
    on_iteration_end = _record  # type: ignore[assignment]
    on_component_completed = _record  # type: ignore[assignment]
    on_experiment = _record  # type: ignore[assignment]
    on_hypothesis_transition = _record  # type: ignore[assignment]
    on_termination = _record  # type: ignore[assignment]
    on_model_call = _record  # type: ignore[assignment]

    def of_type(self, event_type: type) -> list:
        """All recorded events of one type, in order."""
        return [e for e in self.events if isinstance(e, event_type)]
