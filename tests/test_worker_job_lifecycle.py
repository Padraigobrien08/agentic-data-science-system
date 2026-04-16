"""Worker job claim, lease, and durable retry behavior."""

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
from backend.services.exceptions import WorkerLeaseLostError
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
            attempt_count=1,
        )
        db.add(job)
        db.commit()
        return rid, jid
    finally:
        db.close()


def test_queue_observability_snapshot_matches_claimable_pending(session_factory: sessionmaker[Session]) -> None:
    _seed_queued_job(session_factory)
    db = session_factory()
    try:
        snap = RunExecutionJobRepository(db).queue_observability_snapshot(max_attempts=4)
        assert snap.pending_claimable == 1
        assert snap.jobs_running_lease_ok == 0
        assert snap.jobs_running_stale_lease == 0
        assert snap.open_jobs_on_cancelled_run == 0
    finally:
        db.close()


def test_claim_preserves_attempt_and_sets_lease(session_factory: sessionmaker[Session]) -> None:
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
        assert job.claim_token is not None
        db.commit()
    finally:
        db.close()


def test_null_lease_reclaimed_when_run_still_queued(session_factory: sessionmaker[Session]) -> None:
    """Running row with missing lease + run queued: same reclaim path as expired lease."""
    run_id, _jid = _seed_queued_job(session_factory)
    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        j1 = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert j1 is not None
        assert j1.attempt_count == 1
        db.commit()
    finally:
        db.close()

    db2 = session_factory()
    try:
        job = db2.scalars(select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_id)).first()
        assert job is not None
        job.lease_expires_at = None
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


def test_stale_lease_same_attempt_when_run_still_queued(session_factory: sessionmaker[Session]) -> None:
    """Expired lease + run queued: reclaim extends lease without bumping attempt_count."""
    run_id, _jid = _seed_queued_job(session_factory)
    db = session_factory()
    first_claim_token: str | None = None
    try:
        repo = RunExecutionJobRepository(db)
        j1 = repo.claim_next_runnable(lease_seconds=1.0, max_attempts=4)
        assert j1 is not None
        assert j1.attempt_count == 1
        first_claim_token = j1.claim_token
        assert first_claim_token is not None
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
        assert j2.claim_token is not None
        assert j2.claim_token != first_claim_token
        db3.commit()
    finally:
        db3.close()


def test_queue_observability_counts_final_allowed_pending_attempt(
    session_factory: sessionmaker[Session],
) -> None:
    _seed_queued_job(session_factory)
    db = session_factory()
    try:
        snap = RunExecutionJobRepository(db).queue_observability_snapshot(max_attempts=1)
        assert snap.pending_claimable == 1
    finally:
        db.close()


def test_stale_running_reclaim_creates_next_pending_attempt(
    session_factory: sessionmaker[Session],
) -> None:
    run_id, _jid = _seed_queued_job(session_factory)
    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        claimed = repo.claim_next_runnable(lease_seconds=1.0, max_attempts=3)
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
        reclaimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=3)
        assert reclaimed is None

        rows = list(
            db2.scalars(
                select(RunExecutionJob)
                .where(RunExecutionJob.analysis_run_id == run_id)
                .order_by(RunExecutionJob.attempt_count.asc(), RunExecutionJob.created_at.asc())
            ).all()
        )
        assert [row.attempt_count for row in rows] == [1, 2]
        assert rows[0].status == RunExecutionJobStatus.failed
        assert rows[0].error_detail == "lease_expired_mid_run"
        assert rows[1].status == RunExecutionJobStatus.pending
        assert rows[1].claim_token is None

        run = db2.get(AnalysisRun, run_id)
        assert run is not None
        assert run.status == AnalysisRunStatus.queued
    finally:
        db2.close()


def test_renew_lease_rejects_stale_claim_token(session_factory: sessionmaker[Session]) -> None:
    _seed_queued_job(session_factory)
    db = session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        job = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert job is not None
        assert job.claim_token is not None

        with pytest.raises(WorkerLeaseLostError):
            repo.renew_lease(job.id, "stale-token", lease_seconds=120.0)
    finally:
        db.close()


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
                rows = list(
                    db.scalars(
                        select(RunExecutionJob)
                        .where(RunExecutionJob.analysis_run_id == run_id)
                        .order_by(RunExecutionJob.attempt_count.asc(), RunExecutionJob.created_at.asc())
                    ).all()
                )
                assert rows
                if i < 2:
                    assert [row.attempt_count for row in rows] == list(range(1, i + 3))
                    assert all(row.status == RunExecutionJobStatus.failed for row in rows[:-1])
                    assert rows[-1].status == RunExecutionJobStatus.pending, f"iteration {i}"
                else:
                    assert [row.attempt_count for row in rows] == [1, 2, 3]
                    assert all(row.status == RunExecutionJobStatus.failed for row in rows)
            finally:
                db.close()
