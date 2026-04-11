"""Application settings — env-driven, safe defaults for local development."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


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

    # Default: SQLite file under repo data/ (created by migration/runtime, not necessarily by config.py)
    database_url: str = Field(
        default=f"sqlite:///{_REPO_ROOT / 'data' / 'backend.db'}",
        description="SQLAlchemy URL (e.g. postgresql+psycopg2://user:pass@host/dbname)",
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
        default="gpt-4o-mini",
        description="Chat model for intent and planning agents",
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
