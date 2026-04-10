"""Versioned API routes."""

from fastapi import APIRouter

from backend.api.routes import artifacts, health, runs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(runs.router)
api_router.include_router(artifacts.router)
