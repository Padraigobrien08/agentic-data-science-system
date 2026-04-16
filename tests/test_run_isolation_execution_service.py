from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.agents.traceable_analysis_pipeline import TraceableEdgarPipelineResult
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus
from backend.models.project import Project
from backend.models.user import User
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)


def _session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


def test_execute_analysis_run_uses_explicit_workspace_paths(tmp_path: Path) -> None:
    session_iter = _session()
    session = next(session_iter)
    try:
        user = User(email="run-isolation@example.com")
        session.add(user)
        session.flush()
        project = Project(owner_user_id=user.id, name="Run Isolation")
        session.add(project)
        session.flush()

        runs = AnalysisRunService(session)
        run = runs.create(
            project.id,
            orchestration_goal_text="find unusual financial changes",
            input_payload_json={"tickers": ["AAPL"]},
        )
        session.commit()

        settings = Settings(
            artifact_storage_root=tmp_path / "artifact-store",
            run_workspace_root=tmp_path / "run-workspaces",
        )
        artifact_service = ArtifactService(session, settings=settings)

        captured: dict[str, object] = {}

        def _fake_coord(inp, *, execution_context=None):
            assert execution_context is not None
            captured["execution_context"] = execution_context
            workspace = execution_context["run_workspace"]
            report_path = Path(workspace["artifacts_dir"]) / "report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("# report\n", encoding="utf-8")
            return (
                OrchestrationOutput(
                    status=OrchestrationRunStatus.success,
                    message="ok",
                    interpreted_goal=InterpretedGoal(
                        code=InterpretedGoalCode.full_pipeline,
                        description="d",
                        user_goal_text=inp.analysis_goal,
                    ),
                    artifact_paths={"report_md": str(report_path)},
                ),
                None,
            )

        def _fake_traceable(_session, _analysis_run_id, orch_in, *, coordinator, **_):
            out, state = coordinator(orch_in)
            return TraceableEdgarPipelineResult(out, {})

        service = EdgarPipelineExecutionService(
            session,
            artifact_service=artifact_service,
            orchestration_with_state=_fake_coord,
        )

        with patch(
            "backend.services.edgar_pipeline_execution_service.get_settings",
            return_value=settings,
        ):
            with patch(
                "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
                _fake_traceable,
            ):
                with patch("os.chdir") as mock_chdir:
                    out = service.execute_analysis_run(run.id)

        assert out.status == OrchestrationRunStatus.success
        mock_chdir.assert_not_called()

        execution_context = captured["execution_context"]
        assert isinstance(execution_context, dict)
        payload = execution_context["run_workspace"]
        assert payload["run_scoped_id"] == str(run.id)
        assert payload["root"] == str(settings.run_workspace_root / str(run.id))
        assert payload["processed_dir"] == str(settings.run_workspace_root / str(run.id) / "processed")
        assert payload["artifacts_dir"] == str(settings.run_workspace_root / str(run.id) / "artifacts")

        row = session.get(AnalysisRun, run.id)
        assert row is not None
        assert row.status == AnalysisRunStatus.success
        assert isinstance(row.meta_json, dict)
        assert row.meta_json["run_workspace"] == payload

        artifacts = session.query(Artifact).filter(Artifact.analysis_run_id == run.id).all()
        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert isinstance(artifact.meta_json, dict)
        assert artifact.meta_json["run_workspace"] == payload
        assert artifact.meta_json["source"] == "pipeline"
        assert artifact.meta_json["source_filename"] == "report.md"
        assert artifact.meta_json["source_workspace_relative_path"] == "artifacts/report.md"
        assert "source_path" not in artifact.meta_json
    finally:
        try:
            next(session_iter)
        except StopIteration:
            pass
