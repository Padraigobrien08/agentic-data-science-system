"""Declarative base for ORM models — import side effects register tables on metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""
