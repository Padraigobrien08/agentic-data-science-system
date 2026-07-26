"""In-process sliding-window rate limiting for unauthenticated auth endpoints.

Keyed by client IP + route so a burst of logins does not exhaust the registration
budget. State lives in this process only: it protects a single API process against
credential stuffing / registration spam without new infrastructure. Multi-replica
deployments should front this with a shared store (e.g. Redis) or an ingress limiter;
until then each replica enforces the limit independently.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil

from fastapi import HTTPException, Request, status

# Safety cap on distinct tracked keys so a flood of unique IPs cannot grow memory
# unbounded; empty windows are swept before this bound is enforced.
_MAX_TRACKED_KEYS = 50_000


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._max = max_attempts
        self._window = float(window_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def hit(self, key: str) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - self._window
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max:
                retry_after = max(1, ceil(bucket[0] + self._window - now))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            bucket.append(now)
            if len(self._buckets) > _MAX_TRACKED_KEYS:
                self._sweep_empty(cutoff)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)

    def _sweep_empty(self, cutoff: float) -> None:
        """Drop keys whose entire window has expired (caller holds the lock)."""
        stale = [k for k, dq in self._buckets.items() if not dq or dq[-1] <= cutoff]
        for k in stale:
            del self._buckets[k]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    client = request.client
    return client.host if client else "unknown"


async def enforce_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429 when the caller exceeds the auth attempt budget.

    Reads the limiter from ``app.state.auth_rate_limiter`` (set in ``create_app``);
    absent/None means limiting is disabled and the request passes through.
    """
    limiter: SlidingWindowRateLimiter | None = getattr(request.app.state, "auth_rate_limiter", None)
    if limiter is None:
        return
    key = f"{_client_ip(request)}:{request.url.path}"
    decision = limiter.hit(key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please retry later.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
