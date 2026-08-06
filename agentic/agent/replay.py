"""
Replay a persisted investigation under different conditions.

An investigation persists everything needed to re-pose its question: the goal, the dataset
manifest, and (through :class:`~agentic.agent.ids.DeterministicIds`) an id scheme that is a
pure function of its seed. Replay re-runs that question — same goal, same manifest, same
seed — under a *different* policy, budget, or tool registry, and diffs the outcome.

This turns "we changed the model / the prompt / the budget" into an answerable question:
did the analysis actually change, or only the route to it?

What replay does **not** carry over is the data. Frames are materialized, never persisted,
so the caller supplies the frame. Replaying against different data is a legitimate use
(does the conclusion hold on a later period?) but it is the caller's explicit choice, and
:class:`ReplayResult` records the distinction.

Pure domain code: the caller owns loading the baseline and materializing the frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from agentic.domain import Investigation
from agentic.domain.manifest import DatasetManifest
from agentic.experiments import ArtifactSink, ExperimentRegistry

from .budget import LoopBudget, SafetyLimits
from .clock import Clock
from .diff import DiffVerdict, InvestigationDiff, diff_investigations
from .loop import InvestigationLoop
from .observer import AgentObserver
from .policy import AgentPolicy

#: Appended to the baseline id to label the replay. The child ids (hypotheses, experiments,
#: results) keep the baseline's seed so the two runs line up for comparison.
REPLAY_ID_SUFFIX = "::replay"


class ReplayNotPossible(RuntimeError):
    """The baseline lacks what replay needs (a goal, or a dataset manifest)."""


@dataclass(frozen=True)
class ReplayResult:
    """A replay and its comparison against the investigation it was replayed from."""

    baseline: Investigation
    candidate: Investigation
    diff: InvestigationDiff
    #: False when the caller supplied a frame other than the one the baseline ran on, so a
    #: divergence cannot be attributed to the policy change alone.
    same_dataset: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.diff.verdict is not DiffVerdict.identical

    def summary(self) -> str:
        line = self.diff.summary()
        return line if self.same_dataset else f"{line} (replayed against a different dataset)"


def baseline_goal(baseline: Investigation) -> str:
    goal = baseline.state.objective.objective
    if not goal:
        raise ReplayNotPossible(f"investigation {baseline.id} has no goal to replay")
    return goal


def baseline_manifest(baseline: Investigation) -> DatasetManifest:
    """The manifest the baseline ran against, recovered from its persisted state."""
    for dataset in baseline.state.datasets:
        if dataset.manifest is not None:
            return dataset.manifest
    raise ReplayNotPossible(
        f"investigation {baseline.id} has no persisted dataset manifest; it cannot be replayed"
    )


def replay_investigation(
    baseline: Investigation,
    *,
    frame: pd.DataFrame | None,
    policy: AgentPolicy | None = None,
    registry: ExperimentRegistry | None = None,
    budget: LoopBudget | None = None,
    safety: SafetyLimits | None = None,
    observer: AgentObserver | None = None,
    clock: Clock | None = None,
    artifact_sink: ArtifactSink | None = None,
    manifest: DatasetManifest | None = None,
    same_dataset: bool = True,
    replay_id: str | None = None,
) -> ReplayResult:
    """
    Re-run ``baseline``'s goal and manifest from scratch, then diff the two.

    The replay is a *fresh* run, not a resume: it starts from empty state so every decision
    is made again under the new conditions. It seeds ids from the baseline's id, which is
    what lines the two runs' hypotheses and experiments up for comparison, then relabels the
    finished candidate so it is a distinct investigation.

    Replay never takes an :class:`~agentic.agent.store.InvestigationStore`. Sharing the
    baseline's seed means a checkpointing run would overwrite the very investigation it is
    being compared against; persisting the candidate is the caller's decision, after it has
    been relabelled.

    Args:
        frame: the data to analyze. Not persisted with the investigation, so the caller
            must supply it; pass ``same_dataset=False`` when it is not the original data.
        manifest: overrides the baseline's persisted manifest (for replaying against a
            re-materialized dataset whose fingerprint differs).
        replay_id: id for the candidate; defaults to the baseline id plus ``::replay``.
    """
    goal = baseline_goal(baseline)
    resolved_manifest = manifest if manifest is not None else baseline_manifest(baseline)

    kwargs = {}
    if policy is not None:
        kwargs["policy"] = policy
    if registry is not None:
        kwargs["registry"] = registry
    if observer is not None:
        kwargs["observer"] = observer
    if clock is not None:
        kwargs["clock"] = clock
    if artifact_sink is not None:
        kwargs["artifact_sink"] = artifact_sink

    candidate = InvestigationLoop(**kwargs).start(
        goal,
        manifest=resolved_manifest,
        frame=frame,
        adapter_id=baseline.state.objective.adapter_id,
        budget=budget,
        safety=safety,
        # Same seed: child ids line up, so the diff can match hypotheses positionally.
        seed=baseline.id,
    )
    # Relabel once the run is finished. Child ids were already minted from the baseline
    # seed, so they still align while the candidate is its own investigation.
    candidate.id = replay_id or f"{baseline.id}{REPLAY_ID_SUFFIX}"

    notes: list[str] = []
    if frame is None:
        notes.append("replayed without a frame; experiments requiring data will degrade")
    if not same_dataset:
        notes.append("replayed against a different dataset than the baseline")

    return ReplayResult(
        baseline=baseline,
        candidate=candidate,
        diff=diff_investigations(baseline, candidate),
        same_dataset=same_dataset,
        notes=notes,
    )
