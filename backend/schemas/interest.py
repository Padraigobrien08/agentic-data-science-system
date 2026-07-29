"""Interest-signal (landing lead capture) request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class InterestCreate(BaseModel):
    email: EmailStr
    note: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=64)


class InterestAck(BaseModel):
    status: str = "received"
