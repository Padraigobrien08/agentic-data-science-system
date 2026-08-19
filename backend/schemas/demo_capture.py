"""
The demo capture bundle — what a published replay needs that the public
investigation contract deliberately does not carry.

:func:`backend.schemas.investigation.build_detail` is the API contract, and raw model
payloads are admin-gated behind it (``require_admin_debug_access`` on
``GET /v1/runs/{id}/model-calls``). Publishing a demo is a separate, deliberate act by an
operator over a run they chose to expose, so the prompts, responses and chat turns behind a
*published* investigation ship in this bundle rather than being bolted onto that contract.
Nothing here widens what a live run exposes.

The bundle exists because a recorded run costs real money: everything expensive to
reproduce is captured once, at publish time, while the rows are still intact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from backend.llm.pricing import ModelPrice, estimate_cost_usd


class DemoModelCall(BaseModel):
    """One model invocation, including the payloads that make a replay legible."""

    sequence: int
    id: UUID
    provider: str
    model_name: str
    prompt_id: str | None = None
    prompt_version: str | None = None
    status: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    est_cost_usd: float | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    request_payload_json: dict | list | None = None
    response_payload_json: dict | list | None = None
    error_detail: str | None = None


class DemoChatMessage(BaseModel):
    sequence: int
    id: UUID
    role: str
    status: str
    content: str | None = None
    analysis_run_id: UUID | None = None
    created_at: datetime


class DemoChatThread(BaseModel):
    """The conversation the run was commissioned from, when it was recorded with ``--chat``."""

    id: UUID
    title: str | None = None
    created_at: datetime
    messages: list[DemoChatMessage] = []


class DemoCaptureTotals(BaseModel):
    model_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    est_cost_usd: float = 0.0
    #: False when no price table is configured — the cost is then unknown, not zero.
    priced: bool = False


class DemoCapture(BaseModel):
    demo_slug: str
    investigation_id: UUID
    analysis_run_id: UUID | None = None
    totals: DemoCaptureTotals
    model_calls: list[DemoModelCall] = []
    chat: list[DemoChatThread] = []


def _enum_value(raw: Any) -> str:
    return str(getattr(raw, "value", raw))


def build_demo_capture(
    *,
    demo_slug: str,
    investigation_id: UUID,
    analysis_run_id: UUID | None,
    model_call_rows: list[Any],
    conversation_rows: list[Any],
    prices: dict[str, ModelPrice] | None = None,
) -> DemoCapture:
    """
    Assemble the bundle from already-fetched ORM rows.

    Pure mapping, like the other builders in this package: callers do the querying so this
    stays usable from the export script, a test, or a future route without dragging a
    session through it.
    """
    prices = prices or {}
    ordered = sorted(model_call_rows, key=lambda r: (r.started_at or r.created_at, str(r.id)))

    calls: list[DemoModelCall] = []
    totals = DemoCaptureTotals(priced=bool(prices))
    for i, row in enumerate(ordered):
        cost = (
            estimate_cost_usd(
                prices,
                model=row.model_name or "",
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
            )
            if prices
            else None
        )
        calls.append(
            DemoModelCall(
                sequence=i,
                id=row.id,
                provider=row.provider,
                model_name=row.model_name,
                prompt_id=row.prompt_id,
                prompt_version=row.prompt_version,
                status=_enum_value(row.status),
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                latency_ms=row.latency_ms,
                est_cost_usd=cost,
                started_at=row.started_at,
                finished_at=row.finished_at,
                request_payload_json=row.request_payload_json,
                response_payload_json=row.response_payload_json,
                error_detail=row.error_detail,
            )
        )
        totals.model_calls += 1
        totals.prompt_tokens += row.prompt_tokens or 0
        totals.completion_tokens += row.completion_tokens or 0
        totals.latency_ms += row.latency_ms or 0
        totals.est_cost_usd += cost or 0.0

    totals.total_tokens = totals.prompt_tokens + totals.completion_tokens
    totals.est_cost_usd = round(totals.est_cost_usd, 6)

    threads: list[DemoChatThread] = []
    for convo in sorted(conversation_rows, key=lambda c: c.created_at):
        messages = sorted(convo.messages, key=lambda m: m.created_at)
        threads.append(
            DemoChatThread(
                id=convo.id,
                title=convo.title,
                created_at=convo.created_at,
                messages=[
                    DemoChatMessage(
                        sequence=i,
                        id=m.id,
                        role=_enum_value(m.role),
                        status=_enum_value(m.status),
                        content=m.content,
                        analysis_run_id=m.analysis_run_id,
                        created_at=m.created_at,
                    )
                    for i, m in enumerate(messages)
                ],
            )
        )

    return DemoCapture(
        demo_slug=demo_slug,
        investigation_id=investigation_id,
        analysis_run_id=analysis_run_id,
        totals=totals,
        model_calls=calls,
        chat=threads,
    )
