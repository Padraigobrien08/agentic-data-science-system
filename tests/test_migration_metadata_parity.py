"""
Guard: a database built from migrations must match one built from ``Base.metadata``.

The test suite builds its schema with ``Base.metadata.create_all``, so nothing else
notices when a migration under-delivers what the ORM declares — that is exactly how the
51 differences fixed by ``017_schema_metadata_alignment`` accumulated unseen. This runs
the real chain on SQLite and asserts Alembic's own autogenerate comparison finds nothing
left to do, which fails the moment a new migration and its model disagree.

The same assertion runs against Postgres in ``test_investigation_persistence_postgres.py``
(skipped without a Postgres URL).
"""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.pool import NullPool

import backend.models  # noqa: F401  (registers every table on Base.metadata)
from backend.db.base import Base

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    """Drive the real CLI so ``alembic/env.py`` is exercised, not bypassed."""
    env = dict(os.environ)
    env.update(
        EDGAR_BACKEND_DATABASE_URL=url,
        EDGAR_BACKEND_JWT_SECRET="pytest-jwt-secret-minimum-32-characters-long-x",
        EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION="true",
        EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN="t",
        EDGAR_BACKEND_OPS_API_TOKEN="t",
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, check=True,
    )


def metadata_differences(url: str) -> list[str]:
    """Alembic's autogenerate diff of a live database against ``Base.metadata``."""
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(
                conn,
                opts={"compare_type": True, "compare_server_default": True},
            )
            with warnings.catch_warnings():
                # The investigations/conclusions forward pointers are a known FK cycle;
                # it makes table sorting ambiguous but does not affect the comparison.
                warnings.simplefilter("ignore", SAWarning)
                raw = compare_metadata(ctx, Base.metadata)
    finally:
        engine.dispose()

    flat: list = []
    for entry in raw:
        flat.extend(entry) if isinstance(entry, list) else flat.append(entry)
    # ``alembic_version`` is alembic's own bookkeeping and is absent from the ORM metadata.
    return [repr(d) for d in flat if "alembic_version" not in repr(d)]


@pytest.fixture
def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migrated.db'}"


def test_sqlite_upgrade_head_matches_metadata(sqlite_url: str) -> None:
    run_alembic(sqlite_url, "upgrade", "head")
    diffs = metadata_differences(sqlite_url)
    assert diffs == [], "migrations and Base.metadata disagree:\n" + "\n".join(diffs)


def test_sqlite_full_downgrade_then_upgrade_still_matches(sqlite_url: str) -> None:
    """Every revision must reverse cleanly and rebuild the same schema."""
    run_alembic(sqlite_url, "upgrade", "head")
    run_alembic(sqlite_url, "downgrade", "base")

    engine = create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            from sqlalchemy import inspect

            remaining = set(inspect(conn).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()
    assert remaining == set(), f"downgrade to base left tables behind: {sorted(remaining)}"

    run_alembic(sqlite_url, "upgrade", "head")
    diffs = metadata_differences(sqlite_url)
    assert diffs == [], "schema differs after a down/up round trip:\n" + "\n".join(diffs)
