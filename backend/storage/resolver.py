"""Resolve persisted ``storage_uri`` values to the correct backend (extensible for S3)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO

from backend.config.settings import Settings, get_settings
from backend.storage.factory import get_store_for_uri
from backend.storage.types import UnsupportedStorageUri


def read_bytes(uri: str, *, settings: Settings | None = None) -> bytes:
    """Load object bytes for a URI stored on :class:`~backend.models.artifact.Artifact`."""
    cfg = settings if settings is not None else get_settings()
    store = get_store_for_uri(uri, cfg)
    return store.get(store.key_from_uri(uri))


@contextmanager
def open_reader(uri: str, *, settings: Settings | None = None) -> Iterator[BinaryIO]:
    """Stream object bytes for large artifacts."""
    cfg = settings if settings is not None else get_settings()
    store = get_store_for_uri(uri, cfg)
    with store.open_reader(store.key_from_uri(uri)) as fh:
        yield fh


def delete_at_uri(uri: str, *, settings: Settings | None = None) -> None:
    """Best-effort delete of stored bytes (used when removing artifact rows)."""
    cfg = settings if settings is not None else get_settings()
    store = get_store_for_uri(uri, cfg)
    store.delete(store.key_from_uri(uri))
