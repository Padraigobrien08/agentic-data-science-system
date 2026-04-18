"""Live and hybrid evaluation child-run linkage coverage."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from backend.models.analysis_run import AnalysisRun
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
from backend.models.project import Project
from backend.models.run_execution_job import RunExecutionJob
from backend.models.user import User
from backend.services.evaluation_control_plane_service import EvaluationControlPlaneService
from edgar_project.evaluation.catalog import get_supported_evaluation_suite
from edgar_project.evaluation.schemas import BenchmarkSuite
from edgar_project.repo_layout import REPO_ROOT
from tests.api_auth import register_project_and_headers


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, dict[str, str], sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers, factory
    app.dependency_overrides.clear()


def _seed_evaluation_run(
    factory: sessionmaker[Session],
    *,
    suite_id: str,
) -> UUID:
    suite = get_supported_evaluation_suite(suite_id)
    manifest_rel = str(suite.manifest_path.relative_to(REPO_ROOT))
    with factory() as db:
        user = User(email=f"{suite_id}@example.com", hashed_password="hashed")
        db.add(user)
        db.flush()
        project = Project(owner_user_id=user.id, name=f"{suite_id} project")
        db.add(project)
        db.flush()
        row = EvaluationRun(
            project_id=project.id,
            initiated_by_user_id=user.id,
            suite_id=suite_id,
            suite_manifest_path=manifest_rel,
        )
        db.add(row)
        db.commit()
        return row.id


def test_enqueue_live_or_hybrid_case_run_creates_child_run_and_pending_job(
    session_factory: sessionmaker[Session],
) -> None:
    evaluation_run_id = _seed_evaluation_run(session_factory, suite_id="suite_smoke")

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        evaluation_run = db.get(EvaluationRun, evaluation_run_id)
        assert evaluation_run is not None
        suite_ref = get_supported_evaluation_suite("suite_smoke")
        suite = BenchmarkSuite.model_validate_json(
            suite_ref.manifest_path.read_text(encoding="utf-8")
        )
        case = suite.cases[0]
        case_row = EvaluationCaseResult(
            evaluation_run_id=evaluation_run.id,
            case_id=case.case_id,
            input_mode=case.input.mode.value,
            status="pending",
            degradation_class="none",
            run_goal=case.input.goal,
            message="queued",
            policy_json=case.input.policy.model_dump(mode="json") if case.input.policy else None,
            observation_json={"freshness_window_seconds": case.input.policy.freshness_window_seconds},
            checks_json=None,
            metadata_json={"input_mode": case.input.mode.value},
            artifacts_json=None,
        )
        db.add(case_row)
        db.flush()

        child_run_id = service._enqueue_live_or_hybrid_case_run(
            evaluation_run,
            case_row,
            case,
        )
        db.commit()

        child_run = db.get(AnalysisRun, child_run_id)
        assert child_run is not None
        assert child_run.project_id == evaluation_run.project_id
        assert child_run.meta_json is not None
        assert child_run.meta_json["evaluation_case_link"]["evaluation_run_id"] == str(evaluation_run.id)
        assert child_run.meta_json["evaluation_case_link"]["case_id"] == case.case_id
        assert child_run.meta_json["evaluation_case_link"]["suite_id"] == evaluation_run.suite_id
        assert child_run.meta_json["evaluation_case_link"]["input_mode"] == case.input.mode.value

        job = db.scalar(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == child_run_id)
        )
        assert job is not None
        assert job.status.value == "pending"

        db.refresh(case_row)
        assert case_row.latest_analysis_run_id == child_run_id
        assert case_row.latest_analysis_run_status == "queued"
        assert isinstance(case_row.analysis_run_history_json, list)
        assert case_row.analysis_run_history_json[-1]["analysis_run_id"] == str(child_run_id)
        assert case_row.analysis_run_history_json[-1]["status"] == "queued"


def test_case_routes_serialize_linked_analysis_run_fields(
    api_client: tuple[TestClient, str, dict[str, str], sessionmaker[Session]],
) -> None:
    client, project_id, headers, factory = api_client

    created = client.post(
        "/v1/evaluations",
        headers=headers,
        json={"project_id": project_id, "suite_id": "suite_fixtures_v1"},
    )
    assert created.status_code == 201, created.text
    evaluation_run_id = UUID(created.json()["id"])

    with factory() as db:
        evaluation_run = db.get(EvaluationRun, evaluation_run_id)
        assert evaluation_run is not None
        child_run = AnalysisRun(
            project_id=evaluation_run.project_id,
            initiated_by_user_id=evaluation_run.initiated_by_user_id,
            orchestration_goal_text="fixture linked run",
            status="queued",
        )
        db.add(child_run)
        db.flush()
        db.add(
            EvaluationCaseResult(
                evaluation_run_id=evaluation_run_id,
                case_id="fixture-linked",
                input_mode="fixture",
                status="passed",
                degradation_class="none",
                run_goal="fixture linked run",
                message="passed",
                latest_analysis_run_id=child_run.id,
                latest_analysis_run_status="queued",
                analysis_run_history_json=[
                    {"analysis_run_id": str(child_run.id), "status": "queued"}
                ],
            )
        )
        db.commit()

    listed = client.get(
        f"/v1/evaluations/{evaluation_run_id}/cases",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    listed_body = listed.json()
    assert len(listed_body) == 1
    assert listed_body[0]["latest_analysis_run_id"] is not None
    assert listed_body[0]["latest_analysis_run_status"] == "queued"
    assert listed_body[0]["analysis_run_history_json"][0]["status"] == "queued"
