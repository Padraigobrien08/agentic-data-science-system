"""Artifact metadata and content delivery (streaming bytes + JSON preview)."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Iterator, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from backend.api.access_checks import require_artifact_readable
from backend.api.auth_deps import CurrentUserDep, require_admin_debug_access
from backend.api.deps import ArtifactServiceDep, DbSession
from backend.config.settings import Settings
from backend.models.artifact import Artifact
from backend.models.enums import ArtifactKind
from backend.schemas.api_phase_a import ArtifactDetailResponse, artifact_to_detail
from backend.schemas.artifact_content import ArtifactPreviewResponse
from backend.services.artifact_delivery import (
    artifact_previewable,
    build_content_disposition,
    default_inline_disposition,
    effective_media_type,
)
from backend.storage.resolver import open_reader
from backend.storage.types import InvalidStorageKey, ObjectNotFound, UnsupportedStorageUri

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

_PREVIEW_MAX_BYTES = 512 * 1024
_STREAM_CHUNK = 64 * 1024
_RETENTION_EXPIRED_DETAIL = "Artifact content expired by retention policy"


def _raise_if_blob_deleted(row: Artifact) -> None:
    if row.blob_deleted_at is not None:
        raise HTTPException(status_code=410, detail=_RETENTION_EXPIRED_DETAIL)


def _verify_storage_openable(row: Artifact, *, settings: Settings) -> None:
    try:
        with open_reader(row.storage_uri, settings=settings) as fh:
            fh.read(1)
    except ObjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Artifact content not found in storage") from exc
    except UnsupportedStorageUri as exc:
        logger.warning("Unsupported storage URI scheme for artifact %s", row.id)
        raise HTTPException(
            status_code=502,
            detail="Storage backend is not configured for this artifact",
        ) from exc
    except InvalidStorageKey as exc:
        logger.warning("Invalid storage key for artifact %s: %s", row.id, exc)
        raise HTTPException(status_code=502, detail="Invalid stored object locator") from exc
    except OSError as exc:
        logger.exception("Storage read error for artifact %s", row.id)
        raise HTTPException(status_code=502, detail="Could not read artifact from storage") from exc


def _byte_stream(row: Artifact, *, settings: Settings) -> Iterator[bytes]:
    try:
        with open_reader(row.storage_uri, settings=settings) as fh:
            while True:
                chunk = fh.read(_STREAM_CHUNK)
                if not chunk:
                    break
                yield chunk
    except ObjectNotFound:
        logger.error("Artifact %s disappeared during streaming", row.id)
        raise
    except (UnsupportedStorageUri, InvalidStorageKey, OSError):
        logger.exception("Streaming failed for artifact %s", row.id)
        raise


@router.get("/{artifact_id}/content")
def get_artifact_content(
    artifact_id: UUID,
    art_svc: ArtifactServiceDep,
    db: DbSession,
    user: CurrentUserDep,
    disposition: Annotated[
        Literal["inline", "attachment", "auto"],
        Query(description="``auto``: inline for text/json-like MIME types, else attachment."),
    ] = "auto",
) -> StreamingResponse:
    """
    Stream artifact bytes from the object store (``local:`` or future backends).

    Uses :func:`backend.storage.resolver.open_reader` — no raw filesystem paths in the response.
    """
    row = require_artifact_readable(db, art_svc, artifact_id, user.id)
    _raise_if_blob_deleted(row)
    settings = art_svc.settings
    _verify_storage_openable(row, settings=settings)

    if disposition == "auto":
        inline = default_inline_disposition(row)
    else:
        inline = disposition == "inline"

    media = effective_media_type(row)
    cd = build_content_disposition(row=row, inline=inline)

    headers: dict[str, str] = {
        "Content-Disposition": cd,
        "X-Content-Type-Options": "nosniff",
    }
    if row.content_sha256:
        headers["ETag"] = f'"{row.content_sha256}"'
    if row.byte_size is not None and row.byte_size >= 0:
        headers["Content-Length"] = str(row.byte_size)
    headers["Cache-Control"] = "private, no-cache"

    return StreamingResponse(
        _byte_stream(row, settings=settings),
        media_type=media,
        headers=headers,
    )


@router.get("/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def get_artifact_preview(
    artifact_id: UUID,
    art_svc: ArtifactServiceDep,
    db: DbSession,
    user: CurrentUserDep,
) -> ArtifactPreviewResponse:
    """
    Return a bounded UTF-8 text (or pretty JSON) preview for markdown/CSV/JSON/text artifacts.

    Zero-byte objects return ``text: ""`` with ``truncated: false``. See ``docs/artifact-delivery.md``
    for preview eligibility and response fields.

    Returns **415** when the artifact is not treated as text-previewable (e.g. binary).
    """
    row = require_artifact_readable(db, art_svc, artifact_id, user.id)
    _raise_if_blob_deleted(row)
    if not artifact_previewable(row):
        raise HTTPException(
            status_code=415,
            detail="Preview is not available for this media type; use GET …/content to download.",
        )

    settings = art_svc.settings
    _verify_storage_openable(row, settings=settings)

    try:
        with open_reader(row.storage_uri, settings=settings) as fh:
            raw = fh.read(_PREVIEW_MAX_BYTES + 1)
    except ObjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Artifact content not found in storage") from exc
    except UnsupportedStorageUri as exc:
        raise HTTPException(
            status_code=502,
            detail="Storage backend is not configured for this artifact",
        ) from exc
    except InvalidStorageKey as exc:
        raise HTTPException(status_code=502, detail="Invalid stored object locator") from exc
    except OSError as exc:
        logger.exception("Preview read failed for artifact %s", row.id)
        raise HTTPException(status_code=502, detail="Could not read artifact from storage") from exc

    truncated = len(raw) > _PREVIEW_MAX_BYTES
    raw = raw[:_PREVIEW_MAX_BYTES]
    text = raw.decode("utf-8", errors="replace")

    mt = (row.mime_type or "").strip().lower()
    json_valid: bool | None = None
    out_format: Literal["text", "json"] = "text"
    if mt == "application/json" or row.kind == ArtifactKind.json:
        try:
            parsed = json.loads(text)
            json_valid = True
            out_format = "json"
            text = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            json_valid = False
            out_format = "text"

    return ArtifactPreviewResponse(
        format=out_format,
        text=text,
        truncated=truncated,
        mime_type=row.mime_type,
        total_bytes=row.byte_size,
        json_valid=json_valid,
    )


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact(
    artifact_id: UUID,
    art_svc: ArtifactServiceDep,
    db: DbSession,
    user: CurrentUserDep,
    include_meta: bool = Query(
        False,
        description="When true, include meta_json (may be large)",
    ),
) -> ArtifactDetailResponse:
    row = require_artifact_readable(db, art_svc, artifact_id, user.id)
    if include_meta:
        require_admin_debug_access(user, feature="raw artifact metadata")
    return artifact_to_detail(row, include_meta=include_meta)
