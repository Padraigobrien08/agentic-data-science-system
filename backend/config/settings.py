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
BUILTIN_DEV_JWT_SECRET = "dev-only-set-edgar-backend-jwt-secret-min-32-chars"


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
        default=SecretStr(BUILTIN_DEV_JWT_SECRET),
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
        default=False,
        description="When false, POST /v1/auth/register returns 403.",
    )
    allow_insecure_dev_jwt: bool = Field(
        default=False,
        description="Allow the built-in development JWT secret for explicit local-only use.",
    )
    bootstrap_admin_token: SecretStr | None = Field(
        default=None,
        description="Required when open registration is disabled so the first admin can be bootstrapped explicitly.",
    )
    ops_api_token: SecretStr | None = Field(
        default=None,
        description="Required bearer token for ops-only routes such as /metrics and /v1/worker/health.",
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
    artifact_storage_backend: str = Field(
        default="local",
        description='Artifact blob backend: "local" or "s3".',
    )
    artifact_storage_s3_bucket: str | None = Field(
        default=None,
        description="Required bucket name when artifact storage backend is s3.",
    )
    artifact_storage_s3_region: str = Field(
        default="us-east-1",
        description="AWS region for the S3-compatible artifact store.",
    )
    artifact_storage_s3_prefix: str = Field(
        default="",
        description="Optional object-key prefix prepended inside the configured S3 bucket.",
    )
    artifact_storage_s3_endpoint_url: str | None = Field(
        default=None,
        description="Optional S3-compatible endpoint URL override (for non-AWS providers).",
    )
    artifact_storage_s3_access_key_id: str | None = Field(
        default=None,
        description="Optional explicit access key for the S3-compatible artifact store.",
    )
    artifact_storage_s3_secret_access_key: SecretStr | None = Field(
        default=None,
        description="Optional explicit secret access key for the S3-compatible artifact store.",
    )
    artifact_storage_s3_force_path_style: bool = Field(
        default=False,
        description="Force path-style S3 addressing for compatible endpoints that require it.",
    )
    run_workspace_root: Path = Field(
        default=_REPO_ROOT / "data" / "runs",
        description="Filesystem root for durable per-run processed/artifacts workspaces",
    )
    retention_run_payload_days: int = Field(
        default=0,
        ge=0,
        description=(
            "Retention window for analysis-run input/output payload JSON. "
            "0 disables run-payload compaction."
        ),
    )
    retention_model_payload_days: int = Field(
        default=0,
        ge=0,
        description=(
            "Retention window for raw model request/response payload JSON. "
            "0 disables model-payload redaction."
        ),
    )
    retention_artifact_blob_days: int = Field(
        default=0,
        ge=0,
        description=(
            "Retention window for stored artifact blobs. "
            "0 disables artifact-blob cleanup."
        ),
    )
    retention_batch_size: int = Field(
        default=500,
        ge=1,
        le=10_000,
        description="Max run or model rows handled per retention maintenance batch.",
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
        description="Max execution attempts allowed for one analysis run before worker auto-retries stop.",
    )
    run_job_lease_seconds: float = Field(
        default=900.0,
        ge=30.0,
        le=86400.0,
        description="While a job is running, lease_expires_at must stay in the future or the job becomes reclaimable.",
    )
    chat_force_synchronous: bool = Field(
        default=True,
        description=(
            "When true, workspace chat always executes runs synchronously and publicly reports sync-only delivery."
        ),
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
        description=(
            "Default chat model id for all agent phases when a phase-specific "
            "``agent_*_model`` field is empty (``chat.completions``)."
        ),
    )
    agent_intent_model: str = Field(
        default="",
        description="Intent agent model id; empty uses ``agent_completion_model`` (EDGAR_BACKEND_AGENT_INTENT_MODEL).",
    )
    agent_intent_preferences_model: str = Field(
        default="",
        description=(
            "Intent-preferences assistant model; empty uses ``agent_intent_model``, "
            "then ``agent_completion_model`` (EDGAR_BACKEND_AGENT_INTENT_PREFERENCES_MODEL)."
        ),
    )
    agent_planning_model: str = Field(
        default="",
        description="Planning agent model id; empty uses ``agent_completion_model`` (EDGAR_BACKEND_AGENT_PLANNING_MODEL).",
    )
    agent_critic_model: str = Field(
        default="",
        description="Critic agent model id; empty uses ``agent_completion_model`` (EDGAR_BACKEND_AGENT_CRITIC_MODEL).",
    )
    agent_report_model: str = Field(
        default="",
        description="Report agent model id; empty uses ``agent_completion_model`` (EDGAR_BACKEND_AGENT_REPORT_MODEL).",
    )
    agent_intent_prompt_version: str = Field(
        default="1.1.0",
        description="Prompt file version directory under ``backend/agents/prompts/intent/``",
    )
    orchestration_llm_intent_assistance: bool = Field(
        default=False,
        description=(
            "When true and an LLM provider is available, merge validated preference JSON over "
            "rule-based :class:`GoalPreferences` before deterministic template selection (no tool plans)."
        ),
    )
    agent_intent_preferences_prompt_version: str = Field(
        default="1.1.0",
        description="Prompt file under ``backend/agents/prompts/intent_preferences_assistant/``",
    )
    agent_planning_prompt_version: str = Field(
        default="1.1.0",
        description="Prompt file version directory under ``backend/agents/prompts/planning/``",
    )
    agent_critic_prompt_version: str = Field(
        default="1.1.0",
        description="Prompt file version under ``backend/agents/prompts/critic/``",
    )
    agent_report_prompt_version: str = Field(
        default="1.1.0",
        description="Prompt file version under ``backend/agents/prompts/report/``",
    )

    # LLM context budgets — see :class:`backend.agents.context_budget.ContextBudget` / ``from_settings``
    agent_context_max_user_request_chars: int = Field(default=8_000, ge=256)
    agent_context_max_goal_excerpt_chars: int = Field(default=600, ge=64)
    agent_context_max_intent_rules_matched: int = Field(default=16, ge=1, le=256)
    agent_context_max_template_rules_matched: int = Field(default=12, ge=1, le=128)
    agent_context_max_plan_alignment_findings: int = Field(default=12, ge=0, le=256)
    agent_context_max_resolved_companies: int = Field(default=24, ge=0, le=512)
    agent_context_max_tool_result_rows: int = Field(default=32, ge=0, le=512)
    agent_context_max_step_rows: int = Field(default=48, ge=0, le=512)
    agent_context_max_warn_err_samples: int = Field(default=5, ge=0, le=128)
    agent_context_max_warn_err_message_chars: int = Field(default=240, ge=32)
    agent_context_max_run_message_chars: int = Field(default=1_000, ge=64)
    agent_context_max_final_summary_chars: int = Field(default=2_000, ge=128)
    agent_context_max_tool_result_artifact_keys: int = Field(default=12, ge=1, le=64)
    agent_context_max_slim_row_keys: int = Field(default=14, ge=4, le=64)
    agent_context_max_coverage_roles: int = Field(
        default=0,
        ge=0,
        description="Max entries in artifact_coverage role lists; 0 = unlimited.",
    )
    agent_context_max_critic_issue_items: int = Field(default=24, ge=1, le=256)
    agent_context_max_critic_text_field_chars: int = Field(default=8_000, ge=256)
    agent_context_max_read_bytes: int = Field(default=2_000_000, ge=8_192)
    agent_context_max_anomaly_rows: int = Field(default=15, ge=0, le=512)
    agent_context_max_unified_findings_rows: int = Field(default=12, ge=0, le=512)
    agent_context_max_deterioration_rows: int = Field(default=12, ge=0, le=512)
    agent_context_max_findings_summary_rows: int = Field(default=24, ge=0, le=512)
    agent_context_max_caveat_sample_rows: int = Field(default=200, ge=0, le=10_000)
    agent_context_max_caveat_token_types: int = Field(default=40, ge=0, le=512)
    agent_context_max_caveat_detail_rows: int = Field(default=8, ge=0, le=256)
    agent_context_max_generic_csv_rows: int = Field(default=20, ge=0, le=512)
    agent_context_max_panel_feature_rows: int = Field(default=4, ge=0, le=64)
    agent_context_max_panel_trim_chars: int = Field(default=80, ge=16, le=512)
    agent_context_max_cell_chars: int = Field(default=120, ge=16, le=2_000)
    agent_context_max_anomaly_category_buckets: int = Field(default=12, ge=0, le=128)
    agent_context_max_markdown_preview_lines: int = Field(default=100, ge=0, le=2_000)
    agent_context_max_markdown_chars: int = Field(default=10_000, ge=256)
    agent_context_max_markdown_headings: int = Field(default=20, ge=0, le=256)
    agent_context_max_trustworthiness_chars: int = Field(default=4_000, ge=256)
    agent_context_max_generic_column_names: int = Field(default=30, ge=0, le=256)
    agent_context_max_generic_row_columns: int = Field(default=12, ge=0, le=128)
    agent_context_max_artifact_summary_roles: int = Field(
        default=0,
        ge=0,
        description="Max artifact roles in critic/report summary bundle; 0 = unlimited.",
    )
    agent_context_max_artifact_index_entries: int = Field(
        default=0,
        ge=0,
        description="Max artifact_index rows; 0 = unlimited.",
    )
    agent_llm_pricing_json: str = Field(
        default="{}",
        description=(
            "Optional JSON map of OpenAI-style model id → "
            '{"prompt_usd_per_1m": float, "completion_usd_per_1m": float} for run cost estimates.'
        ),
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

    @field_validator(
        "agent_completion_model",
        "agent_intent_model",
        "agent_intent_preferences_model",
        "agent_planning_model",
        "agent_critic_model",
        "agent_report_model",
        mode="before",
    )
    @classmethod
    def _strip_agent_model_fields(cls, v: object) -> object:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "artifact_storage_backend",
        "artifact_storage_s3_bucket",
        "artifact_storage_s3_region",
        "artifact_storage_s3_prefix",
        "artifact_storage_s3_endpoint_url",
        "artifact_storage_s3_access_key_id",
        mode="before",
    )
    @classmethod
    def _normalize_artifact_storage_fields(cls, v: object, info) -> object:
        if isinstance(v, str):
            normalized = v.strip()
            if info.field_name == "artifact_storage_backend":
                return normalized.lower()
            if info.field_name == "artifact_storage_s3_prefix":
                return normalized.strip("/")
            if normalized == "":
                return None
            return normalized
        return v

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
        jwt_secret_value = self.jwt_secret.get_secret_value()
        bootstrap_token = self.bootstrap_admin_token.get_secret_value() if self.bootstrap_admin_token else ""
        ops_token = self.ops_api_token.get_secret_value() if self.ops_api_token else ""
        s3_secret = (
            self.artifact_storage_s3_secret_access_key.get_secret_value()
            if self.artifact_storage_s3_secret_access_key
            else ""
        )
        if not self.debug and len(jwt_secret_value) < 32:
            raise ValueError(
                "EDGAR_BACKEND_JWT_SECRET must be at least 32 characters when EDGAR_BACKEND_DEBUG is false.",
            )
        if jwt_secret_value == BUILTIN_DEV_JWT_SECRET and not self.allow_insecure_dev_jwt:
            raise ValueError(
                "EDGAR_BACKEND_JWT_SECRET is still using the built-in development secret. "
                "Set a real secret or explicitly opt in with EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true.",
            )
        if not self.allow_open_registration and not bootstrap_token.strip():
            raise ValueError(
                "EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN must be set when EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION is false.",
            )
        if not ops_token.strip():
            raise ValueError(
                "EDGAR_BACKEND_OPS_API_TOKEN must be set to a non-empty value.",
            )
        if self.artifact_storage_backend not in {"local", "s3"}:
            raise ValueError(
                "EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND must be either 'local' or 's3'.",
            )
        if self.artifact_storage_backend == "s3":
            if not (self.artifact_storage_s3_bucket or "").strip():
                raise ValueError(
                    "EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET must be set when "
                    "EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND is 's3'.",
                )
            if self.artifact_storage_s3_access_key_id and not s3_secret.strip():
                raise ValueError(
                    "EDGAR_BACKEND_ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY must be set when "
                    "EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ACCESS_KEY_ID is provided.",
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
