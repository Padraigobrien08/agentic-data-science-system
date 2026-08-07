"""
Per-caller bearer token resolution for the MCP server.

The two transports have fundamentally different trust models, and conflating them is the
main way a hosted MCP server goes wrong:

* **stdio** — the server is launched *by* one user's MCP host as a subprocess. There is one
  caller, and their token comes from the environment (``EDGAR_MCP_TOKEN``).
* **streamable-http** — the server is *hosted* and many callers connect to it. Each request
  must carry its own ``Authorization: Bearer`` header, and the server acts strictly as that
  caller.

The critical rule this module enforces: **in HTTP mode the environment token is never used as
a fallback.** If it were, an unauthenticated request to a hosted server would silently execute
with the operator's identity — every caller would inherit the server's access. A request
without a usable header is refused instead.
"""

from __future__ import annotations

import os
from enum import Enum


class TransportMode(str, Enum):
    stdio = "stdio"
    http = "http"


class TokenUnavailable(RuntimeError):
    """No bearer token could be resolved for this call."""


#: Set once at startup by the entry point. Defaults to stdio, the safer assumption: it
#: requires an explicit environment token rather than trusting an inbound header.
_MODE: TransportMode = TransportMode.stdio


def set_transport_mode(mode: TransportMode) -> None:
    global _MODE
    _MODE = mode


def get_transport_mode() -> TransportMode:
    return _MODE


def _bearer_from_headers(headers) -> str:
    """Extract a bearer token from a case-insensitive header mapping."""
    raw = ""
    try:
        raw = headers.get("authorization") or headers.get("Authorization") or ""
    except Exception:  # noqa: BLE001 - defensive: header mappings vary by transport
        return ""
    raw = str(raw).strip()
    if not raw:
        return ""
    scheme, _, value = raw.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def token_from_request() -> str:
    """The caller's bearer token from the in-flight HTTP request, or ``""``."""
    # Imported here so the module stays importable without a live server.
    from backend.mcp.server import mcp

    try:
        context = mcp.get_context()
    except Exception:  # noqa: BLE001 - no active request
        return ""
    request_context = getattr(context, "request_context", None)
    request = getattr(request_context, "request", None)
    headers = getattr(request, "headers", None)
    if headers is None:
        return ""
    return _bearer_from_headers(headers)


def resolve_token() -> str:
    """
    The bearer token this call should act with.

    Raises:
        TokenUnavailable: no token is available for the current transport. In HTTP mode this
            means the request carried no usable ``Authorization: Bearer`` header — it is never
            substituted with the server's own environment token.
    """
    if _MODE is TransportMode.http:
        token = token_from_request()
        if not token:
            raise TokenUnavailable(
                "This request carried no 'Authorization: Bearer <token>' header. A hosted MCP "
                "server acts only as the calling user, so the request cannot proceed."
            )
        return token

    token = os.getenv("EDGAR_MCP_TOKEN") or ""
    if not token:
        raise TokenUnavailable(
            "No API token. Set EDGAR_MCP_TOKEN to a token from POST /v1/auth/login."
        )
    return token
