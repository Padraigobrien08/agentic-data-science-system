"""
Rate limiting on MCP tool invocations.

The MCP server inherits the API's auth and owner scoping because it is a client of ``/v1``,
but it did not inherit any ceiling on call volume: the API's limiter is keyed by IP and applied
only to unauthenticated auth endpoints. A hosted MCP endpoint could be driven as fast as a
caller could open connections.

The structural property matters more than the numbers here — the check lives in ``_guarded``,
which every tool passes through, so a tool added next year is bounded without anyone
remembering to bound it.
"""

from __future__ import annotations

import pytest

from backend.config.settings import Settings
from backend.mcp.rate_limit import (
    ANONYMOUS_KEY,
    McpRateLimited,
    McpRateLimiter,
    caller_key,
    reset_limiter,
)


@pytest.fixture(autouse=True)
def _clean_limiter():
    reset_limiter()
    yield
    reset_limiter()


def _settings(**kw) -> Settings:
    base = dict(mcp_rate_limit_enabled=True, mcp_rate_limit_max_calls=3, mcp_rate_limit_window_seconds=60)
    base.update(kw)
    return Settings(**base)


# --- keying -----------------------------------------------------------------


def test_the_key_is_not_the_token() -> None:
    """
    This dictionary lives for the process lifetime. A heap dump or a debugger session must not
    hand over credentials.
    """
    token = "secret-bearer-token-value"
    key = caller_key(token)
    assert token not in key
    assert key != token
    assert len(key) == 32


def test_the_same_token_keys_the_same_bucket() -> None:
    assert caller_key("abc") == caller_key("abc")
    assert caller_key(" abc ") == caller_key("abc")


def test_different_tokens_key_different_buckets() -> None:
    assert caller_key("abc") != caller_key("abd")


def test_a_missing_token_buckets_as_anonymous() -> None:
    """An anonymous flood should contend with itself, not get a fresh budget per connection."""
    assert caller_key(None) == ANONYMOUS_KEY
    assert caller_key("") == ANONYMOUS_KEY
    assert caller_key("   ") == ANONYMOUS_KEY


# --- the budget -------------------------------------------------------------


def test_calls_within_the_budget_are_allowed() -> None:
    limiter = McpRateLimiter(_settings())
    for _ in range(3):
        limiter.check("token-a")


def test_the_budget_binds_and_reports_a_retry_delay() -> None:
    limiter = McpRateLimiter(_settings())
    for _ in range(3):
        limiter.check("token-a")

    with pytest.raises(McpRateLimited) as exc:
        limiter.check("token-a")
    assert exc.value.retry_after_seconds >= 1


def test_one_caller_cannot_exhaust_anothers_budget() -> None:
    """The point of keying by caller: a noisy agent must not deny service to a quiet one."""
    limiter = McpRateLimiter(_settings())
    for _ in range(3):
        limiter.check("noisy")
    with pytest.raises(McpRateLimited):
        limiter.check("noisy")

    limiter.check("quiet")  # unaffected


def test_disabling_it_removes_the_ceiling() -> None:
    limiter = McpRateLimiter(_settings(mcp_rate_limit_enabled=False))
    for _ in range(50):
        limiter.check("token-a")


# --- the structural property ------------------------------------------------


def test_every_tool_goes_through_the_guarded_choke_point(monkeypatch) -> None:
    """
    The check sits in ``_guarded`` rather than on each tool, so a tool added later is bounded
    by construction. This asserts that the wiring is actually in that path — if someone moves
    the check onto individual tools, this fails and says why.
    """
    from backend.mcp import server as mcp_server

    calls: list[str | None] = []

    class _Recording:
        def check(self, token):
            calls.append(token)

    monkeypatch.setattr(mcp_server, "get_limiter", lambda: _Recording())
    monkeypatch.setattr(mcp_server, "_rate_limit_key", lambda: "tok")

    out = mcp_server._guarded("demo", lambda: {"status": "success"})

    assert out == {"status": "success"}
    assert calls == ["tok"], "_guarded must consult the limiter exactly once per invocation"


def test_a_limited_call_returns_an_envelope_not_an_exception(monkeypatch) -> None:
    """
    Errors never cross the MCP boundary as exceptions — an agent gets a typed envelope it can
    reason about. A 429 is no exception to that.
    """
    from backend.mcp import server as mcp_server

    class _Exhausted:
        def check(self, token):
            raise McpRateLimited(retry_after_seconds=7)

    monkeypatch.setattr(mcp_server, "get_limiter", lambda: _Exhausted())
    monkeypatch.setattr(mcp_server, "_rate_limit_key", lambda: "tok")

    ran = []
    out = mcp_server._guarded("demo", lambda: ran.append(1))

    assert ran == [], "the tool body must not run once the caller is over budget"
    assert out["status"] == "error"
    assert out["errors"][0]["code"] == mcp_server.CODE_RATE_LIMITED
    assert out["errors"][0]["http_status"] == 429
    assert "7" in out["errors"][0]["detail"]


def test_an_unresolvable_caller_is_limited_rather_than_refused(monkeypatch) -> None:
    """
    A token that cannot be resolved buckets as anonymous instead of erroring. Refusing here
    would make the limiter a second authentication path, which is not its job — authentication
    is the API's, inherited through /v1.
    """
    from backend.mcp import server as mcp_server

    def _boom():
        raise RuntimeError("no token in this context")

    monkeypatch.setattr(mcp_server, "resolve_token", _boom)
    assert mcp_server._rate_limit_key() is None
