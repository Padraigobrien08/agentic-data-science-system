"""Resolve persisted ``storage_uri`` values to the correct backend (extensible for S3)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO

from backend.config.settings import Settings, get_settings
from backend.storage.factory import get_local_object_store
from backend.storage.local import LocalFilesystemStore
from backend.storage.types import UnsupportedStorageUri


def _local_store(settings: Settings) -> LocalFilesystemStore:
    return get_local_object_store(settings)


def read_bytes(uri: str, *, settings: Settings | None = None) -> bytes:
    """Load object bytes for a URI stored on :class:`~backend.models.artifact.Artifact`."""
    cfg = settings if settings is not None else get_settings()
    if uri.startswith("local:"):
        store = _local_store(cfg)
        return store.get(store.key_from_uri(uri))
    # Future: elif uri.startswith("s3:") or uri.startswith("https://"): ...
    raise UnsupportedStorageUri(uri)


@contextmanager
def open_reader(uri: str, *, settings: Settings | None = None) -> Iterator[BinaryIO]:
    """Stream object bytes for large artifacts."""
    cfg = settings if settings is not None else get_settings()
    if uri.startswith("local:"):
        store = _local_store(cfg)
        with store.open_reader(store.key_from_uri(uri)) as fh:
            yield fh
        return
    raise UnsupportedStorageUri(uri)


def delete_at_uri(uri: str, *, settings: Settings | None = None) -> None:
    """Best-effort delete of stored bytes (used when removing artifact rows)."""
    cfg = settings if settings is not None else get_settings()
    if uri.startswith("local:"):
        store = _local_store(cfg)
        store.delete(store.key_from_uri(uri))
        return
    raise UnsupportedStorageUri(uri)
