"""FastAPI dependencies: JWT bearer → :class:`~backend.models.user.User`."""

from __future__ import annotations

import hmac
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.deps import DbSession
from backend.auth.tokens import decode_access_token
from backend.config.settings import get_settings
from backend.models.user import User
from backend.services.user_service import UserService

_bearer = HTTPBearer(auto_error=False)
_ops_bearer = HTTPBearer(auto_error=False)


def _bearer_auth_error(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials.strip():
        raise _bearer_auth_error()
    settings = get_settings()
    try:
        user_id = decode_access_token(creds.credentials.strip(), settings=settings)
    except jwt.PyJWTError:
        raise _bearer_auth_error("Invalid or expired token") from None
    user = UserService(db).get(user_id)
    if user is None:
        raise _bearer_auth_error("User no longer exists")
    return user


def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


def get_ops_token(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_ops_bearer)],
) -> str:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials.strip():
        raise _bearer_auth_error()

    settings = get_settings()
    expected = settings.ops_api_token.get_secret_value() if settings.ops_api_token else ""
    provided = creds.credentials.strip()
    if not expected or not hmac.compare_digest(provided, expected):
        raise _bearer_auth_error()
    return provided


def require_ops_token(
    token: Annotated[str, Depends(get_ops_token)],
) -> str:
    return token


OpsTokenDep = Annotated[str, Depends(require_ops_token)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]

__all__ = [
    "CurrentUserDep",
    "OpsTokenDep",
    "UserServiceDep",
    "get_current_active_user",
    "get_current_user",
    "get_ops_token",
    "get_user_service",
    "require_ops_token",
]
