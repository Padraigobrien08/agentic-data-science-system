"""
EDGAR data reaching the adaptive investigation loop.

Before this, an EDGAR-adapter run arrived at the loop as a *schema-only* manifest —
columns declared, ``frame=None`` — so every EDGAR experiment degraded and the loop could
never actually analyze SEC data. These tests prove the panel is materialized into the
run's workspace, the loop receives a real frame, and the EDGAR-specific experiment tools
are genuinely selected and executed.

All offline: the SEC-facing materializer is replaced by one that writes a fixture
features frame, which is exactly the seam the real one implements.
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
from agentic.agent.fixture_policy import FixtureAgentPolicy
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
from backend.services.edgar_panel_materializer import (
    EdgarPanelUnavailable,
    MaterializedEdgarPanel,
)
from edgar_project.run_workspace import RunWorkspace

# The EDGAR tools the loop can only reach once a real frame is present.
EDGAR_TOOLS = {
    "edgar_revenue_growth_analysis",
    "edgar_margin_quality_analysis",
    "edgar_trend_break_analysis",
    "edgar_peer_comparison",
}


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


def _features_frame(tickers: tuple[str, ...] = ("AAA", "BBB", "CCC"), periods: int = 8) -> pd.DataFrame:
    """A realistic EDGAR features frame: identity columns + src.anomaly.FEATURE_COLS."""
    rows = []
    for i, ticker in enumerate(tickers):
        for q in range(periods):
            revenue = 100.0 + (10.0 * q) + (5.0 * i)
            rows.append({
                "ticker": ticker,
                "cik": 1000 + i,
                "company_name": f"{ticker} Inc",
                "period": f"20{21 + q // 4}-Q{q % 4 + 1}",
                "revenue": revenue,
                "net_income": revenue * (0.20 - 0.01 * q),
                "revenue_growth_qoq": 0.10 - 0.005 * q,
                "net_margin": 0.20 - 0.01 * q,
                "current_ratio": 1.8 - 0.02 * q,
                "debt_to_assets": 0.40 + 0.01 * q,
            })
    return pd.DataFrame(rows)


class _FixturePanelMaterializer:
    """Stands in for the SEC-facing materializer, writing a fixture features CSV."""

    def __init__(self, frame: pd.DataFrame | None = None, *, fail_with: str | None = None) -> None:
        self._frame = frame if frame is not None else _features_frame()
        self._fail_with = fail_with
        self.calls: list[dict] = []

    def materialize(
        self, *, tickers: list[str], workspace: RunWorkspace, refresh: bool
    ) -> MaterializedEdgarPanel:
        self.calls.append({"tickers": list(tickers), "workspace": workspace, "refresh": refresh})
        if self._fail_with:
            raise EdgarPanelUnavailable(self._fail_with)
        workspace.ensure_directories()
        path = workspace.processed_dir / "features.csv"
        self._frame.to_csv(path, index=False)
        return MaterializedEdgarPanel(
            features_csv=path, row_count=len(self._frame), tickers=list(tickers)
        )


def _edgar_payload(**dataset_overrides) -> dict:
    dataset = {"adapter": "edgar", "entities": ["AAA", "BBB", "CCC"]}
    dataset.update(dataset_overrides)
    return {
        "engine": ENGINE_AGENTIC,
        "analysis_goal": "revenue growth is deteriorating over time",
        "dataset": dataset,
    }


def _seed_run(session: Session, *, input_payload: dict) -> AnalysisRun:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.flush()
    run = AnalysisRun(
        project_id=project.id,
        initiated_by_user_id=user.id,
        status=AnalysisRunStatus.pending,
        input_payload_json=input_payload,
    )
    session.add(run)
    session.commit()
    return run


def _executed_tools(session: Session) -> list[str]:
    from backend.models.investigation_entities import ExperimentResultRow

    return [row.tool_name for row in session.query(ExperimentResultRow).all()]


@pytest.fixture
def run_service(session: Session, tmp_path: Path, monkeypatch):
    """Service wired to a fixture materializer and a temp run-workspace root."""

    def _build(materializer=None):
        materializer = materializer or _FixturePanelMaterializer()
        settings = Settings(run_workspace_root=tmp_path / "workspaces")
        monkeypatch.setattr(
            "backend.services.agentic_investigation_execution_service.get_settings",
            lambda: settings,
        )
        service = AgenticInvestigationExecutionService(
            session,
            policy_factory=lambda _s: FixtureAgentPolicy(),
            panel_materializer=materializer,
        )
        return service, materializer

    return _build


# -- the panel reaches the loop ---------------------------------------------


def test_edgar_run_materializes_the_panel(session: Session, run_service) -> None:
    service, materializer = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    assert len(materializer.calls) == 1, "the panel must be materialized exactly once"
    assert materializer.calls[0]["tickers"] == ["AAA", "BBB", "CCC"]
    assert materializer.calls[0]["refresh"] is False


def test_edgar_run_executes_experiments_over_a_real_frame(session: Session, run_service) -> None:
    """The regression this whole change exists for: a schema-only manifest ran nothing."""
    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    result = service.execute_analysis_run(run.id)

    assert result.experiments_count > 0, "the loop must actually run experiments over EDGAR data"
    assert result.evidence_count > 0, "experiments over a real frame must produce evidence"


def test_edgar_specific_tools_become_reachable(session: Session, run_service) -> None:
    """EDGAR_INTENT_TOOLS are only candidates when the manifest looks like an EDGAR panel."""
    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    executed = _executed_tools(session)
    assert set(executed) & EDGAR_TOOLS, f"no EDGAR experiment was selected; ran {executed}"
    # EDGAR tools are prepended to the intent candidates, so one leads the run.
    assert executed[0] in EDGAR_TOOLS, f"expected an EDGAR tool first, got {executed[0]!r}"


def test_the_loop_adapts_across_several_experiments(session: Session, run_service) -> None:
    """A real frame lets the loop iterate: several distinct tools, not one degraded step."""
    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    executed = _executed_tools(session)
    assert len(executed) >= 2, f"the loop should run multiple experiments, ran {executed}"
    assert len(set(executed)) == len(executed), f"tools should not repeat: {executed}"


def test_hypotheses_move_against_contradicting_edgar_data(session: Session, run_service) -> None:
    """The fixture revenue rises while the goal claims deterioration, so the claim must fall."""
    from backend.models.investigation_entities import HypothesisRow

    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    statuses = {row.status for row in session.query(HypothesisRow).all()}
    assert statuses, "the run must persist hypotheses"
    assert not statuses <= {"proposed", "active"}, (
        f"evidence should have moved the hypothesis off its initial state; got {statuses}"
    )


def test_schema_only_edgar_manifest_would_have_no_frame() -> None:
    """
    Documents the gap this change closes: without a panel_csv the EDGAR adapter declares
    columns but materializes no data, so every experiment degrades.
    """
    from agentic.adapters import AdapterRequest
    from agentic.adapters.edgar import EDGARAdapter

    materialized = EDGARAdapter().materializer(AdapterRequest(entities=["AAA"])).materialize()
    assert materialized.frame is None
    assert materialized.declared_columns, "the schema is still declared — only the data is missing"


def test_run_reaches_a_successful_terminal_status(session: Session, run_service) -> None:
    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    result = service.execute_analysis_run(run.id)

    assert result.db_status in {AnalysisRunStatus.success, AnalysisRunStatus.partial_success}
    session.refresh(run)
    assert run.status is result.db_status


# -- workspace isolation and traceability -----------------------------------


def test_panel_is_written_into_the_run_scoped_workspace(session: Session, run_service) -> None:
    service, materializer = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    workspace = materializer.calls[0]["workspace"]
    assert workspace.run_scoped_id == str(run.id), "the workspace must be scoped to this run"
    assert (workspace.processed_dir / "features.csv").is_file()


def test_two_runs_get_isolated_workspaces(session: Session, run_service) -> None:
    service, materializer = run_service()
    first = _seed_run(session, input_payload=_edgar_payload())
    second = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(first.id)
    service.execute_analysis_run(second.id)

    roots = {call["workspace"].root for call in materializer.calls}
    assert len(roots) == 2, "runs must not share a panel workspace"


def test_panel_provenance_is_recorded_on_the_run(session: Session, run_service) -> None:
    service, _ = run_service()
    run = _seed_run(session, input_payload=_edgar_payload())

    service.execute_analysis_run(run.id)

    session.refresh(run)
    meta = run.meta_json or {}
    assert meta["run_workspace"]["run_scoped_id"] == str(run.id)
    panel = meta["edgar_panel"]
    assert panel["row_count"] == 24  # 3 tickers x 8 periods
    assert panel["tickers"] == ["AAA", "BBB", "CCC"]
    assert panel["features_csv"].endswith("features.csv")


# -- explicit panel_csv still wins ------------------------------------------


def test_explicit_panel_csv_skips_materialization(session: Session, run_service, tmp_path: Path) -> None:
    """Pointing at a fixture or existing file must not trigger an SEC fetch."""
    fixture = tmp_path / "given.csv"
    _features_frame().to_csv(fixture, index=False)

    service, materializer = run_service()
    run = _seed_run(session, input_payload=_edgar_payload(panel_csv=str(fixture)))

    result = service.execute_analysis_run(run.id)

    assert materializer.calls == [], "an explicit panel_csv must bypass the materializer"
    assert result.experiments_count > 0


def test_refresh_flag_is_forwarded(session: Session, run_service) -> None:
    service, materializer = run_service()
    run = _seed_run(session, input_payload=_edgar_payload(refresh=True))

    service.execute_analysis_run(run.id)

    assert materializer.calls[0]["refresh"] is True


# -- failure is loud, not a silent empty analysis ---------------------------


def test_unavailable_panel_fails_the_run(session: Session, run_service) -> None:
    """
    A run with no data must not quietly produce an 'insufficient evidence' conclusion:
    that is indistinguishable from a real analytical finding.
    """
    service, _ = run_service(_FixturePanelMaterializer(fail_with="SEC unreachable"))
    run = _seed_run(session, input_payload=_edgar_payload())

    with pytest.raises(EdgarPanelUnavailable):
        service.execute_analysis_run(run.id)

    session.refresh(run)
    assert run.status is AnalysisRunStatus.error
    assert "SEC unreachable" in (run.error_summary or "")


def test_no_investigation_is_persisted_when_the_panel_is_unavailable(
    session: Session, run_service
) -> None:
    from backend.models.investigation import Investigation as InvestigationRow

    service, _ = run_service(_FixturePanelMaterializer(fail_with="empty panel"))
    run = _seed_run(session, input_payload=_edgar_payload())

    with pytest.raises(EdgarPanelUnavailable):
        service.execute_analysis_run(run.id)

    assert session.query(InvestigationRow).count() == 0


# -- the materializer's own contract ----------------------------------------


def test_loop_budget_comes_from_settings() -> None:
    """
    The service used to run on ``LoopBudget()`` defaults, which left the elapsed-time and
    cost budgets unreachable in a deployment even though the loop enforces them.
    """
    from backend.services.agentic_investigation_execution_service import _loop_budget

    budget = _loop_budget(Settings(
        agent_max_experiments=3,
        agent_max_parallel_experiments=4,
        agent_max_elapsed_seconds=42.0,
        agent_max_cost_usd=0.25,
    ))
    assert budget.max_experiments == 3
    assert budget.max_parallel_experiments == 4
    assert budget.max_elapsed_seconds == 42.0
    assert budget.max_cost_usd == 0.25


def test_parallel_experiments_setting_reaches_the_loop(session: Session, tmp_path: Path, monkeypatch) -> None:
    """Batching is only useful if an operator can actually turn it on."""
    settings = Settings(
        run_workspace_root=tmp_path / "ws",
        agent_max_parallel_experiments=3,
    )
    monkeypatch.setattr(
        "backend.services.agentic_investigation_execution_service.get_settings",
        lambda: settings,
    )
    seen: dict = {}
    real_start = None

    from agentic.agent.loop import InvestigationLoop

    real_start = InvestigationLoop.start

    def _spy_start(self, *args, **kwargs):
        seen["budget"] = kwargs.get("budget")
        return real_start(self, *args, **kwargs)

    monkeypatch.setattr(InvestigationLoop, "start", _spy_start)

    service = AgenticInvestigationExecutionService(
        session,
        policy_factory=lambda _s: FixtureAgentPolicy(),
        panel_materializer=_FixturePanelMaterializer(),
    )
    run = _seed_run(session, input_payload=_edgar_payload())
    service.execute_analysis_run(run.id)

    assert seen["budget"] is not None, "the service must pass an explicit budget"
    assert seen["budget"].max_parallel_experiments == 3


def test_materializer_rejects_an_empty_ticker_list(tmp_path: Path) -> None:
    from backend.services.edgar_panel_materializer import DeterministicEdgarPanelMaterializer

    workspace = RunWorkspace(
        run_scoped_id="r1",
        root=tmp_path,
        processed_dir=tmp_path / "processed",
        artifacts_dir=tmp_path / "artifacts",
        manual_validation_csv=tmp_path / "mv.csv",
    )
    with pytest.raises(EdgarPanelUnavailable, match="No tickers"):
        DeterministicEdgarPanelMaterializer().materialize(
            tickers=["", "  "], workspace=workspace, refresh=False
        )
