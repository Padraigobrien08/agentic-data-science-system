"""Construct the default object store from settings."""

from __future__ import annotations

from backend.config.settings import Settings, get_settings
from backend.storage.local import LocalFilesystemStore


def get_local_object_store(settings: Settings | None = None) -> LocalFilesystemStore:
    """Primary write/read store for this deployment (local disk today)."""
    cfg = settings if settings is not None else get_settings()
    return LocalFilesystemStore(cfg.artifact_storage_root)
