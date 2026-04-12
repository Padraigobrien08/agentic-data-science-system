"""LLM usage aggregation by phase."""

from __future__ import annotations

import uuid

from backend.agents.prompt_registry import AGENT_PROMPT_IDS
from backend.models.enums import ModelCallStatus
from backend.models.model_call import ModelCall
from backend.schemas.llm_usage import aggregate_llm_usage_for_calls, infer_phase_from_model_call


def _mc(
    *,
    prompt_id: str | None,
    pt: int | None,
    ct: int | None,
    lat: int,
    model: str = "gpt-5.4-mini",
    req_agent: dict | None = None,
) -> ModelCall:
    rid = uuid.uuid4()
    payload = {"model": model, "messages": []}
    if req_agent:
        payload["agent"] = req_agent
    return ModelCall(
        id=uuid.uuid4(),
        analysis_run_id=rid,
        provider="openai",
        model_name=model,
        prompt_id=prompt_id,
        prompt_version="1.1.0",
        status=ModelCallStatus.success,
        prompt_tokens=pt,
        completion_tokens=ct,
        latency_ms=lat,
        request_payload_json=payload,
    )


def test_infer_phase_from_prompt_id() -> None:
    row = _mc(prompt_id=AGENT_PROMPT_IDS["critic"], pt=1, ct=1, lat=10)
    assert infer_phase_from_model_call(row) == "critic"


def test_infer_phase_intent_preferences_from_metadata() -> None:
    row = _mc(
        prompt_id=None,
        pt=1,
        ct=1,
        lat=5,
        req_agent={"phase": "intent_preferences", "role": "intent_preferences_assistant"},
    )
    assert infer_phase_from_model_call(row) == "intent_preferences"


def test_aggregate_tokens_and_latency_by_phase() -> None:
    rid = uuid.uuid4()
    calls = [
        ModelCall(
            id=uuid.uuid4(),
            analysis_run_id=rid,
            provider="openai",
            model_name="m1",
            prompt_id=AGENT_PROMPT_IDS["intent"],
            prompt_version="1.1.0",
            status=ModelCallStatus.success,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200,
            request_payload_json={"model": "m1", "messages": []},
        ),
        ModelCall(
            id=uuid.uuid4(),
            analysis_run_id=rid,
            provider="openai",
            model_name="m1",
            prompt_id=AGENT_PROMPT_IDS["planning"],
            prompt_version="1.1.0",
            status=ModelCallStatus.success,
            prompt_tokens=200,
            completion_tokens=100,
            latency_ms=300,
            request_payload_json={"model": "m1", "messages": []},
        ),
    ]
    out = aggregate_llm_usage_for_calls(rid, calls, pricing_json="{}")
    assert out.totals.prompt_tokens == 300
    assert out.totals.completion_tokens == 150
    assert out.totals.latency_ms_total == 500
    assert out.totals.estimated_cost_usd is None
    assert out.pricing_configured is False
    phases = {p.phase: p for p in out.phases}
    assert phases["intent"].prompt_tokens == 100
    assert phases["planning"].completion_tokens == 100


def test_aggregate_cost_when_pricing_complete() -> None:
    rid = uuid.uuid4()
    pricing = (
        '{"gpt-5.4-mini": {"prompt_usd_per_1m": 1.0, "completion_usd_per_1m": 2.0}}'
    )
    calls = [
        ModelCall(
            id=uuid.uuid4(),
            analysis_run_id=rid,
            provider="openai",
            model_name="gpt-5.4-mini",
            prompt_id=AGENT_PROMPT_IDS["intent"],
            prompt_version="1.1.0",
            status=ModelCallStatus.success,
            prompt_tokens=1_000_000,
            completion_tokens=500_000,
            latency_ms=100,
            request_payload_json={"model": "gpt-5.4-mini", "messages": []},
        ),
    ]
    out = aggregate_llm_usage_for_calls(rid, calls, pricing_json=pricing)
    assert out.pricing_complete is True
    assert out.totals.estimated_cost_usd is not None
    assert abs(out.totals.estimated_cost_usd - 2.0) < 0.001  # 1*1 + 0.5*2
