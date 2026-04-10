"""Shared SQLAlchemy column helpers."""

from __future__ import annotations

import enum
from typing import Any, TypeVar

from sqlalchemy import Enum as SQLEnum

E = TypeVar("E", bound=enum.Enum)


def str_enum_column(enum_class: type[E], *, name: str | None = None, **kwargs: Any) -> Any:
    """String-stored Enum (no native PG enum type required; SQLite-friendly)."""
    return SQLEnum(
        enum_class,
        values_callable=lambda x: [m.value for m in x],
        native_enum=False,
        name=name,
        **kwargs,
    )
