"""JWT access tokens (HS256)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from backend.config.settings import Settings


def create_access_token(
    *,
    user_id: UUID,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)``."""
    now = datetime.now(tz=UTC)
    ttl = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    exp = now + ttl
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "typ": "access",
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, int(ttl.total_seconds())


def decode_access_token(token: str, *, settings: Settings) -> UUID:
    """Validate token and return user id. Raises ``jwt.PyJWTError`` on failure."""
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return UUID(str(payload["sub"]))
