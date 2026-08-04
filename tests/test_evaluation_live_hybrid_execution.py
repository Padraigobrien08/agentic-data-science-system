"""Live and hybrid evaluation child-run linkage coverage."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
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
from backend.models.enums import AnalysisRunStatus
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


@pytest.mark.parametrize(
    ("suite_id", "allow_live", "expected_mode"),
    [
        ("suite_smoke", False, "live"),
        ("suite_hybrid_smoke_v1", True, "hybrid"),
    ],
)
def test_start_async_supported_evaluation_suite_returns_running_with_pending_child_case(
    session_factory: sessionmaker[Session],
    *,
    suite_id: str,
    allow_live: bool,
    expected_mode: str,
) -> None:
    evaluation_run_id = _seed_evaluation_run(session_factory, suite_id=suite_id)

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id, allow_live=allow_live)
        db.commit()
        db.refresh(row)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )
        assert case_row is not None
        child_run = db.get(AnalysisRun, case_row.latest_analysis_run_id)
        job = db.scalar(
            select(RunExecutionJob).where(
                RunExecutionJob.analysis_run_id == case_row.latest_analysis_run_id
            )
        )

    assert row.status.value == "running"
    assert row.started_at is not None
    assert row.finished_at is None
    assert row.results_json is not None
    assert row.results_json["case_count"] == 1
    assert row.results_json["results"][0]["status"] == "pending"
    assert row.summary_json is not None
    assert row.summary_json["pending_cases"] == 1

    assert case_row.status == "pending"
    assert case_row.input_mode == expected_mode
    assert case_row.latest_analysis_run_id is not None
    assert case_row.latest_analysis_run_status == "queued"
    assert case_row.policy_json is not None
    assert case_row.observation_json is not None
    assert case_row.observation_json["freshness_window_seconds"] == 300
    assert case_row.analysis_run_history_json[-1]["status"] == "queued"

    assert child_run is not None
    assert child_run.status == AnalysisRunStatus.queued
    assert job is not None
    assert job.status.value == "pending"


def test_refresh_linked_case_results_reconciles_terminal_child_run_truth(
    session_factory: sessionmaker[Session],
) -> None:
    evaluation_run_id = _seed_evaluation_run(session_factory, suite_id="suite_smoke")

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )
        assert case_row is not None
        child_run = db.get(AnalysisRun, case_row.latest_analysis_run_id)
        assert child_run is not None
        child_run.status = AnalysisRunStatus.success
        child_run.started_at = datetime.now(timezone.utc) - timedelta(seconds=8)
        child_run.finished_at = datetime.now(timezone.utc)
        child_run.output_payload_json = {
            "source_observed_at": (
                datetime.now(timezone.utc) - timedelta(seconds=30)
            ).isoformat()
        }

        refreshed = service.refresh_linked_case_results(row.id)
        db.commit()
        db.refresh(refreshed)
        db.refresh(case_row)

    assert refreshed.status.value == "passed"
    assert refreshed.finished_at is not None
    assert refreshed.results_json is not None
    assert refreshed.results_json["results"][0]["status"] == "passed"
    assert refreshed.summary_json is not None
    assert refreshed.summary_json["pending_cases"] == 0

    assert case_row.status == "passed"
    assert case_row.degradation_class == "none"
    assert case_row.latest_analysis_run_status == "success"
    assert case_row.message == "passed via linked analysis run"
    assert case_row.metadata_json is not None
    assert case_row.metadata_json["analysis_run_id"] == str(case_row.latest_analysis_run_id)
    assert case_row.metadata_json["analysis_run_status"] == "success"
    assert case_row.analysis_run_history_json[-1]["status"] == "success"
    assert case_row.observation_json is not None
    assert case_row.observation_json["freshness_window_seconds"] == 300
    assert case_row.observation_json["source_age_seconds"] >= 0


def test_healthy_run_payload_containing_429_is_not_read_as_rate_limiting(
    session_factory: sessionmaker[Session],
) -> None:
    """A successful run's own data must never trip the upstream-failure heuristics.

    Regression test. The heuristics used to substring-match the whole serialized
    payload, so any run whose data contained "429" — a figure like 4291000, a CIK, or
    an ISO timestamp whose microseconds happened to read .429183 — was classified as
    sec_rate_limited. That misreported healthy runs as upstream-degraded in production
    and made these tests fail depending on the wall-clock time they ran at.
    """
    evaluation_run_id = _seed_evaluation_run(session_factory, suite_id="suite_smoke")

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )
        assert case_row is not None
        child_run = db.get(AnalysisRun, case_row.latest_analysis_run_id)
        assert child_run is not None
        child_run.status = AnalysisRunStatus.success
        child_run.started_at = datetime.now(timezone.utc) - timedelta(seconds=8)
        child_run.finished_at = datetime.now(timezone.utc)
        # Recent enough to stay inside the freshness window (so this asserts the
        # upstream heuristic, not staleness), but with microseconds pinned so the
        # serialized timestamp always contains "429".
        observed_at = (datetime.now(timezone.utc) - timedelta(seconds=30)).replace(
            microsecond=429183
        )
        # Every "429" here is legitimate run data, not an HTTP status.
        child_run.output_payload_json = {
            "source_observed_at": observed_at.isoformat(),
            "revenue": 4291000,
            "cik": "0000042900",
        }
        child_run.meta_json = {"artifact_bytes": 429, "notes": "403 filings scanned"}

        service.refresh_linked_case_results(row.id)
        db.commit()
        db.refresh(case_row)

    assert case_row.degradation_class == "none"
    assert case_row.status == "passed"
    assert "upstream_error_code" not in (case_row.metadata_json or {})


# Auto-retry retained as belt-and-braces only. The failure this originally masked was
# not an ORM/pydantic aliasing issue: the upstream/storage heuristics substring-matched
# the serialized payload, so a timestamp or figure containing "429" read as an HTTP 429
# (see the regression test above). Root cause is fixed; drop the reruns once CI has run
# green for a while.
@pytest.mark.flaky(reruns=3)
@pytest.mark.parametrize(
    ("error_summary", "meta_patch", "expected_degradation", "expected_metadata_key", "expected_metadata_value"),
    [
        (
            "SEC rate limit while reading recent filings",
            {"upstream_error_code": "sec_rate_limited"},
            "upstream_sec_degraded",
            "upstream_error_code",
            "sec_rate_limited",
        ),
        (
            "Could not read artifact from storage",
            {"storage_error_code": "artifact_storage_unavailable"},
            "product_regression",
            "storage_error_code",
            "artifact_storage_unavailable",
        ),
    ],
)
def test_refresh_linked_case_results_captures_sec_and_storage_failure_evidence(
    session_factory: sessionmaker[Session],
    *,
    error_summary: str,
    meta_patch: dict[str, str],
    expected_degradation: str,
    expected_metadata_key: str,
    expected_metadata_value: str,
) -> None:
    evaluation_run_id = _seed_evaluation_run(session_factory, suite_id="suite_smoke")

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )
        assert case_row is not None
        child_run = db.get(AnalysisRun, case_row.latest_analysis_run_id)
        assert child_run is not None
        child_run.status = AnalysisRunStatus.error
        child_run.started_at = datetime.now(timezone.utc) - timedelta(seconds=4)
        child_run.finished_at = datetime.now(timezone.utc)
        child_run.error_summary = error_summary
        child_run.meta_json = {
            **(child_run.meta_json if isinstance(child_run.meta_json, dict) else {}),
            **meta_patch,
        }

        refreshed = service.refresh_linked_case_results(row.id)
        db.commit()
        db.refresh(refreshed)
        db.refresh(case_row)

    assert refreshed.status.value == "error"
    assert refreshed.results_json is not None
    assert refreshed.results_json["results"][0]["status"] == "error"
    assert case_row.status == "error"
    assert case_row.degradation_class == expected_degradation
    assert case_row.latest_analysis_run_status == "error"
    assert case_row.message == error_summary
    assert case_row.metadata_json is not None
    assert case_row.metadata_json[expected_metadata_key] == expected_metadata_value
    assert case_row.analysis_run_history_json[-1]["status"] == "error"


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
            status=AnalysisRunStatus.queued,
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
