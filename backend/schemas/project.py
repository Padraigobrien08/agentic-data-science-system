"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.schemas.common import OrmSchema, TimestampedRead


class ProjectCreate(OrmSchema):
    name: str = Field(max_length=256)
    slug: str | None = Field(default=None, max_length=128)
    description: str | None = None
    settings_json: dict | list | None = None


class ProjectUpdate(OrmSchema):
    name: str | None = Field(default=None, max_length=256)
    slug: str | None = Field(default=None, max_length=128)
    description: str | None = None
    settings_json: dict | list | None = None
    archived_at: datetime | None = None


class ProjectRead(TimestampedRead):
    id: UUID
    owner_user_id: UUID
    name: str
    slug: str | None
    description: str | None
    settings_json: dict | list | None = None
    archived_at: datetime | None
