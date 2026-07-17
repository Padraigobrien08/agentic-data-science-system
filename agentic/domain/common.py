"""
Shared building blocks for the investigation domain.

All domain entities inherit :class:`DomainModel` (Pydantic, ``extra="forbid"``,
JSON-serializable) and get stable, explicit, type-prefixed ids from
:func:`new_id`. Nothing here depends on SQLAlchemy or any framework — these are
pure, framework-independent value objects.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

#: Package-wide schema version. Bump when the serialized shape of domain
#: entities changes in a backward-incompatible way.
DOMAIN_SCHEMA_VERSION = "1"


class DomainModel(BaseModel):
    """Base for every domain entity: strict, serializable, framework-free."""

    model_config = ConfigDict(extra="forbid")


def utc_now() -> datetime:
    """Timezone-aware current time (UTC). Serializes to ISO-8601."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """
    Stable, explicit id with a type prefix, e.g. ``hyp_3f2a...``.

    Ids are generated once at construction and never reassigned, so they are
    safe to reference across serialization boundaries.
    """
    return f"{prefix}_{uuid4().hex}"
