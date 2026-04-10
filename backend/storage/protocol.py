"""Object store protocol — implement for local disk today, S3-compatible API later."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO, Protocol

from backend.storage.types import StoredObject


class ArtifactObjectStore(Protocol):
    """
    Content-addressable blob storage keyed by *relative* object keys.

    Keys use POSIX separators and must not contain ``..`` or leading ``/``.
    URIs persisted in the database embed the backend scheme (e.g. ``local:``).
    """

    @property
    def scheme(self) -> str:
        """URI scheme / prefix this backend owns (e.g. ``local``)."""
        ...

    def make_uri(self, key: str) -> str:
        """Build the canonical URI stored in ``Artifact.storage_uri``."""
        ...

    def key_from_uri(self, uri: str) -> str:
        """Parse a URI produced by :meth:`make_uri` back into a storage key."""
        ...

    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> StoredObject:
        """Write *data* at *key* (overwrite allowed)."""
        ...

    def get(self, key: str) -> bytes:
        """Read full object. Raises :class:`~backend.storage.types.ObjectNotFound` if missing."""
        ...

    @contextmanager
    def open_reader(self, key: str) -> Iterator[BinaryIO]:
        """Stream object bytes (file handle for local; future S3 body)."""
        ...

    def exists(self, key: str) -> bool:
        ...

    def delete(self, key: str) -> None:
        """Remove object if present; no-op if missing."""
        ...

    def list_keys_under(self, prefix: str) -> list[str]:
        """
        Return sorted keys starting with *prefix* (relative keys, POSIX).

        Intended for ops/reconciliation; primary listing for product use is DB metadata.
        """
        ...
