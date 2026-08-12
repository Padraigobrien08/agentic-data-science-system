"""User persistence for registration and lookup."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.enums import UserAccessTier
from backend.models.user import User


class UserService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        return self._session.scalar(select(User).where(User.email == normalized))

    def create_with_password(
        self,
        *,
        email: str,
        hashed_password: str,
        display_name: str | None,
        is_admin: bool = False,
        access_tier: UserAccessTier = UserAccessTier.standard,
    ) -> User:
        normalized = email.strip().lower()
        row = User(
            email=normalized,
            display_name=display_name,
            hashed_password=hashed_password,
            is_admin=is_admin,
            access_tier=access_tier,
        )
        self._session.add(row)
        self._session.flush()
        return row
