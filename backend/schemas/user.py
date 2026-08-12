"""User request/response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import EmailStr, Field

from backend.models.enums import UserAccessTier
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
    is_admin: bool
    access_tier: UserAccessTier = Field(
        default=UserAccessTier.standard,
        description="Spend entitlement: which engine this account may run and under which ceiling.",
    )
    preferences_json: dict | list | None = None
