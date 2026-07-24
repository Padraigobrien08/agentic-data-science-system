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


class EvaluationDependencyHealth(BaseModel):
    """Recent live/hybrid evaluation dependency truth."""

    state_known: bool = Field(
        description="True when recent evaluation dependency state was read successfully from the database",
    )
    sec_dependency_ok: bool | None = Field(
        default=None,
        description="True when no recent SEC dependency degradation is observed, false when degraded, null when unknown",
    )
    storage_dependency_ok: bool | None = Field(
        default=None,
        description="True when no recent storage dependency degradation is observed, false when degraded, null when unknown",
    )
    recent_degraded_case_count: int | None = Field(
        default=None,
        description="Recent live/hybrid evaluation cases carrying SEC or storage degradation evidence",
    )
    detail: str | None = Field(
        default=None,
        description="Operator-facing explanation when evaluation dependency state is degraded or unknown",
    )


class BackgroundDeliveryHealth(BaseModel):
    """User-safe runtime delivery posture for workspace chat."""

    delivery_mode: str = Field(
        description="Coarse chat delivery mode: sync_only, background_ready, or background_degraded",
    )
    background_available: bool = Field(
        description="True when chat can rely on background delivery as a healthy path",
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation for the current chat delivery posture",
    )


class HealthResponse(BaseModel):
    """Service health — suitable for load balancers and ops dashboards."""

    status: str = Field(default="ok", description="Overall status string")
    version: str = Field(description="API package version")
    database: DatabaseHealth
    llm: LlmHealth = Field(
        description="LLM agent configuration in this API process (worker has its own env — check logs / same vars)",
    )
    evaluation: EvaluationDependencyHealth = Field(
        description="Recent supported-evaluation dependency state derived from child-run-backed case results",
    )
    background_delivery: BackgroundDeliveryHealth = Field(
        description="User-safe chat delivery posture derived from runtime policy plus queue health",
    )
    agentic_engine_enabled: bool = Field(
        default=False,
        description="Whether the generalized agentic investigation engine is enabled in this process",
    )


class WorkerHealthResponse(BaseModel):
    """Queue snapshot + last finished job (from DB). Helps spot a running-but-stuck worker."""

    status: str = Field(default="ok", description="Overall worker queue observability status")
    database: DatabaseHealth = Field(description="Database dependency status for queue observability")
    evaluation: EvaluationDependencyHealth = Field(
        description="Recent supported-evaluation dependency state derived from child-run-backed case results",
    )
    queue_state_known: bool = Field(
        description="True when queue counts and flags come from a successful DB-backed read",
    )
    queue_depth: int | None = Field(
        default=None,
        description="Pending jobs eligible for claim when queue state is known",
    )
    jobs_running_lease_ok: int | None = Field(
        default=None,
        description="Running jobs with a valid lease when queue state is known",
    )
    jobs_running_stale_lease: int | None = Field(
        default=None,
        description="Running jobs with missing/expired lease when queue state is known",
    )
    open_jobs_on_cancelled_run: int | None = Field(
        default=None,
        description="Open jobs tied to a cancelled run when queue state is known",
    )
    last_terminal_job_at: datetime | None = Field(
        default=None,
        description="Max updated_at among completed/failed/cancelled execution jobs",
    )
    age_seconds_since_last_terminal_job: float | None = Field(
        default=None,
        description="Seconds since last_terminal_job_at (UTC), if known",
    )
    stale_running_jobs: bool | None = Field(
        default=None,
        description="True if any running job has a stale lease when queue state is known",
    )
    backlog_without_active_lease: bool | None = Field(
        default=None,
        description="True if work is queued but no job currently holds a valid running lease when queue state is known",
    )
