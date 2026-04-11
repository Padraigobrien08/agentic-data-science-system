"""Worker job claim, lease, and transient retry behavior."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
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
from backend.worker.loop import process_next_job


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


def _seed_queued_job(factory: sessionmaker[Session]) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (project_id, job_id) with run queued and one pending job."""
    db = factory()
    try:
        uid = uuid.uuid4()
        user = User(id=uid, email=f"{uid.hex[:8]}@t.example", is_active=True)
        db.add(user)
        pid = uuid.uuid4()
        proj = Project(id=pid, owner_user_id=uid, name="p")
        db.add(proj)
        rid = uuid.uuid4()
        run = AnalysisRun(
            id=rid,
            project_id=pid,
            status=AnalysisRunStatus.queued,
            orchestration_goal_text="g",
            input_payload_json={"tickers": ["X"]},
        )
        db.add(run)
        jid = uuid.uuid4()
        job = RunExecutionJob(
            id=jid,
            analysis_run_id=rid,
            status=RunExecutionJobStatus.pending,
            attempt_count=0,
        )
        db.add(job)
        db.commit()
        return rid, jid
    finally:
        db.close()


def test_claim_increments_attempt_and_sets_lease(session_factory: sessionmaker[Session]) -> None:
    _seed_queued_job(session_factory)
    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        job = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert job is not None
        assert job.status == RunExecutionJobStatus.running
        assert job.attempt_count == 1
        assert job.lease_expires_at is not None
        assert job.claimed_at is not None
        db.commit()
    finally:
        db.close()


def test_stale_lease_same_attempt_when_run_still_queued(session_factory: sessionmaker[Session]) -> None:
    """Expired lease + run queued: reclaim extends lease without bumping attempt_count."""
    run_id, _jid = _seed_queued_job(session_factory)
    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        j1 = repo.claim_next_runnable(lease_seconds=1.0, max_attempts=4)
        assert j1 is not None
        assert j1.attempt_count == 1
        db.commit()
    finally:
        db.close()

    db2 = session_factory()
    try:
        job = db2.scalars(select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_id)).first()
        assert job is not None
        job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db2.commit()
    finally:
        db2.close()

    db3 = session_factory()
    try:
        repo = RunExecutionJobRepository(db3)
        j2 = repo.claim_next_runnable(lease_seconds=120.0, max_attempts=4)
        assert j2 is not None
        assert j2.attempt_count == 1
        assert j2.lease_expires_at is not None
        db3.commit()
    finally:
        db3.close()


def test_transient_failure_requeues_until_max_attempts(session_factory: sessionmaker[Session]) -> None:
    from unittest.mock import patch

    run_id, _ = _seed_queued_job(session_factory)

    def boom(*_a: object, **_k: object) -> None:
        raise TimeoutError("downstream")

    with patch(
        "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
        boom,
    ):
        for i in range(3):
            assert process_next_job(session_factory, lease_seconds=600.0, max_attempts=3) is True
            db = session_factory()
            try:
                job = db.scalars(select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_id)).first()
                assert job is not None
                if i < 2:
                    assert job.status == RunExecutionJobStatus.pending, f"iteration {i}"
                    assert job.attempt_count == i + 1
                else:
                    assert job.status == RunExecutionJobStatus.failed
                    assert job.attempt_count == 3
            finally:
                db.close()
