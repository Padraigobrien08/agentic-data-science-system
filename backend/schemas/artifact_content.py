"""API models for artifact byte delivery and text preview."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArtifactPreviewResponse(BaseModel):
    """
    Bounded UTF-8 text (or pretty-printed JSON) for browser preview.

    Binary or non-previewable types return **415** from the preview route instead.
    """

    format: Literal["text", "json"] = Field(description="``json`` when payload parsed as JSON; else ``text``.")
    text: str = Field(description="UTF-8 preview string (may be truncated).")
    truncated: bool = Field(description="True when more bytes exist beyond the server preview cap.")
    mime_type: str | None = Field(description="Artifact MIME type from metadata.")
    total_bytes: int | None = Field(default=None, description="Declared size from metadata when known.")
    json_valid: bool | None = Field(
        default=None,
        description="When ``format`` is ``json``, whether parsing succeeded.",
    )
