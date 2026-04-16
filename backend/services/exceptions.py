"""Service-layer errors (business rules)."""


class InvalidStatusTransition(ValueError):
    """Raised when a status change is not allowed for the entity."""

    def __init__(self, entity: str, current: object, target: object) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(f"{entity}: cannot transition from {current!r} to {target!r}")


class RunLifecycleError(ValueError):
    """Business rule violation for cancel / retry (maps to HTTP 4xx)."""

    def __init__(self, message: str, *, status_code: int = 409) -> None:
        self.status_code = status_code
        super().__init__(message)


class RunCancelledDuringExecution(Exception):
    """
    The run was marked cancelled in the DB while this pipeline session was active.

    The pipeline session should rollback before raising so the worker can finalize the job
    without overwriting the cancelled run with success or a generic error.
    """


class WorkerLeaseLostError(Exception):
    """Raised when a worker no longer owns the claimed job row it is trying to mutate."""
