"""Construct the default object store from settings."""

from __future__ import annotations

from backend.config.settings import Settings, get_settings
from backend.storage.local import LocalFilesystemStore
from backend.storage.protocol import ArtifactObjectStore
from backend.storage.s3 import S3ObjectStore
from backend.storage.types import UnsupportedStorageUri


def get_local_object_store(settings: Settings | None = None) -> LocalFilesystemStore:
    """Primary write/read store for this deployment (local disk today)."""
    cfg = settings if settings is not None else get_settings()
    return LocalFilesystemStore(cfg.artifact_storage_root)


def get_s3_object_store(settings: Settings | None = None) -> S3ObjectStore:
    """Primary write/read store for deployments configured to use S3-compatible storage."""
    cfg = settings if settings is not None else get_settings()
    secret = (
        cfg.artifact_storage_s3_secret_access_key.get_secret_value()
        if cfg.artifact_storage_s3_secret_access_key
        else None
    )
    return S3ObjectStore(
        bucket=cfg.artifact_storage_s3_bucket or "",
        region=cfg.artifact_storage_s3_region,
        prefix=cfg.artifact_storage_s3_prefix,
        endpoint_url=cfg.artifact_storage_s3_endpoint_url,
        access_key_id=cfg.artifact_storage_s3_access_key_id,
        secret_access_key=secret,
        force_path_style=cfg.artifact_storage_s3_force_path_style,
    )


def get_object_store(settings: Settings | None = None) -> ArtifactObjectStore:
    """Configured default write store for this deployment."""
    cfg = settings if settings is not None else get_settings()
    if cfg.artifact_storage_backend == "s3":
        return get_s3_object_store(cfg)
    return get_local_object_store(cfg)


def get_store_for_uri(uri: str, settings: Settings | None = None) -> ArtifactObjectStore:
    """Resolve a backend by persisted URI scheme."""
    cfg = settings if settings is not None else get_settings()
    if uri.startswith("local:"):
        return get_local_object_store(cfg)
    if uri.startswith("s3:") and cfg.artifact_storage_backend == "s3":
        return get_s3_object_store(cfg)
    raise UnsupportedStorageUri(uri)
