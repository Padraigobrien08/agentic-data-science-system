"""Public landing-page interest capture (unauthenticated)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.deps import DbSession
from backend.api.rate_limit import enforce_auth_rate_limit
from backend.models.interest_signal import InterestSignal
from backend.schemas.interest import InterestAck, InterestCreate

router = APIRouter(tags=["interest"])

# Reuse the auth sliding-window limiter to blunt spam on this open endpoint.
RateLimit = Annotated[None, Depends(enforce_auth_rate_limit)]


@router.post("/interest", response_model=InterestAck, status_code=201)
def register_interest(body: InterestCreate, db: DbSession, _rate_limit: RateLimit = None) -> InterestAck:
    db.add(
        InterestSignal(
            email=str(body.email).strip().lower(),
            note=body.note,
            source=body.source or "landing",
        )
    )
    db.commit()
    return InterestAck()
