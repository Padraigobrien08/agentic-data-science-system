"""Shared Pydantic configuration for API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmSchema(BaseModel):
    """Load from SQLAlchemy models via ``model_validate``."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class TimestampedRead(OrmSchema):
    created_at: datetime
    updated_at: datetime
