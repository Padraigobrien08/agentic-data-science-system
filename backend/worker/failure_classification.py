"""Classify pipeline failures for worker retry policy (transient vs terminal)."""

from __future__ import annotations

from backend.services.exceptions import RunCancelledDuringExecution

# Orchestration / validation problems: do not retry blindly.
_NON_TRANSIENT_TYPES: tuple[type[BaseException], ...] = (
    ValueError,
    KeyError,
    TypeError,
)


def is_transient_pipeline_failure(exc: BaseException) -> bool:
    """
    Return True if the worker may re-queue the run for another attempt.

    Terminal (False): invalid input, contract violations, explicit non-retryable errors.
    Transient (True): I/O, timeouts, unexpected runtime errors, DB contention, etc.
    """
    if exc is None:
        return False
    if isinstance(exc, RunCancelledDuringExecution):
        return False
    if isinstance(exc, _NON_TRANSIENT_TYPES):
        return False
    # Optional: domain errors from backend.services.exceptions
    mod = type(exc).__module__
    if mod.startswith("backend.services.") and "Error" in type(exc).__name__:
        return False
    return True
