"""Chat completion provider abstraction and ``ModelCall`` persistence."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.llm.exceptions import ChatCompletionProviderError, LLMProviderConfigurationError
from backend.llm.factory import get_chat_completion_provider
from backend.llm.types import ChatCompletionRequest, ChatCompletionResult
from backend.config.settings import Settings
from backend.models.enums import ModelCallStatus
from backend.models.model_call import ModelCall
from backend.services.recorded_chat_completion_service import RecordedChatCompletionService


class StubChatProvider:
    provider_id = "stub"

    def __init__(
        self,
        result: ChatCompletionResult | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._result = result
        self._exc = exc

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


@pytest.fixture
def memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def test_recorded_completion_persists_success(memory_session: Session) -> None:
    result = ChatCompletionResult(
        model="stub-model",
        assistant_text="hello",
        finish_reason="stop",
        prompt_tokens=3,
        completion_tokens=2,
        latency_ms=42,
        raw_response={"id": "chatcmpl-x"},
    )
    provider = StubChatProvider(result=result)
    svc = RecordedChatCompletionService(memory_session, provider)
    req = ChatCompletionRequest(model="stub-model", messages=[{"role": "user", "content": "hi"}])
    row, out = svc.complete_and_persist(req, analysis_run_id=None)
    memory_session.commit()

    assert out.assistant_text == "hello"
    assert row.status == ModelCallStatus.success
    assert row.provider == "stub"
    assert row.model_name == "stub-model"
    assert row.prompt_tokens == 3
    assert row.completion_tokens == 2
    assert row.latency_ms == 42
    assert row.request_payload_json == req.to_request_log_dict()
    assert row.response_payload_json == result.model_dump(mode="json")
    assert row.started_at is not None and row.finished_at is not None
    assert row.prompt_id is None and row.prompt_version is None


def test_recorded_completion_persists_prompt_columns(memory_session: Session) -> None:
    result = ChatCompletionResult(
        model="stub-model",
        assistant_text="x",
        finish_reason="stop",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1,
        raw_response={},
    )
    provider = StubChatProvider(result=result)
    svc = RecordedChatCompletionService(memory_session, provider)
    req = ChatCompletionRequest(model="stub-model", messages=[{"role": "user", "content": "hi"}])
    meta = {"role": "intent", "prompt_id": "edgar.agent.intent", "prompt_version": "1.0.0"}
    row, _ = svc.complete_and_persist(
        req,
        analysis_run_id=None,
        request_metadata=meta,
        prompt_id="edgar.agent.intent",
        prompt_version="1.0.0",
    )
    memory_session.commit()
    assert row.prompt_id == "edgar.agent.intent"
    assert row.prompt_version == "1.0.0"
    assert row.provider == "stub"
    assert row.model_name == "stub-model"


def test_recorded_completion_persists_provider_error(memory_session: Session) -> None:
    provider = StubChatProvider(exc=ChatCompletionProviderError("rate limit"))
    svc = RecordedChatCompletionService(memory_session, provider)
    req = ChatCompletionRequest(model="m", messages=[{"role": "user", "content": "x"}])
    with pytest.raises(ChatCompletionProviderError, match="rate limit"):
        svc.complete_and_persist(req)
    memory_session.commit()

    rows = list(memory_session.scalars(select(ModelCall)).all())
    assert len(rows) == 1
    assert rows[0].status == ModelCallStatus.error
    assert "rate limit" in (rows[0].error_detail or "")
    assert rows[0].latency_ms is not None


def test_mark_agent_output_failed_after_success(memory_session: Session) -> None:
    result = ChatCompletionResult(
        model="stub-model",
        assistant_text="{}",
        finish_reason="stop",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1,
        raw_response={},
    )
    svc = RecordedChatCompletionService(memory_session, StubChatProvider(result=result))
    row, _ = svc.complete_and_persist(
        ChatCompletionRequest(model="stub-model", messages=[{"role": "user", "content": "x"}]),
    )
    svc.mark_agent_output_failed(row.id, detail="schema mismatch", agent_code="model_output_schema_invalid")
    memory_session.commit()
    memory_session.refresh(row)
    assert row.status == ModelCallStatus.error
    assert "agent_output_invalid" in (row.error_detail or "")


def test_factory_openai_requires_key() -> None:
    with pytest.raises(LLMProviderConfigurationError):
        get_chat_completion_provider(
            Settings(llm_provider="openai", openai_api_key=None),
        )


def test_factory_openai_builds() -> None:
    p = get_chat_completion_provider(
        Settings(
            llm_provider="openai",
            openai_api_key=SecretStr("sk-test-key"),
            openai_base_url=None,
        ),
    )
    assert p.provider_id == "openai"


def test_factory_off_raises() -> None:
    with pytest.raises(LLMProviderConfigurationError):
        get_chat_completion_provider(Settings(llm_provider="off"))


@pytest.mark.integration
def test_openai_live_smoke() -> None:
    """Set OPENAI_API_KEY and EDGAR_BACKEND_LLM_PROVIDER=openai in environment to run."""
    import os

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    provider = get_chat_completion_provider(
        Settings(
            llm_provider="openai",
            openai_api_key=SecretStr(key),
        ),
    )
    req = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Reply with exactly: ok"}],
        max_tokens=16,
        temperature=0,
    )
    out = provider.complete(req)
    assert out.assistant_text
    assert out.latency_ms >= 0
    assert out.raw_response
