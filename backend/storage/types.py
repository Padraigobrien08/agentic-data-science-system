"""Value types and errors for object storage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Result of a successful ``put`` — persist :attr:`uri` on :class:`~backend.models.artifact.Artifact`."""

    uri: str
    byte_size: int
    sha256_hex: str | None = None
    content_type: str | None = None


class StorageError(Exception):
    """Base class for storage backend failures."""


class ObjectNotFound(StorageError):
    """Requested object key or URI does not exist."""


class UnsupportedStorageUri(StorageError):
    """No backend registered for the URI scheme."""


class InvalidStorageKey(StorageError):
    """Key path is empty or unsafe (e.g. path traversal)."""
