"""Artifact blob storage — local filesystem now; swap or extend factory for S3-compatible backends."""

from backend.storage.factory import get_local_object_store
from backend.storage.local import LocalFilesystemStore, assert_safe_key
from backend.storage.protocol import ArtifactObjectStore
from backend.storage.resolver import delete_at_uri, open_reader, read_bytes
from backend.storage.types import (
    InvalidStorageKey,
    ObjectNotFound,
    StorageError,
    StoredObject,
    UnsupportedStorageUri,
)

__all__ = [
    "ArtifactObjectStore",
    "InvalidStorageKey",
    "LocalFilesystemStore",
    "ObjectNotFound",
    "StorageError",
    "StoredObject",
    "UnsupportedStorageUri",
    "assert_safe_key",
    "delete_at_uri",
    "get_local_object_store",
    "open_reader",
    "read_bytes",
]
