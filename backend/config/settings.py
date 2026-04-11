"""Application settings — env-driven, safe defaults for local development."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DB_POSTURE_LOGGED = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EDGAR_BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EDGAR Analytics API"
    api_v1_prefix: str = "/v1"
    debug: bool = False

    # Auth (JWT HS256). Set EDGAR_BACKEND_JWT_SECRET in production.
    jwt_secret: SecretStr = Field(
        default=SecretStr("dev-only-set-edgar-backend-jwt-secret-min-32-chars"),
        description="HMAC secret for access tokens (use a long random value in production).",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(
        default=720,
        ge=5,
        le=60 * 24 * 14,
        description="Access token lifetime in minutes.",
    )
    allow_open_registration: bool = Field(
        default=True,
        description="When false, POST /v1/auth/register returns 403.",
    )

    # Default file SQLite is for quick local API/tests without Docker. The documented stack uses Postgres
    # (see docker-compose.yml and docs/local-stack.md). Set EDGAR_BACKEND_ALLOW_SQLITE=false in production.
    database_url: str = Field(
        default=f"sqlite:///{_REPO_ROOT / 'data' / 'backend.db'}",
        description=(
            "SQLAlchemy URL. Recommended for real deployments: Postgres "
            "(same as Docker Compose). Default here is a local SQLite file when unset."
        ),
    )
    allow_sqlite: bool = Field(
        default=True,
        description=(
            "When false, SQLite URLs are rejected (use Postgres). "
            "Set EDGAR_BACKEND_ALLOW_SQLITE=false alongside a Postgres URL in production."
        ),
    )

    # Root directory for ``local:`` artifact blobs (see ``backend.storage``)
    artifact_storage_root: Path = Field(
        default=_REPO_ROOT / "data" / "artifact_storage",
        description="Filesystem root for LocalFilesystemStore object keys",
    )

    worker_poll_interval_s: float = Field(
        default=2.0,
        ge=0.1,
        description="Sleep between DB queue polls when no job is available (``python -m backend.worker``)",
    )

    worker_metrics_port: int = Field(
        default=0,
        ge=0,
        le=65535,
        description=(
            "When > 0, the worker process exposes Prometheus metrics on this port "
            "(``prometheus_client.start_http_server``). API ``GET /metrics`` still holds DB queue gauges."
        ),
    )

    run_job_max_attempts: int = Field(
        default=4,
        ge=1,
        le=100,
        description="Max fresh execution attempts per queue row (attempt_count increments on each new claim).",
    )
    run_job_lease_seconds: float = Field(
        default=900.0,
        ge=30.0,
        le=86400.0,
        description="While a job is running, lease_expires_at must stay in the future or the job becomes reclaimable.",
    )

    # LLM (chat completions) — see ``backend.llm``
    llm_provider: str = Field(
        default="off",
        description="``off`` disables factory; ``openai`` uses the OpenAI API (requires API key).",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key (EDGAR_BACKEND_OPENAI_API_KEY)",
    )
    openai_base_url: str | None = Field(
        default=None,
        description="Optional OpenAI-compatible base URL (Azure, proxies)",
    )
    openai_timeout_s: float = Field(
        default=120.0,
        ge=5.0,
        description="HTTP timeout for OpenAI chat completion requests",
    )

    # Intent / planning agents (``backend.agents``) — prompts under versioned files on disk
    agent_completion_model: str = Field(
        default="gpt-5.4-mini",
        description="Chat model for intent, planning, critic, and report agents (``chat.completions`` model id).",
    )
    agent_intent_prompt_version: str = Field(
        default="1.0.0",
        description="Prompt file version directory under ``backend/agents/prompts/intent/``",
    )
    agent_planning_prompt_version: str = Field(
        default="1.0.0",
        description="Prompt file version directory under ``backend/agents/prompts/planning/``",
    )
    agent_critic_prompt_version: str = Field(
        default="1.0.0",
        description="Prompt file version under ``backend/agents/prompts/critic/``",
    )
    agent_report_prompt_version: str = Field(
        default="1.0.0",
        description="Prompt file version under ``backend/agents/prompts/report/``",
    )

    # Observability (structured logs + Prometheus /metrics)
    observability_json_logs: bool = Field(
        default=True,
        description="Emit one JSON object per log line (stderr). Set false for console rendering.",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level: DEBUG, INFO, WARNING, ERROR",
    )

    otel_service_name: str | None = Field(
        default=None,
        description="OpenTelemetry ``service.name`` (falls back to OTEL_SERVICE_NAME env or edgar-backend)",
    )

    @model_validator(mode="after")
    def _openai_api_key_from_unprefixed_env(self) -> Settings:
        """Accept ``OPENAI_API_KEY`` when ``EDGAR_BACKEND_OPENAI_API_KEY`` is unset (common convention)."""
        cur = self.openai_api_key.get_secret_value() if self.openai_api_key else ""
        if str(cur).strip():
            return self
        alt = os.environ.get("OPENAI_API_KEY", "").strip()
        if alt:
            object.__setattr__(self, "openai_api_key", SecretStr(alt))
        return self

    @model_validator(mode="after")
    def _production_sanity(self) -> Settings:
        if not self.debug and len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError(
                "EDGAR_BACKEND_JWT_SECRET must be at least 32 characters when EDGAR_BACKEND_DEBUG is false.",
            )
        if not self.allow_sqlite:
            driver = make_url(self.database_url).drivername
            if driver == "sqlite":
                raise ValueError(
                    "EDGAR_BACKEND_ALLOW_SQLITE is false but EDGAR_BACKEND_DATABASE_URL is SQLite. "
                    "Use Postgres, e.g. postgresql+psycopg2://user:pass@host:5432/dbname "
                    "(Docker Compose sets this automatically)."
                )
        return self

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def _empty_openai_base_url_is_none(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_sqlite_url(cls, v: object) -> object:
        if isinstance(v, str) and v.startswith("sqlite:///") and not v.startswith("sqlite:////"):
            # sqlite:///relative -> absolute under repo root for predictable cwd
            rest = v.removeprefix("sqlite:///")
            if rest and not rest.startswith("/") and "://" not in rest:
                return f"sqlite:///{(_REPO_ROOT / rest).resolve()}"
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def log_database_posture_once(settings: Settings | None = None) -> None:
    """
    Log which database backend is active (once per process).

    SQLite triggers a clear WARNING so it is not mistaken for the Compose/Postgres default.
    """
    global _DB_POSTURE_LOGGED
    if _DB_POSTURE_LOGGED:
        return
    _DB_POSTURE_LOGGED = True

    import structlog

    s = settings if settings is not None else get_settings()
    log = structlog.get_logger("backend.database")
    url = make_url(s.database_url)
    if url.drivername == "sqlite":
        db_name = Path(url.database).name if url.database else "(memory)"
        log.warning(
            "database_backend_sqlite",
            database_backend="sqlite",
            sqlite_file=db_name,
            hint=(
                "SQLite is a convenience default for local dev without Docker. "
                "The documented full stack uses Postgres (docker-compose.yml → EDGAR_BACKEND_DATABASE_URL). "
                "Do not mix API on SQLite with worker on Postgres."
            ),
        )
    else:
        log.info(
            "database_backend",
            database_backend=url.drivername.split("+", 1)[0],
            host=url.host,
            database=url.database,
        )
