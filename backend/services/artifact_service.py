"""Persist artifact metadata (DB via repository) and content (object store)."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.observability.tracing import get_tracer
from backend.domain.json_merge import merge_dict_json
from backend.models.artifact import Artifact
from backend.models.enums import ArtifactKind
from backend.repositories.artifact_repository import ArtifactRepository
from backend.repositories.run_step_repository import RunStepRepository
from backend.storage import delete_at_uri, open_reader, read_bytes
from backend.storage.factory import get_local_object_store
from backend.storage.local import LocalFilesystemStore

_SUFFIX_TO_KIND_MIME: dict[str, tuple[ArtifactKind, str]] = {
    ".csv": (ArtifactKind.tabular, "text/csv"),
    ".tsv": (ArtifactKind.tabular, "text/tab-separated-values"),
    ".json": (ArtifactKind.json, "application/json"),
    ".jsonl": (ArtifactKind.json, "application/jsonl"),
    ".ndjson": (ArtifactKind.json, "application/x-ndjson"),
    ".md": (ArtifactKind.document, "text/markdown"),
    ".markdown": (ArtifactKind.document, "text/markdown"),
    ".txt": (ArtifactKind.document, "text/plain"),
}


def infer_artifact_kind_and_mime(path: Path) -> tuple[ArtifactKind, str]:
    """Map pipeline-style outputs (CSV / JSON / Markdown) to kind + MIME type."""
    suffix = path.suffix.lower()
    if suffix in _SUFFIX_TO_KIND_MIME:
        return _SUFFIX_TO_KIND_MIME[suffix]
    return ArtifactKind.other, "application/octet-stream"


def safe_role_segment(role_key: str) -> str:
    """Filesystem-safe fragment derived from MCP-style role keys."""
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", role_key.strip()).strip("._")
    return (s[:120] if s else "artifact")


class ArtifactService:
    """
    Coordinates :class:`~backend.models.artifact.Artifact` rows (via :class:`~backend.repositories.artifact_repository.ArtifactRepository`)
    with the configured object store.
    """

    def __init__(
        self,
        session: Session,
        *,
        store: LocalFilesystemStore | None = None,
        settings: Settings | None = None,
        artifacts: ArtifactRepository | None = None,
        run_steps: RunStepRepository | None = None,
    ) -> None:
        self._settings = settings if settings is not None else get_settings()
        self._store = store if store is not None else get_local_object_store(self._settings)
        self._artifacts = artifacts if artifacts is not None else ArtifactRepository(session)
        self._run_steps = run_steps if run_steps is not None else RunStepRepository(session)

    @property
    def settings(self) -> Settings:
        """Settings bound to this service (object store root, etc.)."""
        return self._settings

    def _build_object_key(
        self,
        *,
        artifact_id: UUID,
        role_key: str,
        file_suffix: str,
        analysis_run_id: UUID | None,
        evaluation_run_id: UUID | None,
    ) -> str:
        ext = file_suffix.lower().lstrip(".") if file_suffix else "bin"
        safe = safe_role_segment(role_key)
        if analysis_run_id is not None:
            return f"artifacts/analysis_runs/{analysis_run_id}/{artifact_id}_{safe}.{ext}"
        if evaluation_run_id is not None:
            return f"artifacts/evaluation_runs/{evaluation_run_id}/{artifact_id}_{safe}.{ext}"
        raise ValueError("analysis_run_id or evaluation_run_id is required")

    def save_bytes(
        self,
        data: bytes,
        *,
        role_key: str,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        run_step_id: UUID | None = None,
        kind: ArtifactKind | None = None,
        mime_type: str | None = None,
        filename_suffix: str | None = None,
        meta_json: dict | list | None = None,
    ) -> Artifact:
        """
        Write *data* to the object store and insert an :class:`~backend.models.artifact.Artifact` row.

        Exactly one of ``analysis_run_id`` or ``evaluation_run_id`` must be set.
        """
        if (analysis_run_id is None) == (evaluation_run_id is None):
            raise ValueError("Provide exactly one of analysis_run_id or evaluation_run_id")
        if run_step_id is not None and analysis_run_id is None:
            raise ValueError("run_step_id requires analysis_run_id")

        suffix = filename_suffix or "bin"
        artifact_id = uuid.uuid4()
        key = self._build_object_key(
            artifact_id=artifact_id,
            role_key=role_key,
            file_suffix=suffix,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
        )
        k = kind if kind is not None else ArtifactKind.other
        mt = mime_type if mime_type is not None else "application/octet-stream"
        art_tr = get_tracer("backend.artifacts")
        attrs: dict[str, str | int | bool] = {
            "artifact.role": role_key,
            "artifact.kind": k.value,
        }
        if analysis_run_id is not None:
            attrs["analysis.run.id"] = str(analysis_run_id)
        if evaluation_run_id is not None:
            attrs["evaluation.run.id"] = str(evaluation_run_id)
        with art_tr.start_as_current_span("artifact.persist", attributes=attrs) as span:
            stored = self._store.put(key, data, content_type=mt)
            span.set_attribute("artifact.byte_size", int(stored.byte_size))
            uri = stored.uri
            span.set_attribute("artifact.storage.uri", uri[:512] if len(uri) > 512 else uri)

        row = Artifact(
            id=artifact_id,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            run_step_id=run_step_id,
            role_key=role_key,
            kind=k,
            storage_uri=stored.uri,
            mime_type=mt,
            byte_size=stored.byte_size,
            content_sha256=stored.sha256_hex,
            meta_json=meta_json,
        )
        self._artifacts.add(row)
        self._artifacts.flush()
        return row

    def attach_to_analysis_run(
        self,
        artifact_id: UUID,
        analysis_run_id: UUID,
        *,
        clear_run_step: bool = True,
    ) -> Artifact:
        """
        Associate an existing artifact row with an analysis run (clears evaluation scope).

        Does not move bytes on disk; ``storage_uri`` is unchanged.
        """
        row = self.require(artifact_id)
        row.analysis_run_id = analysis_run_id
        row.evaluation_run_id = None
        if clear_run_step:
            row.run_step_id = None
        self._artifacts.flush()
        return row

    def attach_to_run_step(self, artifact_id: UUID, run_step_id: UUID) -> Artifact:
        """
        Link an artifact to a step; sets ``analysis_run_id`` from the step.

        Fails if the artifact is already bound to another analysis run.
        """
        row = self.require(artifact_id)
        step = self._run_steps.get(run_step_id)
        if step is None:
            raise KeyError(f"Run step not found: {run_step_id}")
        if row.analysis_run_id is not None and row.analysis_run_id != step.analysis_run_id:
            raise ValueError(
                "Artifact is bound to a different analysis_run_id than the step's run"
            )
        row.analysis_run_id = step.analysis_run_id
        row.evaluation_run_id = None
        row.run_step_id = run_step_id
        self._artifacts.flush()
        return row

    def detach_from_run_step(self, artifact_id: UUID) -> Artifact:
        """Clear ``run_step_id`` only; artifact remains on the analysis run if set."""
        row = self.require(artifact_id)
        row.run_step_id = None
        self._artifacts.flush()
        return row

    def merge_meta_json(self, artifact_id: UUID, patch: dict | None) -> Artifact:
        row = self.require(artifact_id)
        merged = merge_dict_json(
            row.meta_json if isinstance(row.meta_json, dict) else None,
            patch,
        )
        row.meta_json = merged
        self._artifacts.flush()
        return row

    def _pipeline_source_provenance(
        self,
        *,
        path: Path,
        analysis_run_id: UUID | None,
    ) -> dict[str, str]:
        meta = {"source_filename": path.name}
        if analysis_run_id is None:
            return meta

        run_workspace_root = (self._settings.run_workspace_root / str(analysis_run_id)).resolve()
        try:
            relative_path = path.relative_to(run_workspace_root)
        except ValueError:
            return meta

        meta["source_workspace_relative_path"] = relative_path.as_posix()
        return meta

    def ingest_pipeline_file(
        self,
        source_path: Path | str,
        *,
        role_key: str,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        run_step_id: UUID | None = None,
        meta_json: dict | list | None = None,
    ) -> Artifact:
        """
        Read an existing pipeline output file (CSV, JSON, Markdown, etc.) and store a managed copy.

        Infers :class:`~backend.models.enums.ArtifactKind` and MIME type from the file suffix.
        """
        path = Path(source_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(str(path))
        data = path.read_bytes()
        kind, mime = infer_artifact_kind_and_mime(path)
        provenance_meta = self._pipeline_source_provenance(
            path=path,
            analysis_run_id=analysis_run_id,
        )
        merged_meta: dict | list | None
        if meta_json is None:
            merged_meta = provenance_meta
        elif isinstance(meta_json, dict):
            merged_meta = {**meta_json, **provenance_meta}
        else:
            merged_meta = meta_json
        return self.save_bytes(
            data,
            role_key=role_key,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            run_step_id=run_step_id,
            kind=kind,
            mime_type=mime,
            filename_suffix=path.suffix,
            meta_json=merged_meta,
        )

    def ingest_pipeline_paths(
        self,
        role_to_path: Mapping[str, Path | str],
        *,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        run_step_id: UUID | None = None,
    ) -> list[Artifact]:
        """
        Ingest multiple on-disk artifacts (e.g. ``OrchestrationOutput.artifact_paths``).

        *role_to_path* maps logical role keys (``panel_csv``, ``report_md``, …) to paths.
        """
        out: list[Artifact] = []
        for role_key, p in role_to_path.items():
            out.append(
                self.ingest_pipeline_file(
                    p,
                    role_key=role_key,
                    analysis_run_id=analysis_run_id,
                    evaluation_run_id=evaluation_run_id,
                    run_step_id=run_step_id,
                )
            )
        return out

    def ingest_json_payload(
        self,
        payload: dict | list,
        *,
        role_key: str,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        run_step_id: UUID | None = None,
        meta_json: dict | list | None = None,
    ) -> Artifact:
        """Serialize a JSON-serializable structure to UTF-8 bytes and store it."""
        raw = json.dumps(payload, indent=2, default=str).encode("utf-8")
        return self.save_bytes(
            raw,
            role_key=role_key,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            run_step_id=run_step_id,
            kind=ArtifactKind.json,
            mime_type="application/json",
            filename_suffix=".json",
            meta_json=meta_json,
        )

    def ingest_text_document(
        self,
        text: str,
        *,
        role_key: str,
        analysis_run_id: UUID | None = None,
        evaluation_run_id: UUID | None = None,
        run_step_id: UUID | None = None,
        filename_suffix: str = ".md",
        mime_type: str = "text/markdown",
        kind: ArtifactKind = ArtifactKind.document,
        meta_json: dict | list | None = None,
    ) -> Artifact:
        """Store a Markdown or plain-text report string."""
        data = text.encode("utf-8")
        return self.save_bytes(
            data,
            role_key=role_key,
            analysis_run_id=analysis_run_id,
            evaluation_run_id=evaluation_run_id,
            run_step_id=run_step_id,
            kind=kind,
            mime_type=mime_type,
            filename_suffix=filename_suffix,
            meta_json=meta_json,
        )

    def get(self, artifact_id: UUID) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def require(self, artifact_id: UUID) -> Artifact:
        row = self.get(artifact_id)
        if row is None:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return row

    def load_bytes(self, artifact_id: UUID) -> bytes:
        """Read stored content for an artifact row."""
        row = self.require(artifact_id)
        return read_bytes(row.storage_uri, settings=self._settings)

    @contextmanager
    def open_content(self, artifact_id: UUID) -> Iterator[BinaryIO]:
        """Stream stored content (avoids loading entire file into memory)."""
        row = self.require(artifact_id)
        with open_reader(row.storage_uri, settings=self._settings) as fh:
            yield fh

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[Artifact]:
        return self._artifacts.list_for_analysis_run(analysis_run_id)

    def list_for_run_step(self, run_step_id: UUID) -> list[Artifact]:
        return self._artifacts.list_for_run_step(run_step_id)

    def list_for_evaluation_run(self, evaluation_run_id: UUID) -> list[Artifact]:
        return self._artifacts.list_for_evaluation_run(evaluation_run_id)

    def list_storage_keys_for_analysis_run(self, analysis_run_id: UUID) -> list[str]:
        """Raw object keys under the analysis-run prefix (storage reconciliation)."""
        prefix = f"artifacts/analysis_runs/{analysis_run_id}"
        return self._store.list_keys_under(prefix)

    def list_storage_keys_for_evaluation_run(self, evaluation_run_id: UUID) -> list[str]:
        prefix = f"artifacts/evaluation_runs/{evaluation_run_id}"
        return self._store.list_keys_under(prefix)

    def delete(self, artifact_id: UUID) -> None:
        """Remove DB row and delete backing bytes."""
        row = self.get(artifact_id)
        if row is None:
            return
        uri = row.storage_uri
        self._artifacts.delete(row)
        self._artifacts.flush()
        delete_at_uri(uri, settings=self._settings)
