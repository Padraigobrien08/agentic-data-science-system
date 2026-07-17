"""
Deterministic artifact emission.

An :class:`ArtifactSink` records tables, JSON objects, and chart specs produced by
an experiment. Every artifact is content-addressed (``sha256``) so identical
computations emit byte-identical, identically-fingerprinted artifacts. The
in-memory sink is used by tests and in-process runs; the directory sink also
writes bytes to disk.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from agentic.domain.common import DomainModel, new_id
from pydantic import Field

from .descriptor import ArtifactType


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(obj) -> str:
    """Stable JSON serialization (sorted keys, no whitespace drift)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class ArtifactRecord(DomainModel):
    """Metadata for one emitted artifact (content is addressed by fingerprint)."""

    id: str = Field(default_factory=lambda: new_id("art"))
    name: str
    artifact_type: ArtifactType
    media_type: str
    fingerprint: str
    byte_size: int = Field(ge=0)
    path: str | None = Field(default=None)


class ArtifactSink(ABC):
    """Records deterministic artifacts emitted by an experiment."""

    @abstractmethod
    def emit_table(self, name: str, frame: pd.DataFrame) -> ArtifactRecord: ...

    @abstractmethod
    def emit_json(self, name: str, obj) -> ArtifactRecord: ...

    @abstractmethod
    def emit_chart(self, name: str, spec: dict) -> ArtifactRecord: ...


class InMemoryArtifactSink(ArtifactSink):
    """Collects artifact bytes in memory (tests / in-process runs)."""

    def __init__(self) -> None:
        self.contents: dict[str, bytes] = {}
        self.records: list[ArtifactRecord] = []

    def _record(self, name: str, data: bytes, artifact_type: ArtifactType, media_type: str) -> ArtifactRecord:
        rec = ArtifactRecord(
            name=name,
            artifact_type=artifact_type,
            media_type=media_type,
            fingerprint=_sha256(data),
            byte_size=len(data),
        )
        self.contents[rec.id] = data
        self.records.append(rec)
        return rec

    def emit_table(self, name: str, frame: pd.DataFrame) -> ArtifactRecord:
        data = frame.to_csv(index=False).encode("utf-8")
        return self._record(name, data, ArtifactType.table, "text/csv")

    def emit_json(self, name: str, obj) -> ArtifactRecord:
        data = canonical_json(obj).encode("utf-8")
        return self._record(name, data, ArtifactType.json, "application/json")

    def emit_chart(self, name: str, spec: dict) -> ArtifactRecord:
        data = canonical_json(spec).encode("utf-8")
        return self._record(name, data, ArtifactType.chart_spec, "application/vnd.chart+json")


class DirectoryArtifactSink(InMemoryArtifactSink):
    """Also writes artifact bytes to a directory (stable file names by artifact id)."""

    _EXT = {
        ArtifactType.table: ".csv",
        ArtifactType.json: ".json",
        ArtifactType.chart_spec: ".chart.json",
        ArtifactType.summary: ".json",
    }

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _record(self, name: str, data: bytes, artifact_type: ArtifactType, media_type: str) -> ArtifactRecord:
        rec = super()._record(name, data, artifact_type, media_type)
        path = self.directory / f"{rec.id}{self._EXT.get(artifact_type, '')}"
        path.write_bytes(data)
        return rec.model_copy(update={"path": str(path)})
