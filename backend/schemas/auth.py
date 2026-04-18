"""Auth request/response bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AuthRegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)
    display_name: str | None = Field(default=None, max_length=256)


class AuthBootstrapBody(AuthRegisterBody):
    pass


class AuthLoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AccessTokenResponse(BaseModel):
    """OAuth2-style bearer token response (explicit fields for clients)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds.")


class AuthCapabilitiesResponse(BaseModel):
    """Coarse public auth state for truthful onboarding surfaces."""

    allow_open_registration: bool
    bootstrap_required: bool
    bootstrap_completed: bool
