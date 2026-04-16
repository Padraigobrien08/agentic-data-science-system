"""Register/login helpers for API tests (Bearer JWT)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

TEST_PASSWORD = "test-pass-word-10chars"


def _login_and_create_project(client: TestClient, *, email: str) -> tuple[str, dict[str, str]]:
    r = client.post(
        "/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.post("/v1/projects", json={"name": "Test project"}, headers=headers)
    assert r2.status_code == 201, r2.text
    return str(r2.json()["id"]), headers


def register_project_and_headers(client: TestClient) -> tuple[str, dict[str, str]]:
    """
    Create a user via ``POST /v1/auth/register``, log in, create a project.

    Returns ``(project_id_str, auth_headers)``.
    """
    email = f"test-{uuid.uuid4().hex[:14]}@example.com"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert r.status_code == 201, r.text
    return _login_and_create_project(client, email=email)


def bootstrap_admin_and_headers(
    client: TestClient,
    *,
    bootstrap_token: str = "pytest-bootstrap-token",
) -> tuple[str, dict[str, str]]:
    """Create the first admin via bootstrap, log in, and create a project."""

    email = f"admin-{uuid.uuid4().hex[:14]}@example.com"
    r = client.post(
        "/v1/auth/bootstrap",
        json={"email": email, "password": TEST_PASSWORD, "display_name": "Bootstrap Admin"},
        headers={"X-EDGAR-Bootstrap-Token": bootstrap_token},
    )
    assert r.status_code == 201, r.text
    return _login_and_create_project(client, email=email)
