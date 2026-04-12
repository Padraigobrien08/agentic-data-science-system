"""Offline LLM context size comparison (dev utility)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.agents.context_budget import ContextBudget
from backend.dev.llm_context_compare import (
    BUDGET_PRESETS,
    budget_from_spec,
    compare_budgets,
    json_utf8_bytes,
    merge_budget_overrides,
)


def test_compare_budgets_tight_smaller_than_default_for_critic() -> None:
    rows = compare_budgets(ContextBudget(), merge_budget_overrides(ContextBudget(), BUDGET_PRESETS["tight"]))
    by_phase = {r.phase: r for r in rows}
    assert by_phase["critic"].new_bytes < by_phase["critic"].old_bytes
    assert by_phase["critic"].reduction_pct is not None
    assert by_phase["critic"].reduction_pct > 30


def test_json_utf8_bytes_matches_wire_shape() -> None:
    d = {"x": "π", "n": 1}
    assert json_utf8_bytes(d) == len(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def test_budget_from_json_file(tmp_path: Path) -> None:
    p = tmp_path / "ov.json"
    p.write_text(json.dumps({"max_step_rows": 3}), encoding="utf-8")
    b = budget_from_spec(str(p))
    assert b.max_step_rows == 3


def test_merge_budget_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="Unknown ContextBudget"):
        merge_budget_overrides(ContextBudget(), {"not_a_field": 1})
