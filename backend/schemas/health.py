"""API response models for health and readiness checks."""

from datetime import datetime

from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database connectivity slice."""

    ok: bool = Field(description="True when a trivial query succeeded")
    detail: str | None = Field(default=None, description="Error message when ok is false")


class LlmHealth(BaseModel):
    """Whether agent LLM calls (critic/report) would run in this process — config only, no live probe."""

    provider: str = Field(description="Normalized EDGAR_BACKEND_LLM_PROVIDER (e.g. off, openai)")
    ready: bool = Field(
        description="True when get_chat_completion_provider() would succeed (provider + key configured)",
    )
    message: str = Field(
        description="Always set: what is wrong, or confirmation when ready (avoids null-only hints)",
    )


class HealthResponse(BaseModel):
    """Service health — suitable for load balancers and ops dashboards."""

    status: str = Field(default="ok", description="Overall status string")
    version: str = Field(description="API package version")
    database: DatabaseHealth
    llm: LlmHealth = Field(
        description="LLM agent configuration in this API process (worker has its own env — check logs / same vars)",
    )


class WorkerHealthResponse(BaseModel):
    """Queue snapshot + last finished job (from DB). Helps spot a running-but-stuck worker."""

    queue_depth: int = Field(description="Pending jobs eligible for claim")
    jobs_running_lease_ok: int = Field(description="Running jobs with a valid lease")
    jobs_running_stale_lease: int = Field(description="Running jobs with missing/expired lease")
    open_jobs_on_cancelled_run: int = Field(description="Open jobs tied to a cancelled run")
    last_terminal_job_at: datetime | None = Field(
        default=None,
        description="Max updated_at among completed/failed/cancelled execution jobs",
    )
    age_seconds_since_last_terminal_job: float | None = Field(
        default=None,
        description="Seconds since last_terminal_job_at (UTC), if known",
    )
    stale_running_jobs: bool = Field(description="True if any running job has a stale lease")
    backlog_without_active_lease: bool = Field(
        description="True if work is queued but no job currently holds a valid running lease",
    )
