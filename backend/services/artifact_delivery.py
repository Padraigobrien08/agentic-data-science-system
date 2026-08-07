"""Pure helpers for artifact HTTP delivery (filenames, disposition, preview eligibility)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.models.enums import ArtifactKind

if TYPE_CHECKING:
    from backend.models.artifact import Artifact

# Normalized lowercase MIME types suitable for UTF-8 text preview.
_PREVIEW_MIME_PREFIXES: tuple[str, ...] = ("text/",)
_PREVIEW_MIME_EXACT: frozenset[str] = frozenset(
    {
        "application/json",
        "application/jsonl",
        "application/x-ndjson",
    }
)

#: RFC 6839 structured syntax suffix: ``application/vnd.chart+json`` and friends are JSON,
#: so they are just as previewable as ``application/json``. Without this, a vendor JSON type
#: (the agentic loop emits chart specs as ``application/vnd.chart+json``) is rejected with a
#: 415 even though its bytes are plain JSON text.
_PREVIEW_MIME_SUFFIXES: tuple[str, ...] = ("+json",)

_DISPOSITION_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def artifact_previewable(row: Artifact) -> bool:
    """
    True if the preview endpoint should accept this artifact (UTF-8 text-oriented).

    Rules are documented in ``docs/artifact-delivery.md`` (``text/*``, selected JSON types,
    any ``+json`` structured-suffix type, or kind fallback when ``mime_type`` is empty).
    """
    mt = (row.mime_type or "").strip().lower()
    if mt:
        if mt in _PREVIEW_MIME_EXACT:
            return True
        if mt.startswith(_PREVIEW_MIME_PREFIXES):
            return True
        if mt.endswith(_PREVIEW_MIME_SUFFIXES):
            return True
        return False
    # No MIME: fall back to kind hints from ingest layer.
    return row.kind in (ArtifactKind.document, ArtifactKind.json, ArtifactKind.tabular)


def effective_media_type(row: Artifact) -> str:
    """``Content-Type`` for the object bytes."""
    mt = (row.mime_type or "").strip()
    return mt if mt else "application/octet-stream"


def default_inline_disposition(row: Artifact) -> bool:
    """Prefer inline viewing in browser for obvious text/JSON types."""
    mt = effective_media_type(row).lower()
    if mt.startswith("text/"):
        return True
    if mt in _PREVIEW_MIME_EXACT:
        return True
    return False


def artifact_content_filename(row: Artifact) -> str:
    """
    ASCII-safe suggested filename (no path segments).

    Uses ``role_key`` plus an extension inferred from MIME / kind.
    """
    base = _DISPOSITION_SAFE.sub("_", (row.role_key or "artifact").strip())[:120] or "artifact"
    ext = _extension_for_artifact(row)
    name = f"{base}{ext}"
    return name[:200]


def _extension_for_artifact(row: Artifact) -> str:
    mt = effective_media_type(row).lower()
    if mt == "text/markdown":
        return ".md"
    if mt == "text/plain":
        return ".txt"
    if mt == "text/csv":
        return ".csv"
    if mt == "text/tab-separated-values":
        return ".tsv"
    if mt in ("application/json", "application/jsonl", "application/x-ndjson"):
        return ".json"
    if row.kind == ArtifactKind.tabular:
        return ".csv"
    if row.kind == ArtifactKind.json:
        return ".json"
    if row.kind == ArtifactKind.document:
        return ".txt"
    return ".bin"


def build_content_disposition(*, row: Artifact, inline: bool) -> str:
    """RFC 6266-style ``Content-Disposition`` value with ASCII ``filename``."""
    fname = artifact_content_filename(row)
    disp = "inline" if inline else "attachment"
    # Escape quotes in filename (should not occur after sanitization).
    safe = fname.replace("\\", "\\\\").replace('"', "'")
    return f'{disp}; filename="{safe}"'
