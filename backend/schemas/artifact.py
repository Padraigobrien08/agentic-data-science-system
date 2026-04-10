"""Artifact metadata schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import ArtifactKind
from backend.schemas.common import OrmSchema, TimestampedRead


class ArtifactCreate(OrmSchema):
    role_key: str = Field(max_length=128)
    kind: ArtifactKind = ArtifactKind.other
    storage_uri: str = Field(max_length=2048)
    mime_type: str | None = Field(default=None, max_length=256)
    byte_size: int | None = Field(default=None, ge=0)
    content_sha256: str | None = Field(default=None, max_length=64)
    meta_json: dict | list | None = None
    analysis_run_id: UUID | None = None
    evaluation_run_id: UUID | None = None
    run_step_id: UUID | None = None


class ArtifactUpdate(OrmSchema):
    storage_uri: str | None = Field(default=None, max_length=2048)
    mime_type: str | None = Field(default=None, max_length=256)
    byte_size: int | None = Field(default=None, ge=0)
    content_sha256: str | None = Field(default=None, max_length=64)
    meta_json: dict | list | None = None
    run_step_id: UUID | None = None


class ArtifactRead(TimestampedRead):
    id: UUID
    analysis_run_id: UUID | None
    evaluation_run_id: UUID | None
    run_step_id: UUID | None
    role_key: str
    kind: ArtifactKind
    storage_uri: str
    mime_type: str | None
    byte_size: int | None
    content_sha256: str | None
    meta_json: dict | list | None = None
