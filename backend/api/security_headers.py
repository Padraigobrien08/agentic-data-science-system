"""Response security headers for the HTTP API boundary.

Applied to every response. Values use ``setdefault`` so a route that already sets a
specific header (e.g. artifact delivery) keeps its own value. HSTS is only emitted on
HTTPS requests, and the Content-Security-Policy skips the interactive docs paths so
Swagger UI / ReDoc keep loading their bundled assets.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# FastAPI's default interactive docs + schema. A strict CSP would block their assets.
_DEFAULT_CSP_EXEMPT_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/openapi.json")


def _is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto")
    if forwarded:
        # May be a comma-separated list when passing through multiple proxies.
        return forwarded.split(",", 1)[0].strip().lower() == "https"
    return request.url.scheme == "https"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        hsts_max_age_seconds: int = 0,
        content_security_policy: str | None = None,
        csp_exempt_prefixes: Sequence[str] = _DEFAULT_CSP_EXEMPT_PREFIXES,
    ) -> None:
        super().__init__(app)
        self._hsts_max_age = hsts_max_age_seconds
        self._csp = (content_security_policy or "").strip()
        self._csp_exempt = tuple(csp_exempt_prefixes)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        if self._csp and not request.url.path.startswith(self._csp_exempt):
            headers.setdefault("Content-Security-Policy", self._csp)

        if self._hsts_max_age > 0 and _is_https(request):
            headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={self._hsts_max_age}; includeSubDomains",
            )
        return response
