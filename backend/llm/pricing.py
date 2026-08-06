"""
Token → USD cost estimation for model calls.

Prices are **operator configuration**, not a hardcoded table: model pricing changes
independently of this codebase, and a stale built-in table would silently produce
wrong numbers in cost budgets and cost metrics. ``EDGAR_BACKEND_LLM_MODEL_PRICES``
supplies them; models without a configured price contribute ``0.0`` and are logged
once so the gap is visible rather than silent.

Configuration is a JSON object keyed by model id, with USD per **one million** tokens::

    EDGAR_BACKEND_LLM_MODEL_PRICES='{"gpt-5.4-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60}}'

Consumers: the agentic loop's cost budget (``LoopBudget.max_cost_usd``) and the
``edgar_agent_cost_usd_total`` metric.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

log = structlog.get_logger(__name__)

_TOKENS_PER_UNIT = 1_000_000

#: Models already reported as unpriced, so the warning is emitted once per process.
_WARNED: set[str] = set()


@dataclass(frozen=True)
class ModelPrice:
    """USD per one million prompt / completion tokens."""

    input_per_1m: float = 0.0
    output_per_1m: float = 0.0

    def cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            (prompt_tokens * self.input_per_1m) + (completion_tokens * self.output_per_1m)
        ) / _TOKENS_PER_UNIT


def parse_model_prices(raw: object) -> dict[str, ModelPrice]:
    """
    Build a price table from settings, ignoring malformed entries.

    Pricing must never break a run: an unparseable entry is dropped with a warning
    rather than raised, so a typo in operator config degrades cost tracking instead
    of failing the investigation.
    """
    if not isinstance(raw, dict):
        return {}
    table: dict[str, ModelPrice] = {}
    for model, value in raw.items():
        if not isinstance(value, dict):
            log.warning("llm_price_entry_invalid", model=str(model), reason="not_an_object")
            continue
        try:
            price = ModelPrice(
                input_per_1m=float(value.get("input_per_1m", 0.0) or 0.0),
                output_per_1m=float(value.get("output_per_1m", 0.0) or 0.0),
            )
        except (TypeError, ValueError):
            log.warning("llm_price_entry_invalid", model=str(model), reason="non_numeric")
            continue
        if price.input_per_1m < 0 or price.output_per_1m < 0:
            log.warning("llm_price_entry_invalid", model=str(model), reason="negative")
            continue
        table[str(model)] = price
    return table


def estimate_cost_usd(
    prices: dict[str, ModelPrice],
    *,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float:
    """
    Cost of one call, or ``0.0`` when the model is unpriced or usage is unknown.

    Returning zero (rather than guessing) keeps an unconfigured deployment honest:
    the cost budget simply never binds, instead of binding on invented numbers.
    """
    price = prices.get(model)
    if price is None:
        if model not in _WARNED:
            _WARNED.add(model)
            log.info("llm_model_unpriced", model=model,
                     hint="set EDGAR_BACKEND_LLM_MODEL_PRICES to enable cost tracking")
        return 0.0
    return price.cost_usd(int(prompt_tokens or 0), int(completion_tokens or 0))
