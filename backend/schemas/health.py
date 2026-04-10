"""API response models for health and readiness checks."""

from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database connectivity slice."""

    ok: bool = Field(description="True when a trivial query succeeded")
    detail: str | None = Field(default=None, description="Error message when ok is false")


class HealthResponse(BaseModel):
    """Service health — suitable for load balancers and ops dashboards."""

    status: str = Field(default="ok", description="Overall status string")
    version: str = Field(description="API package version")
    database: DatabaseHealth
