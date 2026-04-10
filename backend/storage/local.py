"""Local filesystem object store — URIs use the ``local:`` scheme."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote, unquote

from backend.storage.types import InvalidStorageKey, ObjectNotFound, StoredObject

_UNSAFE_KEY = re.compile(r"\.\.|^/|\\\\|^$")


def assert_safe_key(key: str) -> str:
    """Validate *key* is a non-empty relative POSIX path without traversal."""
    k = key.replace("\\", "/").strip("/")
    if not k or _UNSAFE_KEY.search(k):
        raise InvalidStorageKey(f"Invalid storage key: {key!r}")
    parts = k.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise InvalidStorageKey(f"Invalid storage key segment in {key!r}")
    return k


class LocalFilesystemStore:
    """
    Stores blobs under *root_dir*; DB URIs look like ``local:artifacts/run-id/file.csv``.

    S3 follow-up: implement the same :class:`~backend.storage.protocol.ArtifactObjectStore`
    surface with scheme ``s3`` (or ``s3+alias``) and keys ``bucket/prefix/object``.
    """

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir.resolve()

    @property
    def scheme(self) -> str:
        return "local"

    @property
    def root_dir(self) -> Path:
        return self._root

    def _abs_path(self, key: str) -> Path:
        safe = assert_safe_key(key)
        path = (self._root / safe).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise InvalidStorageKey(f"Key resolves outside storage root: {key!r}") from exc
        return path

    def make_uri(self, key: str) -> str:
        safe = assert_safe_key(key)
        # Percent-encode so keys with unusual chars round-trip; ':' in path is rare but safe
        encoded = quote(safe, safe="/")
        return f"{self.scheme}:{encoded}"

    def key_from_uri(self, uri: str) -> str:
        prefix = f"{self.scheme}:"
        if not uri.startswith(prefix):
            raise InvalidStorageKey(f"Not a {self.scheme}: URI: {uri!r}")
        tail = uri[len(prefix) :].lstrip("/")
        if not tail:
            raise InvalidStorageKey(f"Empty key in URI: {uri!r}")
        return unquote(tail)

    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> StoredObject:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        return StoredObject(
            uri=self.make_uri(key),
            byte_size=len(data),
            sha256_hex=digest,
            content_type=content_type,
        )

    def get(self, key: str) -> bytes:
        path = self._abs_path(key)
        if not path.is_file():
            raise ObjectNotFound(key)
        return path.read_bytes()

    @contextmanager
    def open_reader(self, key: str) -> Iterator[BinaryIO]:
        path = self._abs_path(key)
        if not path.is_file():
            raise ObjectNotFound(key)
        with path.open("rb") as fh:
            yield fh

    def exists(self, key: str) -> bool:
        return self._abs_path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._abs_path(key)
        path.unlink(missing_ok=True)

    def list_keys_under(self, prefix: str) -> list[str]:
        pfx = prefix.strip()
        if pfx:
            base = assert_safe_key(pfx.replace("\\", "/"))
            start = self._root / base
        else:
            start = self._root
        if not start.exists():
            return []
        keys: list[str] = []
        for path in start.rglob("*"):
            if path.is_file():
                keys.append(path.relative_to(self._root).as_posix())
        return sorted(set(keys))
