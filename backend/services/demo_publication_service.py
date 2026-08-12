"""
The unauthenticated replay tier: recorded investigations published by slug.

Publishing is the *only* way anything in this system becomes readable without a token, so the
authorization rule is deliberately narrow and computed at request time rather than stored as a
flag on each reachable row:

    an artifact is public **iff** it belongs to the analysis run of an investigation that
    currently has a ``demo_slug``.

Two consequences worth stating. Clearing the slug revokes the investigation *and* every
artifact behind it in the same instant — there is no second flag to remember. And a newly
written artifact on a published run is public the moment it exists, which is correct here
(a published demo is frozen) but is why publishing is an operator action against a finished
run rather than something a user can trigger.

See ``docs/decisions/2026-08-11-showcase-direction.md`` (D3, S1).
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.artifact import Artifact
from backend.models.investigation import Investigation

#: Lowercase, digits, single hyphens. Restrictive because the slug is a public URL segment
#: that gets written down in a README and typed by hand.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 64


class InvalidDemoSlug(ValueError):
    """The proposed slug is not a safe public URL segment."""


class DemoNotFound(LookupError):
    """No published demo for this slug — or it was unpublished."""


def validate_slug(slug: str) -> str:
    normalized = (slug or "").strip().lower()
    if not normalized:
        raise InvalidDemoSlug("Slug must not be empty.")
    if len(normalized) > SLUG_MAX_LENGTH:
        raise InvalidDemoSlug(f"Slug must be at most {SLUG_MAX_LENGTH} characters.")
    if not SLUG_PATTERN.match(normalized):
        raise InvalidDemoSlug(
            "Slug must be lowercase alphanumeric words separated by single hyphens "
            f"(got {slug!r})."
        )
    return normalized


def list_published(db: Session) -> list[Investigation]:
    """Every published demo, oldest first so the ordering on the landing page is stable."""
    return list(
        db.scalars(
            select(Investigation)
            .where(Investigation.demo_slug.is_not(None))
            .order_by(Investigation.created_at.asc())
        ).all()
    )


def get_published(db: Session, slug: str) -> Investigation:
    """Resolve a published demo by slug, or raise :class:`DemoNotFound`."""
    normalized = (slug or "").strip().lower()
    row = db.scalar(select(Investigation).where(Investigation.demo_slug == normalized))
    if row is None:
        raise DemoNotFound(slug)
    return row


def get_published_artifact(db: Session, slug: str, artifact_id: UUID) -> Artifact:
    """
    Resolve an artifact readable through a published demo.

    Raises :class:`DemoNotFound` when the demo does not exist *or* when the artifact is not
    part of it — the same error for both, so a public caller cannot use this endpoint to probe
    which artifact ids exist. That mirrors the 404-for-unauthorized rule the authenticated API
    already applies in ``backend.api.access_checks``.
    """
    investigation = get_published(db, slug)
    if investigation.analysis_run_id is None:
        raise DemoNotFound(slug)
    row = db.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.analysis_run_id == investigation.analysis_run_id,
        )
    )
    if row is None:
        raise DemoNotFound(slug)
    return row


def publish(db: Session, investigation_id: UUID, slug: str) -> Investigation:
    """Attach a public slug to a finished investigation (operator action)."""
    normalized = validate_slug(slug)
    row = db.get(Investigation, investigation_id)
    if row is None:
        raise DemoNotFound(str(investigation_id))
    existing = db.scalar(select(Investigation).where(Investigation.demo_slug == normalized))
    if existing is not None and existing.id != investigation_id:
        raise InvalidDemoSlug(
            f"Slug {normalized!r} is already published for investigation {existing.id}. "
            "Unpublish it first, or choose another slug."
        )
    row.demo_slug = normalized
    db.flush()
    return row


def unpublish(db: Session, slug: str) -> Investigation:
    """Revoke public access. The investigation and its artifacts are private again at once."""
    row = get_published(db, slug)
    row.demo_slug = None
    db.flush()
    return row
