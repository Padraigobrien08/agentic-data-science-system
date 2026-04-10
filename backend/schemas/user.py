"""User request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from backend.schemas.common import OrmSchema, TimestampedRead


class UserCreate(OrmSchema):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=256)
    password: str | None = Field(default=None, min_length=8, description="Plain password; hashed server-side")


class UserUpdate(OrmSchema):
    display_name: str | None = Field(default=None, max_length=256)
    is_active: bool | None = None
    preferences_json: dict | list | None = None


class UserRead(TimestampedRead):
    id: UUID
    email: EmailStr
    display_name: str | None
    is_active: bool
    preferences_json: dict | list | None = None
