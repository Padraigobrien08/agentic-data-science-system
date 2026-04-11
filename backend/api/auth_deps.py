"""FastAPI dependencies: JWT bearer → :class:`~backend.models.user.User`."""

from __future__ import annotations

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


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials.strip():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    try:
        user_id = decode_access_token(creds.credentials.strip(), settings=settings)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    user = UserService(db).get(user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_active_user)]

__all__ = [
    "CurrentUserDep",
    "UserServiceDep",
    "get_current_active_user",
    "get_current_user",
    "get_user_service",
]
