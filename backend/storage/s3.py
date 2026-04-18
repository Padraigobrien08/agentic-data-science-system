"""S3-compatible object store — persisted URIs use the logical ``s3:`` scheme."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import BinaryIO
from urllib.parse import quote, unquote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.storage.local import assert_safe_key
from backend.storage.types import ObjectNotFound, StoredObject

_STREAM_CHUNK_SIZE = 1024 * 1024


@dataclass(slots=True)
class _HashingStream:
    source: BinaryIO
    digest: hashlib._Hash
    byte_size: int = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self.source.read(size)
        if chunk:
            self.digest.update(chunk)
            self.byte_size += len(chunk)
        return chunk


class S3ObjectStore:
    """S3-compatible object store that keeps bucket and prefix out of persisted URIs."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str = "us-east-1",
        prefix: str = "",
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        force_path_style: bool = False,
    ) -> None:
        client_config = Config(
            s3={"addressing_style": "path" if force_path_style else "auto"},
            region_name=region,
        )
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=client_config,
        )

    @property
    def scheme(self) -> str:
        return "s3"

    @property
    def bucket(self) -> str:
        return self._bucket

    def make_uri(self, key: str) -> str:
        safe = assert_safe_key(key)
        encoded = quote(safe, safe="/")
        return f"{self.scheme}:{encoded}"

    def key_from_uri(self, uri: str) -> str:
        prefix = f"{self.scheme}:"
        if not uri.startswith(prefix):
            raise ObjectNotFound(uri)
        tail = uri[len(prefix) :].lstrip("/")
        if not tail:
            raise ObjectNotFound(uri)
        return assert_safe_key(unquote(tail))

    def _provider_key(self, key: str) -> str:
        safe = assert_safe_key(key)
        if not self._prefix:
            return safe
        return f"{self._prefix}/{safe}"

    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> StoredObject:
        return self.put_fileobj(
            key,
            io.BytesIO(data),
            content_type=content_type,
        )

    def put_fileobj(
        self,
        key: str,
        source: BinaryIO,
        *,
        content_type: str | None = None,
    ) -> StoredObject:
        logical_key = assert_safe_key(key)
        digest = hashlib.sha256()
        hashing_stream = _HashingStream(source=source, digest=digest)
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self._client.upload_fileobj(
            hashing_stream,
            self._bucket,
            self._provider_key(logical_key),
            ExtraArgs=extra_args or None,
        )
        return StoredObject(
            uri=self.make_uri(logical_key),
            byte_size=hashing_stream.byte_size,
            sha256_hex=digest.hexdigest(),
            content_type=content_type,
        )

    def get(self, key: str) -> bytes:
        logical_key = assert_safe_key(key)
        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=self._provider_key(logical_key),
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise ObjectNotFound(logical_key) from exc
            raise
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    @contextmanager
    def open_reader(self, key: str) -> Iterator[BinaryIO]:
        logical_key = assert_safe_key(key)
        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=self._provider_key(logical_key),
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise ObjectNotFound(logical_key) from exc
            raise
        body = response["Body"]
        try:
            yield body
        finally:
            body.close()

    def exists(self, key: str) -> bool:
        logical_key = assert_safe_key(key)
        try:
            self._client.head_object(
                Bucket=self._bucket,
                Key=self._provider_key(logical_key),
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                return False
            raise

    def delete(self, key: str) -> None:
        logical_key = assert_safe_key(key)
        self._client.delete_object(
            Bucket=self._bucket,
            Key=self._provider_key(logical_key),
        )

    def list_keys_under(self, prefix: str) -> list[str]:
        logical_prefix = prefix.strip()
        if logical_prefix:
            logical_prefix = assert_safe_key(logical_prefix.replace("\\", "/"))
        provider_prefix = self._provider_key(logical_prefix) if logical_prefix else self._prefix
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=provider_prefix):
            for item in page.get("Contents", []):
                raw_key = item["Key"]
                logical_key = raw_key
                if self._prefix and raw_key.startswith(f"{self._prefix}/"):
                    logical_key = raw_key[len(self._prefix) + 1 :]
                elif self._prefix and raw_key == self._prefix:
                    logical_key = ""
                if logical_key:
                    keys.append(logical_key)
        return sorted(set(keys))
