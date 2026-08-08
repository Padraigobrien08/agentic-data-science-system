"""
A complex-typed setting must tolerate an empty environment value.

pydantic-settings JSON-decodes `dict`- and `list`-typed fields *before* validators run, so an
empty string raises `SettingsError` at construction. That is not a field-level problem: every
process that loads settings dies — api, worker, and the migrate job — with an error that names
the field but not the cause.

It is also easy to trigger by accident. `docker-compose.yml` forwards optional settings as
`${VAR:-}`, which sends an empty string when the operator has not set them, and an empty value
is the natural way to write "none configured" in a `.env`. Adding
`EDGAR_BACKEND_LLM_MODEL_PRICES` to the compose anchor did exactly this and took the whole stack
down in CI while passing locally, because the local `.env` happened to have a real value.

The fix per field is `NoDecode` plus a `mode="before"` validator that treats empty as the
default — the pattern `cors_allow_origins` already established. This test enforces it for every
complex-typed setting, so the next one added cannot reintroduce the failure.
"""

from __future__ import annotations

import pytest

from backend.config.settings import Settings

#: Env values an operator may plausibly leave behind for "not configured".
_EMPTY_VALUES = ("", "   ")


def _complex_fields() -> list[str]:
    """Settings whose annotation makes pydantic-settings JSON-decode the raw env string."""
    return [
        name
        for name, field in Settings.model_fields.items()
        if any(t in str(field.annotation) for t in ("dict", "list"))
    ]


def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The unrelated guards that would otherwise mask the parse behaviour under test."""
    monkeypatch.setenv("EDGAR_BACKEND_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN", "y" * 40)
    monkeypatch.setenv("EDGAR_BACKEND_OPS_API_TOKEN", "z" * 40)


def test_there_is_at_least_one_complex_setting_to_check() -> None:
    """Guards the parametrisation below from silently covering nothing."""
    assert _complex_fields()


@pytest.mark.parametrize("empty", _EMPTY_VALUES, ids=["empty-string", "whitespace"])
@pytest.mark.parametrize("field_name", _complex_fields())
def test_an_empty_value_is_treated_as_not_configured(
    field_name: str, empty: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv(f"EDGAR_BACKEND_{field_name.upper()}", empty)

    settings = Settings(_env_file=None)

    value = getattr(settings, field_name)
    assert value in ({}, []), (
        f"{field_name} did not fall back to its empty default. If this raised SettingsError, "
        "annotate the field `NoDecode` and add a mode='before' validator that returns the "
        "default for an empty string — see llm_model_prices and cors_allow_origins."
    )


def test_model_prices_still_parse_real_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv(
        "EDGAR_BACKEND_LLM_MODEL_PRICES",
        '{"gpt-5.4-mini": {"input_per_1m": 0.75, "output_per_1m": 4.5}}',
    )

    prices = Settings(_env_file=None).llm_model_prices

    assert prices["gpt-5.4-mini"]["input_per_1m"] == 0.75


def test_malformed_model_prices_are_rejected_with_a_named_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tolerating empty must not mean tolerating garbage — a typo should still be loud."""
    _required_env(monkeypatch)
    monkeypatch.setenv("EDGAR_BACKEND_LLM_MODEL_PRICES", "{not json")

    with pytest.raises(Exception, match="not valid JSON"):
        Settings(_env_file=None)
