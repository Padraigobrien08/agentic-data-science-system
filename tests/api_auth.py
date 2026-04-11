"""Register/login helpers for API tests (Bearer JWT)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

TEST_PASSWORD = "test-pass-word-10chars"


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
    r2 = client.post(
        "/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert r2.status_code == 200, r2.text
    token = r2.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r3 = client.post("/v1/projects", json={"name": "Test project"}, headers=headers)
    assert r3.status_code == 201, r3.text
    return str(r3.json()["id"]), headers
