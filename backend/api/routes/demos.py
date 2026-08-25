"""
Public replay tier — recorded investigations, readable without an account.

This is the **only unauthenticated read surface in the product**, so it is deliberately small
and deliberately read-only: list published demos, read one, and read the artifacts behind its
evidence. There is no way to start work, spend budget, or reach an unpublished row from here.

Authorization is publication, computed per request in
:mod:`backend.services.demo_publication_service` — an artifact is public iff it belongs to the
analysis run of an investigation that currently holds a ``demo_slug``. Unpublishing revokes
the investigation and every artifact behind it at once.

Registered outside the authenticated router in ``backend.api.router``; see
``docs/decisions/2026-08-11-showcase-direction.md`` (D3, S1).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.api.deps import ArtifactServiceDep, DbSession
from backend.api.routes.artifacts import build_artifact_preview, stream_artifact_content
from backend.schemas.artifact_content import ArtifactPreviewResponse
from backend.schemas.demo_capture import DemoChatThread, build_demo_chat
from backend.schemas.investigation import (
    InvestigationDetail,
    InvestigationSummary,
    build_detail,
    build_summary,
)
from backend.services.demo_publication_service import (
    DemoNotFound,
    get_published,
    get_published_artifact,
    get_published_conversations,
    list_published,
)

router = APIRouter(prefix="/demos", tags=["demos"])


def _not_found(slug: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"No published demo for {slug!r}")


@router.get("", response_model=list[InvestigationSummary])
def list_demos(db: DbSession) -> list[InvestigationSummary]:
    """Published recorded investigations, oldest first. Unauthenticated."""
    return [build_summary(row) for row in list_published(db)]


@router.get("/{slug}", response_model=InvestigationDetail)
def get_demo(slug: str, db: DbSession) -> InvestigationDetail:
    """
    One published investigation in full: hypotheses, evidence, decisions, critiques,
    experiments, conclusion, and timeline. Unauthenticated.
    """
    try:
        row = get_published(db, slug)
    except DemoNotFound as exc:
        raise _not_found(slug) from exc
    return build_detail(row)


@router.get("/{slug}/chat", response_model=list[DemoChatThread])
def get_demo_chat(slug: str, db: DbSession) -> list[DemoChatThread]:
    """
    The conversation recorded against a published demo. Unauthenticated.

    Only the turns — never the model payloads behind them, which stay admin-gated. The two
    used to travel together in one bundle, which meant a live deployment could not show the
    question a run was asked without also exposing raw prompts and responses. They are
    different things with different audiences, so they are served separately.

    An empty list is a normal answer: runs recorded before chat capture have no thread.
    """
    try:
        conversations = get_published_conversations(db, slug)
    except DemoNotFound as exc:
        raise _not_found(slug) from exc
    return build_demo_chat(conversations)


@router.get("/{slug}/artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def get_demo_artifact_preview(
    slug: str,
    artifact_id: UUID,
    db: DbSession,
    art_svc: ArtifactServiceDep,
) -> ArtifactPreviewResponse:
    """Bounded text/JSON preview of an artifact behind a published demo."""
    try:
        row = get_published_artifact(db, slug, artifact_id)
    except DemoNotFound as exc:
        raise _not_found(slug) from exc
    return build_artifact_preview(row, settings=art_svc.settings)


@router.get("/{slug}/artifacts/{artifact_id}/content")
def get_demo_artifact_content(
    slug: str,
    artifact_id: UUID,
    db: DbSession,
    art_svc: ArtifactServiceDep,
    disposition: Annotated[
        Literal["inline", "attachment", "auto"],
        Query(description="``auto``: inline for text/json-like MIME types, else attachment."),
    ] = "auto",
) -> StreamingResponse:
    """Stream the bytes of an artifact behind a published demo."""
    try:
        row = get_published_artifact(db, slug, artifact_id)
    except DemoNotFound as exc:
        raise _not_found(slug) from exc
    return stream_artifact_content(row, settings=art_svc.settings, disposition=disposition)
