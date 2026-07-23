"""Alembic environment — loads settings and model metadata from ``backend`` package."""

from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.config.settings import get_settings
from backend.db.base import Base

# Register all models on Base.metadata
import backend.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def get_database_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_wide_version_table(connection) -> None:
    """
    Pre-create ``alembic_version`` with a wide ``version_num`` column.

    Alembic (>= 1.14) hard-codes ``alembic_version.version_num`` as ``VARCHAR(32)``,
    but this project's revision identifiers exceed 32 characters (e.g.
    ``013_live_hybrid_evaluation_case_run_links``). On a *fresh* database that
    makes ``alembic upgrade head`` fail when it stamps the first long revision.
    Creating the table up front with a wide column (idempotent, ``IF NOT EXISTS``)
    fixes fresh migrations without touching any revision id or applied migration;
    existing databases already hold long heads, so their table is left untouched.
    """
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS alembic_version ("
        "version_num VARCHAR(255) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live connection)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Ensure a wide alembic_version table in its own committed transaction, fully
    # isolated from the migration connection so it cannot interfere with alembic's
    # own transaction handling.
    with connectable.connect() as pre_connection:
        with pre_connection.begin():
            _ensure_wide_version_table(pre_connection)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
