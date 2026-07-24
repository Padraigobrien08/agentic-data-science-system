"""
Structured adapter failures.

Malformed or unavailable inputs raise a typed :class:`AdapterError` carrying a
stable ``code`` and machine-readable detail, rather than leaking raw framework
exceptions. :class:`SourceNotFoundError` also subclasses :class:`FileNotFoundError`
so existing file-not-found expectations keep working.
"""

from __future__ import annotations


class AdapterError(Exception):
    """Base for all structured adapter failures."""

    code = "ADAPTER_ERROR"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class SourceNotFoundError(AdapterError, FileNotFoundError):
    """The requested source (file/query/records) does not exist."""

    code = "SOURCE_NOT_FOUND"


class UnsupportedSourceError(AdapterError):
    """The adapter cannot service the requested source type/modality."""

    code = "UNSUPPORTED_SOURCE"


class MalformedDatasetError(AdapterError):
    """The source exists but could not be parsed into a dataset."""

    code = "MALFORMED_DATASET"


class EmptyDatasetError(AdapterError):
    """The source parsed but yielded no rows/documents."""

    code = "EMPTY_DATASET"
