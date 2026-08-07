"""Secure-default settings regressions for startup validation and onboarding posture."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from backend.config.settings import BUILTIN_DEV_JWT_SECRET, Settings

SECURE_JWT_SECRET = "secure-jwt-secret-minimum-32-characters-long"
BOOTSTRAP_TOKEN = "pytest-bootstrap-token"


def _clear_security_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT",
        "EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION",
        "EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN",
        "EDGAR_BACKEND_JWT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)


def test_built_in_secret_rejected_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)

    with pytest.raises(ValueError, match="EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true"):
        Settings(
            _env_file=None,
            jwt_secret=SecretStr(BUILTIN_DEV_JWT_SECRET),
            bootstrap_admin_token=SecretStr(BOOTSTRAP_TOKEN),
        )


def test_built_in_secret_allowed_only_with_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_security_env(monkeypatch)

    settings = Settings(
        _env_file=None,
        jwt_secret=SecretStr(BUILTIN_DEV_JWT_SECRET),
        allow_insecure_dev_jwt=True,
        bootstrap_admin_token=SecretStr(BOOTSTRAP_TOKEN),
    )

    assert settings.allow_insecure_dev_jwt is True


def test_open_registration_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)

    settings = Settings(
        _env_file=None,
        jwt_secret=SecretStr(SECURE_JWT_SECRET),
        bootstrap_admin_token=SecretStr(BOOTSTRAP_TOKEN),
    )

    assert settings.allow_open_registration is False


def test_closed_registration_requires_bootstrap_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)

    with pytest.raises(ValueError, match="EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN"):
        Settings(
            _env_file=None,
            jwt_secret=SecretStr(SECURE_JWT_SECRET),
        )


# --- CORS origin parsing from the environment -------------------------------
#
# Regression: pydantic-settings JSON-decodes complex fields *before* field validators run,
# so the documented comma-separated form never worked from the environment and an empty
# value -- the natural way to write "no CORS", and the documented default -- raised a
# SettingsError at import, taking the app down at startup. The field is annotated
# ``NoDecode`` so the raw string reaches the validator.


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("   ", []),
        ("https://a.example", ["https://a.example"]),
        ("https://a.example,https://b.example", ["https://a.example", "https://b.example"]),
        ("https://a.example, https://b.example ", ["https://a.example", "https://b.example"]),
        ('["https://c.example"]', ["https://c.example"]),
        ('["https://c.example", "https://d.example"]', ["https://c.example", "https://d.example"]),
    ],
)
def test_cors_origins_parse_from_env(monkeypatch, raw: str, expected: list[str]) -> None:
    monkeypatch.setenv("EDGAR_BACKEND_CORS_ALLOW_ORIGINS", raw)
    assert Settings().cors_allow_origins == expected


def test_cors_origins_unset_defaults_to_closed(monkeypatch) -> None:
    monkeypatch.delenv("EDGAR_BACKEND_CORS_ALLOW_ORIGINS", raising=False)
    assert Settings().cors_allow_origins == []


def test_malformed_cors_json_is_rejected_clearly(monkeypatch) -> None:
    monkeypatch.setenv("EDGAR_BACKEND_CORS_ALLOW_ORIGINS", "[not valid json")
    with pytest.raises(ValidationError):
        Settings()
