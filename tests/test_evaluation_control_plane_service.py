"""Shared evaluation control-plane execution service coverage."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
from backend.models.project import Project
from backend.models.user import User
from backend.services.evaluation_control_plane_service import EvaluationControlPlaneService
from edgar_project.evaluation.catalog import get_supported_evaluation_suite
from edgar_project.evaluation.schemas import ValidationDegradationClass
from edgar_project.repo_layout import REPO_ROOT


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


def test_start_fixture_suite_persists_passed_case_rows(
    session_factory: sessionmaker[Session],
) -> None:
    evaluation_run_id = _seed_evaluation_run(
        session_factory,
        suite_id="suite_fixtures_v1",
    )

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id)
        db.commit()
        db.refresh(row)
        case_rows = list(
            db.scalars(
                select(EvaluationCaseResult).where(
                    EvaluationCaseResult.evaluation_run_id == row.id
                )
            ).all()
        )

    assert row.status.value == "passed"
    assert row.started_at is not None
    assert row.finished_at is not None
    assert row.results_json is not None
    assert row.results_json["case_count"] == 5
    assert row.summary_json is not None
    assert row.summary_json["suite_id"] == "suite_fixtures_v1"
    assert len(case_rows) == 5
    assert {case.status for case in case_rows} == {"passed"}
    assert all(case.observation_json is None for case in case_rows)


def test_start_live_suite_without_opt_in_persists_policy_skipped_case(
    session_factory: sessionmaker[Session],
) -> None:
    evaluation_run_id = _seed_evaluation_run(
        session_factory,
        suite_id="suite_smoke",
    )

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id, allow_live=False)
        db.commit()
        db.refresh(row)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )

    assert row.status.value == "skipped"
    assert case_row is not None
    assert case_row.status == "skipped"
    assert case_row.degradation_class == ValidationDegradationClass.policy_skipped.value
    assert case_row.policy_json is not None
    assert case_row.policy_json["requires_explicit_live_opt_in"] is True
    assert case_row.observation_json is not None
    assert case_row.observation_json["freshness_window_seconds"] == 300


def test_start_hybrid_suite_with_opt_in_persists_policy_and_observation_json(
    session_factory: sessionmaker[Session],
) -> None:
    evaluation_run_id = _seed_evaluation_run(
        session_factory,
        suite_id="suite_hybrid_smoke_v1",
    )

    with session_factory() as db:
        service = EvaluationControlPlaneService(db)
        row = service.start_evaluation_run(evaluation_run_id, allow_live=True)
        db.commit()
        db.refresh(row)
        case_row = db.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == row.id
            )
        )

    assert row.status.value == "skipped"
    assert case_row is not None
    assert case_row.input_mode == "hybrid"
    assert case_row.policy_json is not None
    assert case_row.observation_json is not None
    assert case_row.observation_json["freshness_window_seconds"] == 300
    assert case_row.metadata_json is not None
    assert case_row.metadata_json["input_mode"] == "hybrid"
