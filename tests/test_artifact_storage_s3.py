"""S3-compatible storage contract regressions."""

from __future__ import annotations

import io
from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic import SecretStr

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from backend.config.settings import Settings
from backend.storage.factory import (
    get_local_object_store,
    get_object_store,
    get_s3_object_store,
)
from backend.storage.resolver import open_reader, read_bytes
from backend.storage.types import ObjectNotFound, UnsupportedStorageUri

SECURE_JWT_SECRET = "secure-jwt-secret-minimum-32-characters-long"
BOOTSTRAP_TOKEN = "pytest-bootstrap-token"
OPS_TOKEN = "pytest-ops-token"


def _storage_settings(tmp_path: Path, **overrides: object) -> Settings:
    root = tmp_path / "artifact_root"
    root.mkdir(exist_ok=True)
    defaults: dict[str, object] = {
        "artifact_storage_root": root,
        "artifact_storage_backend": "s3",
        "artifact_storage_s3_bucket": "artifact-bucket",
        "artifact_storage_s3_region": "us-east-1",
        "jwt_secret": SecretStr(SECURE_JWT_SECRET),
        "bootstrap_admin_token": SecretStr(BOOTSTRAP_TOKEN),
        "ops_api_token": SecretStr(OPS_TOKEN),
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _create_bucket(settings: Settings) -> None:
    client = boto3.client("s3", region_name=settings.artifact_storage_s3_region)
    client.create_bucket(Bucket=settings.artifact_storage_s3_bucket)


@contextmanager
def _mock_aws():
    with moto.mock_aws():
        yield


def test_s3_settings_require_bucket(tmp_path) -> None:
    with pytest.raises(ValueError, match="ARTIFACT_STORAGE_S3_BUCKET"):
        _storage_settings(tmp_path, artifact_storage_s3_bucket=None)


def test_s3_store_put_get_list_delete_and_uri_omits_bucket(tmp_path) -> None:
    settings = _storage_settings(tmp_path)
    with _mock_aws():
        _create_bucket(settings)
        store = get_s3_object_store(settings)
        payload = (b"0123456789abcdef" * 1024) + b"tail"

        stored = store.put_fileobj(
            "artifacts/analysis_runs/run-id/report.bin",
            io.BytesIO(payload),
            content_type="application/octet-stream",
        )

        assert stored.uri.startswith("s3:")
        assert settings.artifact_storage_s3_bucket not in stored.uri
        assert store.key_from_uri(stored.uri) == "artifacts/analysis_runs/run-id/report.bin"
        assert store.get("artifacts/analysis_runs/run-id/report.bin") == payload
        assert stored.sha256_hex is not None
        assert store.exists("artifacts/analysis_runs/run-id/report.bin") is True
        assert store.list_keys_under("artifacts/analysis_runs") == [
            "artifacts/analysis_runs/run-id/report.bin"
        ]

        with store.open_reader("artifacts/analysis_runs/run-id/report.bin") as fh:
            assert fh.read() == payload

        store.delete("artifacts/analysis_runs/run-id/report.bin")
        assert store.exists("artifacts/analysis_runs/run-id/report.bin") is False
        with pytest.raises(ObjectNotFound):
            store.get("artifacts/analysis_runs/run-id/report.bin")


def test_get_object_store_selects_s3_backend(tmp_path) -> None:
    settings = _storage_settings(tmp_path)
    with _mock_aws():
        _create_bucket(settings)
        store = get_object_store(settings)
        assert store.scheme == "s3"


def test_resolver_reads_mixed_local_and_s3_uris(tmp_path) -> None:
    settings = _storage_settings(tmp_path)
    with _mock_aws():
        _create_bucket(settings)
        local_store = get_local_object_store(settings)
        local = local_store.put("legacy/report.txt", b"legacy", content_type="text/plain")

        s3_store = get_s3_object_store(settings)
        remote = s3_store.put("artifacts/analysis_runs/run-id/remote.txt", b"remote")

        assert read_bytes(local.uri, settings=settings) == b"legacy"
        assert read_bytes(remote.uri, settings=settings) == b"remote"

        with open_reader(local.uri, settings=settings) as fh:
            assert fh.read() == b"legacy"
        with open_reader(remote.uri, settings=settings) as fh:
            assert fh.read() == b"remote"

        with pytest.raises(UnsupportedStorageUri):
            read_bytes("gcs:bucket/object.txt", settings=settings)


def test_resolver_rejects_s3_uri_when_backend_not_configured(tmp_path) -> None:
    settings = _storage_settings(tmp_path, artifact_storage_backend="local")
    with pytest.raises(UnsupportedStorageUri):
        read_bytes("s3:artifacts/analysis_runs/run-id/report.txt", settings=settings)
