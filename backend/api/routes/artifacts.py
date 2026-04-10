"""Artifact metadata (Phase A — no binary download endpoint yet)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.api.deps import ArtifactServiceDep
from backend.schemas.api_phase_a import ArtifactDetailResponse, artifact_to_detail

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact(
    artifact_id: UUID,
    art_svc: ArtifactServiceDep,
    include_meta: bool = Query(
        False,
        description="When true, include meta_json (may be large)",
    ),
) -> ArtifactDetailResponse:
    row = art_svc.get(artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact_to_detail(row, include_meta=include_meta)
