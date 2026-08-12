"""Versioned API routes."""

from fastapi import APIRouter, Depends

from backend.api.auth_deps import get_current_active_user
from backend.api.routes import (
    artifacts,
    auth,
    conversations,
    demos,
    evaluations,
    health,
    interest,
    investigations,
    projects,
    runs,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(interest.router)
# Public by design: the replay tier is the one read surface with no account. Authorization is
# publication (``Investigation.demo_slug``), enforced per request in the route's service —
# so this must stay *outside* the authenticated group below.
api_router.include_router(demos.router)
api_router.include_router(projects.router, dependencies=[Depends(get_current_active_user)])
api_router.include_router(conversations.router, dependencies=[Depends(get_current_active_user)])
api_router.include_router(runs.router, dependencies=[Depends(get_current_active_user)])
api_router.include_router(evaluations.router, dependencies=[Depends(get_current_active_user)])
api_router.include_router(artifacts.router, dependencies=[Depends(get_current_active_user)])
api_router.include_router(investigations.router, dependencies=[Depends(get_current_active_user)])
