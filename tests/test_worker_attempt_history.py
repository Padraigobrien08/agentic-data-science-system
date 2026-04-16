"""End-to-end attempt-history regressions for one analysis run id."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.project import Project
from backend.models.run_execution_job import RunExecutionJob
from backend.models.user import User
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.run_lifecycle_service import RunLifecycleService
from backend.worker.loop import process_next_job


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _seed_queued_job(factory: sessionmaker[Session]) -> uuid.UUID:
    db = factory()
    try:
        uid = uuid.uuid4()
        db.add(User(id=uid, email=f"{uid.hex[:8]}@t.example", is_active=True))
        pid = uuid.uuid4()
        db.add(Project(id=pid, owner_user_id=uid, name="history-test"))
        rid = uuid.uuid4()
        db.add(
            AnalysisRun(
                id=rid,
                project_id=pid,
                status=AnalysisRunStatus.queued,
                orchestration_goal_text="goal",
                input_payload_json={"tickers": ["MSFT"]},
            )
        )
        db.add(
            RunExecutionJob(
                analysis_run_id=rid,
                status=RunExecutionJobStatus.pending,
                attempt_count=1,
            )
        )
        db.commit()
        return rid
    finally:
        db.close()


def _status_history(
    factory: sessionmaker[Session],
    analysis_run_id: uuid.UUID,
) -> tuple[AnalysisRunStatus, bool, list[tuple[int, RunExecutionJobStatus, str | None]]]:
    db = factory()
    try:
        row, has_open, _latest, history = RunLifecycleService(db).build_status_view(analysis_run_id)
        return (
            row.status,
            has_open,
            [(job.attempt_count, job.status, job.error_detail) for job in history],
        )
    finally:
        db.close()


def test_transient_retry_accumulates_history_on_same_run_id(
    session_factory: sessionmaker[Session],
) -> None:
    run_id = _seed_queued_job(session_factory)

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        side_effect=TimeoutError("downstream timeout"),
    ):
        assert process_next_job(session_factory, lease_seconds=600.0, max_attempts=4) is True

    run_status, has_open, history = _status_history(session_factory, run_id)
    assert run_status == AnalysisRunStatus.queued
    assert has_open is True
    assert history == [
        (2, RunExecutionJobStatus.pending, None),
        (1, RunExecutionJobStatus.failed, "downstream timeout"),
    ]


def test_stale_running_reclaim_accumulates_history_on_same_run_id(
    session_factory: sessionmaker[Session],
) -> None:
    run_id = _seed_queued_job(session_factory)

    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        claimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert claimed is not None
        run = db.get(AnalysisRun, run_id)
        assert run is not None
        run.status = AnalysisRunStatus.running
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()

    db2 = session_factory()
    try:
        repo = RunExecutionJobRepository(db2)
        assert repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4) is None
        db2.commit()
    finally:
        db2.close()

    run_status, has_open, history = _status_history(session_factory, run_id)
    assert run_status == AnalysisRunStatus.queued
    assert has_open is True
    assert history == [
        (2, RunExecutionJobStatus.pending, None),
        (1, RunExecutionJobStatus.failed, "lease_expired_mid_run"),
    ]


def test_manual_retry_adds_new_pending_attempt_to_history(
    session_factory: sessionmaker[Session],
) -> None:
    run_id = _seed_queued_job(session_factory)

    db = session_factory()
    try:
        run = db.get(AnalysisRun, run_id)
        assert run is not None
        run.status = AnalysisRunStatus.error
        job = db.query(RunExecutionJob).filter(RunExecutionJob.analysis_run_id == run_id).one()
        job.status = RunExecutionJobStatus.failed
        job.error_detail = "first attempt failed"
        db.commit()
    finally:
        db.close()

    db2 = session_factory()
    try:
        RunLifecycleService(db2).retry_analysis_run(run_id)
        db2.commit()
    finally:
        db2.close()

    run_status, has_open, history = _status_history(session_factory, run_id)
    assert run_status == AnalysisRunStatus.queued
    assert has_open is True
    assert history == [
        (2, RunExecutionJobStatus.pending, None),
        (1, RunExecutionJobStatus.failed, "first attempt failed"),
    ]
