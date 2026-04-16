"""Helpers for isolated Postgres worker-queue regression tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.project import Project
from backend.models.run_execution_job import RunExecutionJob
from backend.models.user import User

DEFAULT_TEST_POSTGRES_URL = "postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar"


def postgres_test_url() -> str:
    return os.getenv("EDGAR_TEST_POSTGRES_URL", DEFAULT_TEST_POSTGRES_URL)


def _unique_database_name() -> str:
    return f"edgar_test_{uuid.uuid4().hex[:12]}"


def _quoted_database_name(database_name: str) -> str:
    return f'"{database_name}"'


@pytest.fixture(scope="module")
def postgres_session_factory() -> Iterator[sessionmaker[Session]]:
    admin_url = make_url(postgres_test_url())
    database_name = _unique_database_name()
    test_url = admin_url.set(database=database_name)

    admin_engine = create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {_quoted_database_name(database_name)}"))

    test_engine = create_engine(test_url, poolclass=NullPool)
    Base.metadata.create_all(test_engine)

    try:
        yield sessionmaker(bind=test_engine, expire_on_commit=False)
    finally:
        test_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {_quoted_database_name(database_name)}"))
        admin_engine.dispose()


def seed_queued_job(factory: sessionmaker[Session]) -> tuple[uuid.UUID, uuid.UUID]:
    """Return ``(analysis_run_id, job_id)`` for one queued run with a pending attempt."""
    db = factory()
    try:
        uid = uuid.uuid4()
        db.add(User(id=uid, email=f"{uid.hex[:8]}@t.example", is_active=True))
        pid = uuid.uuid4()
        db.add(Project(id=pid, owner_user_id=uid, name="postgres-test"))
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
        jid = uuid.uuid4()
        db.add(
            RunExecutionJob(
                id=jid,
                analysis_run_id=rid,
                status=RunExecutionJobStatus.pending,
                attempt_count=1,
            )
        )
        db.commit()
        return rid, jid
    finally:
        db.close()


def list_jobs_for_run(factory: sessionmaker[Session], analysis_run_id: uuid.UUID) -> list[RunExecutionJob]:
    db = factory()
    try:
        return list(
            db.scalars(
                select(RunExecutionJob)
                .where(RunExecutionJob.analysis_run_id == analysis_run_id)
                .order_by(RunExecutionJob.attempt_count.asc(), RunExecutionJob.created_at.asc())
            ).all()
        )
    finally:
        db.close()

