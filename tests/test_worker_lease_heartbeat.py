"""Worker lease heartbeat and ownership-loss regressions."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

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
from backend.worker.lease import WorkerLeaseGuard
from backend.worker.loop import process_next_job
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)


@pytest.fixture
def threaded_session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    db_path = tmp_path / "worker-heartbeat.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _seed_queued_job(factory: sessionmaker[Session]) -> uuid.UUID:
    db = factory()
    try:
        uid = uuid.uuid4()
        db.add(User(id=uid, email=f"{uid.hex[:8]}@t.example", is_active=True))
        pid = uuid.uuid4()
        db.add(Project(id=pid, owner_user_id=uid, name="p"))
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


def _fake_output() -> OrchestrationOutput:
    return OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=InterpretedGoal(
            code=InterpretedGoalCode.full_pipeline,
            description="full",
            user_goal_text="goal",
        ),
        artifact_paths={},
    )


class _FastWorkerLeaseGuard(WorkerLeaseGuard):
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        job_id: uuid.UUID,
        claim_token: str,
        lease_seconds: float,
    ) -> None:
        super().__init__(
            session_factory,
            job_id=job_id,
            claim_token=claim_token,
            lease_seconds=lease_seconds,
            interval_seconds=0.01,
        )


def test_process_next_job_renews_lease_during_delayed_pipeline(
    threaded_session_factory: sessionmaker[Session],
) -> None:
    run_id = _seed_queued_job(threaded_session_factory)
    entered_pipeline = threading.Event()
    release_pipeline = threading.Event()
    heartbeat_seen = threading.Event()
    result: dict[str, bool] = {}
    renew_calls: list[str] = []

    original_renew_lease = RunExecutionJobRepository.renew_lease

    def delayed_traceable(
        _session: Session,
        _analysis_run_id: uuid.UUID,
        _orch_in: object,
        *,
        execution_checkpoint=None,
        **_: object,
    ) -> SimpleNamespace:
        assert execution_checkpoint is not None
        execution_checkpoint()
        entered_pipeline.set()
        assert release_pipeline.wait(timeout=1.0)
        execution_checkpoint()
        return SimpleNamespace(orchestration_output=_fake_output(), output_payload_patch={})

    def recording_renew_lease(
        self: RunExecutionJobRepository,
        job_id: uuid.UUID,
        claim_token: str,
        *,
        lease_seconds: float,
    ):
        renew_calls.append(claim_token)
        heartbeat_seen.set()
        return original_renew_lease(self, job_id, claim_token, lease_seconds=lease_seconds)

    def run_worker() -> None:
        result["claimed"] = process_next_job(
            threaded_session_factory,
            lease_seconds=30.0,
            max_attempts=3,
        )

    with (
        patch("backend.worker.loop.WorkerLeaseGuard", _FastWorkerLeaseGuard),
        patch(
            "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
            delayed_traceable,
        ),
        patch.object(RunExecutionJobRepository, "renew_lease", recording_renew_lease),
    ):
        worker_thread = threading.Thread(target=run_worker)
        worker_thread.start()
        assert entered_pipeline.wait(timeout=1.0)
        assert heartbeat_seen.wait(timeout=1.0)
        release_pipeline.set()
        worker_thread.join(timeout=2.0)
        assert not worker_thread.is_alive()

    assert result["claimed"] is True
    assert renew_calls

    db = threaded_session_factory()
    try:
        run = db.get(AnalysisRun, run_id)
        job = db.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_id)
        ).first()
        assert run is not None
        assert job is not None
        assert run.status == AnalysisRunStatus.success
        assert job.status == RunExecutionJobStatus.completed
    finally:
        db.close()


def test_process_next_job_aborts_when_ownership_lost_during_orchestration(
    threaded_session_factory: sessionmaker[Session],
) -> None:
    run_id = _seed_queued_job(threaded_session_factory)
    entered_pipeline = threading.Event()
    continue_pipeline = threading.Event()
    force_lease_loss = threading.Event()
    result: dict[str, bool] = {}

    def checkpointed_traceable(
        _session: Session,
        _analysis_run_id: uuid.UUID,
        _orch_in: object,
        *,
        execution_checkpoint=None,
        **_: object,
    ) -> SimpleNamespace:
        assert execution_checkpoint is not None
        execution_checkpoint()
        entered_pipeline.set()
        assert continue_pipeline.wait(timeout=1.0)
        execution_checkpoint()
        pytest.fail("ownership-loss checkpoint should have aborted execution")

    class _LossCheckpointGuard:
        def __init__(
            self,
            _session_factory: sessionmaker[Session],
            *,
            job_id: uuid.UUID,
            claim_token: str,
            lease_seconds: float,
        ) -> None:
            self.job_id = job_id
            self.claim_token = claim_token
            self.lease_seconds = lease_seconds

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

        def checkpoint(self) -> None:
            if force_lease_loss.is_set():
                raise WorkerLeaseLostError("simulated reclaim")

    def run_worker() -> None:
        result["claimed"] = process_next_job(
            threaded_session_factory,
            lease_seconds=30.0,
            max_attempts=3,
        )

    with (
        patch("backend.worker.loop.WorkerLeaseGuard", _LossCheckpointGuard),
        patch(
            "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
            checkpointed_traceable,
        ),
        patch("backend.worker.loop.observe_worker_attempt_complete") as observe_complete,
    ):
        worker_thread = threading.Thread(target=run_worker)
        worker_thread.start()
        assert entered_pipeline.wait(timeout=1.0)
        force_lease_loss.set()
        continue_pipeline.set()
        worker_thread.join(timeout=2.0)
        assert not worker_thread.is_alive()
        assert observe_complete.call_count == 1
        assert observe_complete.call_args.kwargs["finalize_outcome"] == "lease_lost"

    assert result["claimed"] is True

    db = threaded_session_factory()
    try:
        run = db.get(AnalysisRun, run_id)
        job = db.scalars(
            select(RunExecutionJob).where(RunExecutionJob.analysis_run_id == run_id)
        ).first()
        assert run is not None
        assert job is not None
        assert run.status == AnalysisRunStatus.queued
        assert run.output_payload_json is None
        assert job.status == RunExecutionJobStatus.running
        assert job.claim_token is not None
        assert job.attempt_count == 1
    finally:
        db.close()
