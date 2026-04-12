"""API projection for per-run LLM token and cost aggregation by agent phase."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.model_call import ModelCall


class LlmPhaseUsageRow(BaseModel):
    """Aggregated usage for one logical phase (intent, planning, critic, …)."""

    phase: str = Field(description="Stable phase key: intent, planning, intent_preferences, critic, report, unknown.")
    call_count: int = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    latency_ms_total: int = Field(ge=0, description="Sum of per-call latency_ms (nulls treated as 0).")
    estimated_cost_usd: float | None = Field(
        None,
        description="Sum of per-call estimates when pricing is configured for all used models.",
    )
    model_names: list[str] = Field(
        default_factory=list,
        description="Distinct model_name values seen in this phase (sorted).",
    )


class LlmUsageTotals(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    latency_ms_total: int = Field(ge=0)
    estimated_cost_usd: float | None = None
    call_count: int = Field(ge=0)


class LlmRunUsageSummary(BaseModel):
    """Full aggregation for one analysis run."""

    analysis_run_id: UUID
    phases: list[LlmPhaseUsageRow] = Field(default_factory=list)
    totals: LlmUsageTotals
    pricing_configured: bool = Field(
        description="True when ``agent_llm_pricing_json`` is non-empty (rates exist for cost math).",
    )
    pricing_complete: bool = Field(
        description="True when every call with token counts had a matching model entry in pricing JSON.",
    )
    pricing_source: str = Field(
        default="agent_llm_pricing_json",
        description="Where rates were loaded from (settings key).",
    )


class LlmRunUsageSummaryWire(BaseModel):
    """Embedding under transparency (GET /runs/{id} with include_transparency)."""

    phases: list[LlmPhaseUsageRow] = Field(default_factory=list)
    totals: LlmUsageTotals
    pricing_configured: bool
    pricing_complete: bool
    pricing_source: str = "agent_llm_pricing_json"


def _parse_pricing_map(raw: str) -> dict[str, dict[str, float]]:
    if not raw or not str(raw).strip():
        return {}
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        pp = v.get("prompt_usd_per_1m")
        cp = v.get("completion_usd_per_1m")
        try:
            row = {
                "prompt_usd_per_1m": float(pp) if pp is not None else 0.0,
                "completion_usd_per_1m": float(cp) if cp is not None else 0.0,
            }
        except (TypeError, ValueError):
            continue
        out[k.strip()] = row
    return out


def _estimate_call_cost_usd(
    model_name: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    pricing: dict[str, dict[str, float]],
) -> float | None:
    if prompt_tokens is None and completion_tokens is None:
        return None
    pt = int(prompt_tokens or 0)
    ct = int(completion_tokens or 0)
    rates = pricing.get(model_name.strip())
    if rates is None:
        return None
    p1m = rates.get("prompt_usd_per_1m", 0.0)
    c1m = rates.get("completion_usd_per_1m", 0.0)
    return (pt / 1_000_000.0) * p1m + (ct / 1_000_000.0) * c1m


def infer_phase_from_model_call(row: ModelCall) -> str:
    """Map persisted row to a stable phase string."""
    from backend.agents.prompt_registry import AGENT_PROMPT_IDS

    prompt_to_role = {v: k for k, v in AGENT_PROMPT_IDS.items()}
    if row.prompt_id and row.prompt_id in prompt_to_role:
        return prompt_to_role[row.prompt_id]

    payload = row.request_payload_json
    if isinstance(payload, dict):
        agent = payload.get("agent")
        if isinstance(agent, dict):
            ph = agent.get("phase")
            if isinstance(ph, str) and ph.strip():
                p = ph.strip()
                if p == "intent_preferences":
                    return "intent_preferences"
                return p
            role = agent.get("role")
            if isinstance(role, str) and role.strip():
                r = role.strip()
                if r == "intent_preferences_assistant":
                    return "intent_preferences"
                if r in AGENT_PROMPT_IDS:
                    return r
    return "unknown"


PHASE_SORT_ORDER: tuple[str, ...] = (
    "intent",
    "intent_preferences",
    "planning",
    "critic",
    "report",
    "unknown",
)


def aggregate_llm_usage_for_calls(
    analysis_run_id: UUID,
    calls: list[ModelCall],
    *,
    pricing_json: str,
) -> LlmRunUsageSummary:
    """
    Sum tokens and latency by phase; estimate cost when every token-bearing call has a model entry
    in the pricing map (otherwise totals/phase costs are null but tokens still sum).
    """
    pricing = _parse_pricing_map(pricing_json)
    has_rates = bool(pricing)
    buckets: dict[str, dict[str, Any]] = {}

    def _ensure(phase: str) -> dict[str, Any]:
        if phase not in buckets:
            buckets[phase] = {
                "call_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms_total": 0,
                "cost_sum": 0.0,
                "cost_incomplete": False,
                "models": set(),
            }
        return buckets[phase]

    run_calls = [mc for mc in calls if mc.analysis_run_id == analysis_run_id]

    for mc in run_calls:
        phase = infer_phase_from_model_call(mc)
        b = _ensure(phase)
        b["call_count"] += 1
        b["prompt_tokens"] += int(mc.prompt_tokens or 0)
        b["completion_tokens"] += int(mc.completion_tokens or 0)
        b["latency_ms_total"] += int(mc.latency_ms or 0)
        if mc.model_name:
            b["models"].add(mc.model_name.strip())

        cost = _estimate_call_cost_usd(mc.model_name, mc.prompt_tokens, mc.completion_tokens, pricing)
        has_tokens = (mc.prompt_tokens or 0) > 0 or (mc.completion_tokens or 0) > 0
        if has_tokens and has_rates:
            if cost is None:
                b["cost_incomplete"] = True
            else:
                b["cost_sum"] += cost
        elif has_tokens and not has_rates:
            b["cost_incomplete"] = True

    def _phase_sort_key(p: str) -> tuple[int, str]:
        try:
            idx = PHASE_SORT_ORDER.index(p)
        except ValueError:
            idx = len(PHASE_SORT_ORDER)
        return (idx, p)

    phase_rows: list[LlmPhaseUsageRow] = []
    total_pt = 0
    total_ct = 0
    total_lat = 0
    total_calls = 0
    total_cost_sum = 0.0
    any_incomplete = not has_rates

    for phase in sorted(buckets.keys(), key=_phase_sort_key):
        b = buckets[phase]
        pc = b["prompt_tokens"]
        cc = b["completion_tokens"]
        lat = b["latency_ms_total"]
        n = b["call_count"]
        models = sorted(b["models"])
        inc = b["cost_incomplete"]
        csum = b["cost_sum"]
        if inc:
            any_incomplete = True
        phase_cost: float | None
        if not has_rates or inc:
            phase_cost = None
        else:
            phase_cost = round(csum, 8)

        phase_rows.append(
            LlmPhaseUsageRow(
                phase=phase,
                call_count=n,
                prompt_tokens=pc,
                completion_tokens=cc,
                latency_ms_total=lat,
                estimated_cost_usd=phase_cost,
                model_names=models,
            )
        )
        total_pt += pc
        total_ct += cc
        total_lat += lat
        total_calls += n
        if phase_cost is not None:
            total_cost_sum += phase_cost

    pricing_complete = has_rates and not any_incomplete and bool(run_calls)
    if not run_calls:
        pricing_complete = True

    totals_cost: float | None = None
    if pricing_complete and has_rates:
        totals_cost = round(total_cost_sum, 8)

    return LlmRunUsageSummary(
        analysis_run_id=analysis_run_id,
        phases=phase_rows,
        totals=LlmUsageTotals(
            prompt_tokens=total_pt,
            completion_tokens=total_ct,
            latency_ms_total=total_lat,
            estimated_cost_usd=totals_cost,
            call_count=total_calls,
        ),
        pricing_configured=has_rates,
        pricing_complete=pricing_complete,
        pricing_source="agent_llm_pricing_json",
    )


def to_transparency_wire(summary: LlmRunUsageSummary) -> LlmRunUsageSummaryWire:
    return LlmRunUsageSummaryWire(
        phases=summary.phases,
        totals=summary.totals,
        pricing_configured=summary.pricing_configured,
        pricing_complete=summary.pricing_complete,
        pricing_source=summary.pricing_source,
    )
