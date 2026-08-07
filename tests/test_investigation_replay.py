"""
Replaying a persisted analysis run and diffing the result.

The service exists to answer "did changing the model / budget change our analysis?" against
real persisted runs. The property it must protect is that a replay compares *like with like*:
it reuses the exact panel the baseline analyzed, and refuses rather than silently comparing
against different data.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — register ORM metadata
from agentic.agent import DiffVerdict, FixtureAgentPolicy, LoopBudget
from agentic.agent.policy import ExperimentChoice
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.models.project import Project
from backend.models.user import User
from backend.services.agentic_investigation_execution_service import (
    ENGINE_AGENTIC,
    AgenticInvestigationExecutionService,
)
from backend.services.edgar_panel_materializer import MaterializedEdgarPanel
from backend.services.investigation_replay_service import (
    InvestigationReplayService,
    ReplayDataUnavailable,
    ReplayNotPossible,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def _features(tickers=("AAA", "BBB", "CCC"), periods: int = 8) -> pd.DataFrame:
    rows = []
    for i, ticker in enumerate(tickers):
        for q in range(periods):
            revenue = 100.0 + (10.0 * q) + (5.0 * i)
            rows.append({
                "ticker": ticker, "cik": 1000 + i, "company_name": f"{ticker} Inc",
                "period": f"20{21 + q // 4}-Q{q % 4 + 1}", "revenue": revenue,
                "net_income": revenue * (0.20 - 0.01 * q),
                "revenue_growth_qoq": 0.10 - 0.005 * q, "net_margin": 0.20 - 0.01 * q,
                "current_ratio": 1.8 - 0.02 * q, "debt_to_assets": 0.40 + 0.01 * q,
            })
    return pd.DataFrame(rows)


class _FixturePanelMaterializer:
    def materialize(self, *, tickers, workspace, refresh) -> MaterializedEdgarPanel:
        workspace.ensure_directories()
        path = workspace.processed_dir / "features.csv"
        frame = _features()
        frame.to_csv(path, index=False)
        return MaterializedEdgarPanel(features_csv=path, row_count=len(frame), tickers=list(tickers))


def _seed_run(session: Session, payload: dict) -> AnalysisRun:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.flush()
    run = AnalysisRun(
        project_id=project.id, initiated_by_user_id=user.id,
        status=AnalysisRunStatus.pending, input_payload_json=payload,
    )
    session.add(run)
    session.commit()
    return run


def _edgar_payload() -> dict:
    return {
        "engine": ENGINE_AGENTIC,
        "analysis_goal": "revenue is increasing over time",
        "dataset": {"adapter": "edgar", "entities": ["AAA", "BBB", "CCC"]},
    }


def _inline_payload() -> dict:
    return {
        "engine": ENGINE_AGENTIC,
        "analysis_goal": "revenue is increasing over time",
        "dataset": {
            "adapter": "in_memory", "name": "rev",
            "records": [{"entity": "A", "period": f"2021-{i}", "revenue": 5 + 6 * i} for i in range(8)],
            "time_field": "period", "entity_id_fields": ["entity"],
        },
    }


@pytest.fixture
def executed_run(session: Session, tmp_path: Path, monkeypatch):
    """Run an agentic investigation so there is a real persisted baseline to replay."""

    def _execute(payload: dict | None = None):
        settings = Settings(run_workspace_root=tmp_path / "ws")
        monkeypatch.setattr(
            "backend.services.agentic_investigation_execution_service.get_settings",
            lambda: settings,
        )
        service = AgenticInvestigationExecutionService(
            session,
            policy_factory=lambda _s: FixtureAgentPolicy(),
            panel_materializer=_FixturePanelMaterializer(),
        )
        run = _seed_run(session, payload or _edgar_payload())
        service.execute_analysis_run(run.id)
        session.refresh(run)
        return run

    return _execute


def _replay_service(session: Session) -> InvestigationReplayService:
    return InvestigationReplayService(session, settings=Settings())


# -- replaying unchanged reproduces the baseline -----------------------------


def test_replaying_a_run_unchanged_is_identical(session: Session, executed_run) -> None:
    run = executed_run()
    result = _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())

    assert result.diff.verdict is DiffVerdict.identical
    assert result.same_dataset
    assert result.diff.baseline_tools == result.diff.candidate_tools


def test_replay_uses_the_exact_panel_the_run_analyzed(session: Session, executed_run) -> None:
    """Like-with-like: the recorded panel is read, not re-materialized from the SEC."""
    run = executed_run()
    panel_path = Path(run.meta_json["edgar_panel"]["features_csv"])
    assert panel_path.is_file()

    result = _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())
    assert result.diff.verdict is DiffVerdict.identical


def test_replay_does_not_overwrite_the_baseline(session: Session, executed_run) -> None:
    from backend.models.investigation import Investigation as InvestigationRow

    run = executed_run()
    before = session.query(InvestigationRow).count()
    result = _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())

    assert session.query(InvestigationRow).count() == before, "replay must not persist over the baseline"
    assert result.candidate.id != result.baseline.id


def test_inline_dataset_runs_are_replayable(session: Session, executed_run) -> None:
    run = executed_run(_inline_payload())
    result = _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())
    assert result.diff.verdict is DiffVerdict.identical


# -- changed conditions surface as a diff ------------------------------------


def test_a_tighter_budget_is_reported_as_divergence(session: Session, executed_run) -> None:
    run = executed_run()
    result = _replay_service(session).replay_run(
        run.id, policy=FixtureAgentPolicy(), budget=LoopBudget(max_experiments=1))

    assert result.changed
    assert len(result.diff.candidate_tools) < len(result.diff.baseline_tools)
    assert "diverged" in result.summary() or "different route" in result.summary()


class _DecliningPolicy(FixtureAgentPolicy):
    """Stands in for a model that stops choosing experiments."""

    def select_experiment(self, *, goal_summary, candidates):
        return ExperimentChoice(request_index=None, rationale="declined")


def test_a_different_policy_is_reported_as_divergence(session: Session, executed_run) -> None:
    """The headline use case: swap the decision-maker, see whether the answer holds."""
    run = executed_run()
    result = _replay_service(session).replay_run(run.id, policy=_DecliningPolicy())

    assert result.diff.verdict is DiffVerdict.diverged
    assert result.diff.candidate_tools == []
    assert result.diff.baseline_tools


# -- refusing rather than comparing against different data -------------------


def test_replay_refuses_when_the_panel_is_gone(session: Session, executed_run) -> None:
    """
    Silently re-materializing would attribute a data change to the policy. Refusing keeps
    the diff honest.
    """
    run = executed_run()
    Path(run.meta_json["edgar_panel"]["features_csv"]).unlink()

    with pytest.raises(ReplayDataUnavailable, match="gone"):
        _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())


def test_replay_refuses_a_run_with_no_investigation(session: Session) -> None:
    run = _seed_run(session, _edgar_payload())  # never executed
    with pytest.raises(ReplayNotPossible, match="no persisted investigation"):
        _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())


def test_replay_refuses_a_run_with_no_reconstructable_dataset(session: Session, executed_run) -> None:
    run = executed_run()
    run.meta_json = {}
    run.input_payload_json = {"engine": ENGINE_AGENTIC, "analysis_goal": "x"}
    session.commit()

    with pytest.raises(ReplayDataUnavailable, match="cannot be replayed"):
        _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())


# -- the diff is a reportable artifact ---------------------------------------


def test_diff_serializes_for_transport(session: Session, executed_run) -> None:
    run = executed_run()
    result = _replay_service(session).replay_run(run.id, policy=FixtureAgentPolicy())

    payload = result.diff.model_dump(mode="json")
    assert payload["verdict"] in {v.value for v in DiffVerdict}
    assert payload["baseline_conclusion"]["statement"]
    assert isinstance(payload["hypothesis_deltas"], list)
