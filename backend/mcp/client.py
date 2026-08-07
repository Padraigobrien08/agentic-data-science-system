"""
Thin HTTP client for the platform's ``/v1`` API.

The orchestration MCP server is a **client of the API**, not a second implementation of it.
That is deliberate: going through HTTP means every call inherits the API's authentication,
owner scoping, validation, and 404-for-unauthorized semantics, and the same MCP server works
against a local stack or a deployed instance without change.

Configuration comes from the environment so the server can be launched by an MCP host that
knows nothing about this codebase:

* ``EDGAR_MCP_API_URL``  — base URL of the API (default ``http://127.0.0.1:8000``)
* ``EDGAR_MCP_TOKEN``    — bearer token obtained from ``POST /v1/auth/login``
* ``EDGAR_MCP_TIMEOUT``  — per-request timeout in seconds (default 60)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_S = 60.0


class PlatformApiError(RuntimeError):
    """A non-2xx response from the platform API."""

    def __init__(self, status_code: int, detail: str, *, path: str = "") -> None:
        super().__init__(f"{status_code} from {path or 'API'}: {detail}")
        self.status_code = status_code
        self.detail = detail
        self.path = path


class PlatformNotConfigured(RuntimeError):
    """No API token is available, so no authenticated call can be made."""


@dataclass
class PlatformClient:
    """Authenticated HTTP client for ``/v1``."""

    base_url: str = DEFAULT_BASE_URL
    token: str = ""
    timeout_s: float = DEFAULT_TIMEOUT_S

    @classmethod
    def from_env(cls) -> "PlatformClient":
        return cls(
            base_url=(os.getenv("EDGAR_MCP_API_URL") or DEFAULT_BASE_URL).rstrip("/"),
            token=os.getenv("EDGAR_MCP_TOKEN") or "",
            timeout_s=float(os.getenv("EDGAR_MCP_TIMEOUT") or DEFAULT_TIMEOUT_S),
        )

    # -- transport -----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise PlatformNotConfigured(
                "No API token. Set EDGAR_MCP_TOKEN to a token from POST /v1/auth/login."
            )
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/v1/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(
            method, self._url(path), headers=self._headers(), timeout=self.timeout_s, **kwargs
        )
        if response.status_code >= 400:
            raise PlatformApiError(response.status_code, _detail(response), path=path)
        if not response.content:
            return None
        return response.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        return self._request("GET", path, params=clean)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=payload or {})

    # -- investigations ------------------------------------------------------

    def create_investigation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("investigations", payload)

    def list_investigations(
        self,
        *,
        project_id: str | None = None,
        analysis_run_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self.get(
            "investigations",
            {"project_id": project_id, "analysis_run_id": analysis_run_id,
             "limit": limit, "offset": offset},
        )

    def get_investigation(self, investigation_id: str) -> dict[str, Any]:
        return self.get(f"investigations/{investigation_id}")

    # -- runs and artifacts --------------------------------------------------

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self.get(f"runs/{run_id}")

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        return self.get(f"runs/{run_id}/status")

    def list_run_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        return self.get(f"runs/{run_id}/artifacts")

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        return self.get(f"artifacts/{artifact_id}")

    def get_artifact_preview(self, artifact_id: str) -> dict[str, Any]:
        return self.get(f"artifacts/{artifact_id}/preview")

    # -- projects ------------------------------------------------------------

    def list_projects(self) -> list[dict[str, Any]]:
        return self.get("projects")


def _detail(response: requests.Response) -> str:
    """Best-effort error text, without assuming the body is JSON."""
    try:
        body = response.json()
    except ValueError:
        return (response.text or "").strip()[:500]
    if isinstance(body, dict):
        detail = body.get("detail", body)
        return detail if isinstance(detail, str) else str(detail)[:500]
    return str(body)[:500]
