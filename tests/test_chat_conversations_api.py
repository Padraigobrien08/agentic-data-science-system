"""Durable chat conversations + messages API (v1.5 history persistence)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("fastapi")

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import create_app
from tests.api_auth import register_project_and_headers


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()


def _create_conversation(client: TestClient, project_id: str, headers: dict[str, str], **body) -> dict:
    r = client.post(f"/v1/projects/{project_id}/conversations", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list_conversation(api_client) -> None:
    client, project_id, headers = api_client
    conv = _create_conversation(client, project_id, headers, title="MSFT margins")
    assert conv["project_id"] == project_id
    assert conv["title"] == "MSFT margins"
    assert conv["last_message_at"] is None

    r = client.get(f"/v1/projects/{project_id}/conversations", headers=headers)
    assert r.status_code == 200, r.text
    ids = [c["id"] for c in r.json()]
    assert conv["id"] in ids


def test_new_chat_preserves_prior_threads(api_client) -> None:
    """v1.5 core: creating a new conversation must not hide the previous one."""
    client, project_id, headers = api_client
    first = _create_conversation(client, project_id, headers, title="First chat")
    second = _create_conversation(client, project_id, headers, title="Second chat")

    r = client.get(f"/v1/projects/{project_id}/conversations", headers=headers)
    assert r.status_code == 200, r.text
    ids = [c["id"] for c in r.json()]
    assert first["id"] in ids and second["id"] in ids


def test_append_messages_and_resume(api_client) -> None:
    client, project_id, headers = api_client
    conv = _create_conversation(client, project_id, headers)
    conv_id = conv["id"]

    r_user = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Is MSFT revenue growth deteriorating?"},
        headers=headers,
    )
    assert r_user.status_code == 201, r_user.text

    r_assist = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={
            "role": "assistant",
            "content": "Revenue growth shows intermittent deterioration.",
            "meta_json": {"evidence_strength": "medium"},
        },
        headers=headers,
    )
    assert r_assist.status_code == 201, r_assist.text

    # Resume: reopening the conversation restores its messages in order.
    r = client.get(f"/v1/conversations/{conv_id}", headers=headers)
    assert r.status_code == 200, r.text
    detail = r.json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    # Title derived from the first user prompt; ordering key refreshed.
    assert detail["title"] == "Is MSFT revenue growth deteriorating?"
    assert detail["last_message_at"] is not None


def test_conversation_owner_isolation(api_client) -> None:
    client, project_id, headers = api_client
    conv = _create_conversation(client, project_id, headers)

    # A different user must not see or reach the conversation (404, not 403).
    _other_project, other_headers = register_project_and_headers(client)
    r = client.get(f"/v1/conversations/{conv['id']}", headers=other_headers)
    assert r.status_code == 404, r.text


def test_delete_conversation(api_client) -> None:
    client, project_id, headers = api_client
    conv = _create_conversation(client, project_id, headers)
    r = client.delete(f"/v1/conversations/{conv['id']}", headers=headers)
    assert r.status_code == 204, r.text
    r2 = client.get(f"/v1/conversations/{conv['id']}", headers=headers)
    assert r2.status_code == 404
