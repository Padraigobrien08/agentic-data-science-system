"""
Per-caller rate limiting for MCP tool invocations.

The MCP server is a client of ``/v1``, so it inherits the API's auth and owner scoping — but
not its rate limiting, which is keyed by IP and applied only to the unauthenticated auth
endpoints. A hosted MCP endpoint therefore had no ceiling on tool calls at all.

**Keyed by caller, not by IP.** Over stdio there is no IP; over streamable-HTTP every caller
arrives at the same proxy. The bearer token *is* the caller identity in both transports, which
is exactly what needs bounding — one token should not be able to drive the API as fast as it
can open connections.

The key is a truncated SHA-256 of the token, never the token itself: this dictionary lives for
the process lifetime, and a heap dump or a debugger session should not hand over credentials.

State is per-process, like :mod:`backend.api.rate_limit`. Under stdio that is exactly right —
one subprocess per user. Under HTTP a second replica enforces its own budget independently;
close that with a shared store or an ingress limiter if it ever matters.
"""

from __future__ import annotations

import hashlib

from backend.api.rate_limit import SlidingWindowRateLimiter
from backend.config.settings import Settings, get_settings

#: Used when no token can be resolved — stdio with an env token still resolves one, so this
#: covers the unauthenticated handshake path. Bucketing those together is deliberate: an
#: anonymous flood should contend with itself rather than get a fresh budget per connection.
ANONYMOUS_KEY = "anonymous"


class McpRateLimited(RuntimeError):
    """The caller exceeded their tool-invocation budget."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded for MCP tool calls. Retry in {retry_after_seconds}s."
        )


def caller_key(token: str | None) -> str:
    """A stable, non-reversible identity for one caller."""
    raw = (token or "").strip()
    if not raw:
        return ANONYMOUS_KEY
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class McpRateLimiter:
    """Sliding-window budget over tool invocations, keyed by caller."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self._enabled = s.mcp_rate_limit_enabled
        self._limiter = (
            SlidingWindowRateLimiter(
                max_attempts=s.mcp_rate_limit_max_calls,
                window_seconds=float(s.mcp_rate_limit_window_seconds),
            )
            if self._enabled
            else None
        )

    def check(self, token: str | None) -> None:
        """Raise :class:`McpRateLimited` when this caller is over budget."""
        if self._limiter is None:
            return
        decision = self._limiter.hit(caller_key(token))
        if not decision.allowed:
            raise McpRateLimited(decision.retry_after_seconds)


#: Process-wide limiter, built lazily so importing the module does not read settings — the
#: MCP server is importable in contexts (tests, tooling) that never serve a request.
_LIMITER: McpRateLimiter | None = None


def get_limiter() -> McpRateLimiter:
    global _LIMITER
    if _LIMITER is None:
        _LIMITER = McpRateLimiter()
    return _LIMITER


def reset_limiter() -> None:
    """Drop the process limiter so the next call rebuilds it from current settings (tests)."""
    global _LIMITER
    _LIMITER = None
