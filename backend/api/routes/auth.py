"""Registration, login, and current user (JWT bearer)."""

from __future__ import annotations

import secrets
import uuid
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import DbSession
from backend.api.rate_limit import enforce_auth_rate_limit
from backend.auth.tokens import create_access_token
from backend.config.settings import get_settings
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.auth import (
    AccessTokenResponse,
    AuthBootstrapBody,
    AuthCapabilitiesResponse,
    AuthLoginBody,
    AuthRegisterBody,
    GuestSessionResponse,
)
from backend.schemas.user import UserRead
from backend.security.passwords import hash_password, verify_password
from backend.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

# Starter tickers so a guest can ask a real question immediately.
_GUEST_DEMO_TICKERS = ["AAPL", "MSFT", "NVDA"]

# Applied to the unauthenticated write endpoints to blunt credential stuffing /
# registration spam / bootstrap-token brute forcing (see backend.api.rate_limit).
AuthRateLimit = Annotated[None, Depends(enforce_auth_rate_limit)]


@router.get("/capabilities", response_model=AuthCapabilitiesResponse)
def capabilities(db: DbSession) -> AuthCapabilitiesResponse:
    settings = get_settings()
    bootstrap_completed = db.scalar(select(User.id).where(User.is_admin.is_(True)).limit(1)) is not None
    return AuthCapabilitiesResponse(
        allow_open_registration=settings.allow_open_registration,
        bootstrap_required=not settings.allow_open_registration and not bootstrap_completed,
        bootstrap_completed=bootstrap_completed,
    )


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    body: AuthRegisterBody,
    db: DbSession,
    _rate_limit: AuthRateLimit = None,
) -> User:
    settings = get_settings()
    if not settings.allow_open_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    users = UserService(db)
    if users.get_by_email(str(body.email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        row = users.create_with_password(
            email=str(body.email),
            hashed_password=hash_password(body.password),
            display_name=body.display_name,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    db.refresh(row)
    return row


@router.post("/bootstrap", response_model=UserRead, status_code=201)
def bootstrap_admin(
    body: AuthBootstrapBody,
    db: DbSession,
    bootstrap_token: str | None = Header(default=None, alias="X-EDGAR-Bootstrap-Token"),
    _rate_limit: AuthRateLimit = None,
) -> User:
    settings = get_settings()
    configured_bootstrap_token = (
        settings.bootstrap_admin_token.get_secret_value()
        if settings.bootstrap_admin_token is not None
        else ""
    )
    if not configured_bootstrap_token.strip():
        raise HTTPException(status_code=503, detail="Bootstrap admin token is not configured")
    if not bootstrap_token or not compare_digest(bootstrap_token, configured_bootstrap_token):
        raise HTTPException(status_code=401, detail="Invalid bootstrap token")
    if db.scalar(select(User.id).where(User.is_admin.is_(True)).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Bootstrap already completed")

    users = UserService(db)
    if users.get_by_email(str(body.email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        row = users.create_with_password(
            email=str(body.email),
            hashed_password=hash_password(body.password),
            display_name=body.display_name,
            is_admin=True,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    db.refresh(row)
    return row


@router.post("/login", response_model=AccessTokenResponse)
def login(body: AuthLoginBody, db: DbSession, _rate_limit: AuthRateLimit = None) -> AccessTokenResponse:
    settings = get_settings()
    users = UserService(db)
    user = users.get_by_email(str(body.email))
    if user is None or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token, expires_in = create_access_token(user_id=user.id, settings=settings)
    return AccessTokenResponse(access_token=token, expires_in=expires_in)


@router.post("/guest", response_model=GuestSessionResponse, status_code=201)
def guest_session(db: DbSession, _rate_limit: AuthRateLimit = None) -> GuestSessionResponse:
    """Provision an isolated throwaway guest account + demo workspace and return a token.

    Lets a visitor try the product with no sign-up. Off unless ``allow_guest_demo`` is set,
    because auto-provisioning accounts is a spam vector on a public deployment.
    """
    settings = get_settings()
    if not settings.allow_guest_demo:
        raise HTTPException(status_code=403, detail="Guest demo access is disabled")

    users = UserService(db)
    email = f"guest-{uuid.uuid4().hex[:16]}@demo.local"
    try:
        user = users.create_with_password(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            display_name="Guest",
        )
        db.flush()
        project = Project(
            owner_user_id=user.id,
            name="Demo workspace",
            description="Sandbox for exploring EDGAR analysis without an account.",
            tickers=list(_GUEST_DEMO_TICKERS),
        )
        db.add(project)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not create a guest session") from None
    db.refresh(project)

    token, expires_in = create_access_token(user_id=user.id, settings=settings)
    return GuestSessionResponse(access_token=token, expires_in=expires_in, project_id=project.id)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUserDep) -> User:
    return user
