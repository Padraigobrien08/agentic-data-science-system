"""Postgres-only worker queue claim and reclaim regressions."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session, sessionmaker

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.exceptions import WorkerLeaseLostError
from tests.postgres_queue_test_utils import list_jobs_for_run, seed_queued_job


def test_only_one_concurrent_session_can_claim_same_pending_row(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    run_id, _job_id = seed_queued_job(postgres_session_factory)
    claimed = threading.Event()
    release_first = threading.Event()
    results: dict[str, object] = {}

    def first_claim() -> None:
        db = postgres_session_factory()
        try:
            repo = RunExecutionJobRepository(db)
            job = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
            results["first_job_id"] = None if job is None else str(job.id)
            results["first_claim_token"] = None if job is None else job.claim_token
            claimed.set()
            assert release_first.wait(timeout=2.0)
            db.commit()
        finally:
            db.close()

    def second_claim() -> None:
        assert claimed.wait(timeout=2.0)
        db = postgres_session_factory()
        try:
            repo = RunExecutionJobRepository(db)
            job = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
            results["second_job_id"] = None if job is None else str(job.id)
            db.commit()
        finally:
            db.close()

    t1 = threading.Thread(target=first_claim)
    t2 = threading.Thread(target=second_claim)
    t1.start()
    t2.start()
    t2.join(timeout=3.0)
    release_first.set()
    t1.join(timeout=3.0)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert results["first_job_id"] is not None
    assert results["second_job_id"] is None

    rows = list_jobs_for_run(postgres_session_factory, run_id)
    assert len(rows) == 1
    assert rows[0].status == RunExecutionJobStatus.running
    assert rows[0].claim_token == results["first_claim_token"]


def test_stale_queued_reclaim_rotates_claim_token_and_rejects_old_owner(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    run_id, job_id = seed_queued_job(postgres_session_factory)

    db = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        claimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert claimed is not None
        old_claim_token = claimed.claim_token
        assert old_claim_token is not None
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()

    db2 = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db2)
        reclaimed = repo.claim_next_runnable(lease_seconds=120.0, max_attempts=4)
        assert reclaimed is not None
        assert reclaimed.id == job_id
        assert reclaimed.attempt_count == 1
        assert reclaimed.claim_token is not None
        assert reclaimed.claim_token != old_claim_token
        db2.commit()
    finally:
        db2.close()

    db3 = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db3)
        with pytest.raises(WorkerLeaseLostError):
            repo.renew_lease(job_id, old_claim_token, lease_seconds=60.0)
        assert (
            repo.finalize_attempt_if_owned(
                job_id,
                old_claim_token,
                status=RunExecutionJobStatus.completed,
            )
            is False
        )
    finally:
        db3.close()

    rows = list_jobs_for_run(postgres_session_factory, run_id)
    assert len(rows) == 1
    assert rows[0].status == RunExecutionJobStatus.running
    assert rows[0].attempt_count == 1


def test_stale_running_reclaim_creates_next_pending_attempt_and_blocks_old_owner(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    run_id, job_id = seed_queued_job(postgres_session_factory)

    db = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db)
        claimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert claimed is not None
        old_claim_token = claimed.claim_token
        assert old_claim_token is not None
        run = db.get(AnalysisRun, run_id)
        assert run is not None
        run.status = AnalysisRunStatus.running
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()

    db2 = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db2)
        reclaimed = repo.claim_next_runnable(lease_seconds=60.0, max_attempts=4)
        assert reclaimed is None
        db2.commit()
    finally:
        db2.close()

    db3 = postgres_session_factory()
    try:
        repo = RunExecutionJobRepository(db3)
        assert (
            repo.finalize_attempt_if_owned(
                job_id,
                old_claim_token,
                status=RunExecutionJobStatus.completed,
            )
            is False
        )
    finally:
        db3.close()

    rows = list_jobs_for_run(postgres_session_factory, run_id)
    assert [row.attempt_count for row in rows] == [1, 2]
    assert rows[0].status == RunExecutionJobStatus.failed
    assert rows[0].error_detail == "lease_expired_mid_run"
    assert rows[1].status == RunExecutionJobStatus.pending
    assert rows[1].claim_token is None

