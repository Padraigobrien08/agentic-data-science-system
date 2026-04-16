"""Background lease heartbeat for claimed worker jobs."""

from __future__ import annotations

import threading
from collections.abc import Callable
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.exceptions import WorkerLeaseLostError

log = structlog.get_logger(__name__)


class WorkerLeaseGuard:
    """Renew a claimed job lease in the background and surface ownership loss via checkpoints."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        job_id: UUID,
        claim_token: str,
        lease_seconds: float,
        interval_seconds: float | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._job_id = job_id
        self._claim_token = claim_token
        self._lease_seconds = lease_seconds
        self._interval_seconds = (
            interval_seconds if interval_seconds is not None else self.default_interval_seconds(lease_seconds)
        )
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def default_interval_seconds(lease_seconds: float) -> float:
        return min(max(lease_seconds / 3.0, 5.0), 60.0)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=f"lease-guard-{self._job_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def checkpoint(self) -> None:
        if self._lost.is_set():
            raise WorkerLeaseLostError("Worker no longer owns the claimed execution job")

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            session = self._session_factory()
            try:
                repo = RunExecutionJobRepository(session)
                repo.renew_lease(
                    self._job_id,
                    self._claim_token,
                    lease_seconds=self._lease_seconds,
                )
                session.commit()
            except WorkerLeaseLostError:
                session.rollback()
                self._lost.set()
                return
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                log.warning(
                    "worker_lease_guard_heartbeat_failed",
                    worker_event="worker_lease_heartbeat_failed",
                    job_id=str(self._job_id),
                    exc_type=type(exc).__name__,
                    error=str(exc),
                )
            finally:
                session.close()
