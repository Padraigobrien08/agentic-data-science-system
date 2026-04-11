"""Database URL / SQLite guardrails in settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytest.importorskip("pydantic_settings")

from backend.config.settings import Settings


def test_allow_sqlite_false_rejects_sqlite_url() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(allow_sqlite=False, database_url="sqlite:////tmp/disallowed.db")
    assert "ALLOW_SQLITE" in str(exc.value)


def test_allow_sqlite_true_accepts_sqlite_url() -> None:
    s = Settings(allow_sqlite=True, database_url="sqlite:////tmp/allowed.db")
    assert "sqlite" in s.database_url
