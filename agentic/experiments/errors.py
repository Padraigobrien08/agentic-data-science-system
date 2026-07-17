"""
Structured experiment failures.

Experiments never leak raw framework exceptions across the boundary. Every
failure is an :class:`ExperimentError` carrying a stable ``code`` and a
machine-readable :meth:`to_info` mapping to the domain
:class:`~agentic.domain.experiment.ExperimentError` model used on execution records.
"""

from __future__ import annotations

from agentic.domain.experiment import ExperimentError as ExperimentErrorInfo


class ExperimentError(Exception):
    """Base for all structured experiment failures."""

    code = "EXPERIMENT_ERROR"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_info(self) -> ExperimentErrorInfo:
        return ExperimentErrorInfo(
            code=self.code,
            message=self.message,
            detail=self.detail,
            exc_type=type(self).__name__,
        )


class ExperimentValidationError(ExperimentError):
    """Parameters or capabilities failed validation."""

    code = "EXPERIMENT_VALIDATION"


class CapabilityError(ExperimentError):
    """The dataset does not satisfy the tool's required capabilities."""

    code = "CAPABILITY_UNSATISFIED"


class ParameterError(ExperimentError):
    """A parameter is missing, ill-typed, or references an absent column."""

    code = "INVALID_PARAMETER"


class ExperimentExecutionError(ExperimentError):
    """A deterministic computation failed at runtime."""

    code = "EXPERIMENT_EXECUTION"


class UnknownExperimentError(ExperimentError):
    """The requested tool is not registered."""

    code = "UNKNOWN_EXPERIMENT"
