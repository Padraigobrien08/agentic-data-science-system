"""
Replay a persisted analysis run's investigation and diff the outcome.

Turns "we changed the model / prompt / budget" into an answerable question against real
persisted runs: re-pose the same goal over the same data under new conditions, and report
whether the analysis changed or only the route to it.

The defining constraint is that a replay must compare like with like. Re-fetching from the
SEC would silently change the data underneath the comparison, so this service reuses the
**exact panel the baseline ran on**, recorded on the run as ``meta_json.edgar_panel``. When
that file is gone the replay is refused rather than quietly re-materialized: a diff computed
against different data attributes to the policy a change that may have come from the data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
import structlog

from agentic.agent.budget import LoopBudget, SafetyLimits
from agentic.agent.policy import AgentPolicy
from agentic.agent.replay import ReplayNotPossible, ReplayResult, replay_investigation
from agentic.domain import Investigation
from backend.agents.agentic_model_policy import build_agent_policy
from backend.config.settings import Settings, get_settings
from backend.models.analysis_run import AnalysisRun
from backend.observability.agent_observer import BackendAgentObserver
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.services.analysis_run_service import AnalysisRunService

log = structlog.get_logger(__name__)


class ReplayDataUnavailable(ReplayNotPossible):
    """The baseline's dataset can no longer be reconstructed, so no honest diff is possible."""


def _payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


class InvestigationReplayService:
    """Replays the investigation attached to a persisted analysis run."""

    def __init__(
        self,
        session,
        *,
        run_service: AnalysisRunService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._runs = run_service or AnalysisRunService(session)
        self._repo = SqlAlchemyInvestigationRepository(session)
        self._settings = settings

    # -- public API ----------------------------------------------------------

    def replay_run(
        self,
        analysis_run_id: UUID,
        *,
        policy: AgentPolicy | None = None,
        budget: LoopBudget | None = None,
        safety: SafetyLimits | None = None,
        observe: bool = True,
    ) -> ReplayResult:
        """
        Replay the investigation belonging to ``analysis_run_id``.

        Args:
            policy: the decision-maker to replay under. Defaults to the currently
                configured one, which is what makes "did upgrading the model change our
                answers?" a one-call question.
            budget: alternative budget, for asking whether a cheaper run reaches the
                same answer.
            observe: emit the replay's own traces/metrics. The candidate is a real
                investigation run, so its cost and latency are worth seeing.
        """
        settings = self._settings or get_settings()
        row = self._runs.require(analysis_run_id)
        baseline = self._load_investigation(analysis_run_id)
        frame = self._reconstruct_frame(row)

        result = replay_investigation(
            baseline,
            frame=frame,
            policy=policy if policy is not None else build_agent_policy(settings),
            budget=budget,
            safety=safety,
            observer=BackendAgentObserver(analysis_run_id=str(analysis_run_id)) if observe else None,
        )
        log.info(
            "investigation_replayed",
            analysis_run_id=str(analysis_run_id),
            baseline_id=result.diff.baseline_id,
            candidate_id=result.diff.candidate_id,
            verdict=result.diff.verdict.value,
            summary=result.summary(),
        )
        return result

    # -- internals -----------------------------------------------------------

    def _load_investigation(self, analysis_run_id: UUID) -> Investigation:
        row = self._repo.get_by_analysis_run_id(analysis_run_id)
        if row is None:
            raise ReplayNotPossible(
                f"analysis run {analysis_run_id} has no persisted investigation to replay "
                "(it may have run on the deterministic EDGAR engine)"
            )
        return self._repo.load_domain(row.id)

    def _reconstruct_frame(self, row: AnalysisRun) -> pd.DataFrame | None:
        """
        Rebuild the exact frame the baseline analyzed.

        Order matters: the recorded panel file is preferred over anything that would
        re-derive the data, because a replay is only meaningful when the data is held fixed.
        """
        meta = _payload_dict(row.meta_json)
        panel = _payload_dict(meta.get("edgar_panel"))
        features_csv = panel.get("features_csv")
        if features_csv:
            path = Path(str(features_csv))
            if not path.is_file():
                raise ReplayDataUnavailable(
                    f"the panel this run analyzed is gone ({path}); replaying would compare "
                    "against different data. Re-run the analysis instead of replaying it."
                )
            return pd.read_csv(path)

        dataset = _payload_dict(_payload_dict(row.input_payload_json).get("dataset"))
        records = dataset.get("records")
        if isinstance(records, list) and records:
            return pd.DataFrame(records)

        path_value = dataset.get("path") or dataset.get("panel_csv")
        if path_value:
            path = Path(str(path_value))
            if not path.is_file():
                raise ReplayDataUnavailable(
                    f"the dataset file this run analyzed is gone ({path}); replaying would "
                    "compare against different data."
                )
            return pd.read_csv(path)

        raise ReplayDataUnavailable(
            "this run did not record a reconstructable dataset, so it cannot be replayed"
        )
