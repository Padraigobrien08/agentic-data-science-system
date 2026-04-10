"""
Curated demo scenarios for ``python3 -m edgar_project.cli demo``.

Definitions live in :file:`scenarios.json` (version-controlled, inspectable).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCENARIOS_FILE = Path(__file__).resolve().parent / "scenarios.json"


@dataclass(frozen=True)
class DemoScenario:
    """One curated live-demo scenario (orchestration + SEC/MCP)."""

    id: str
    title: str
    description: str
    tickers: list[str]
    goal: str
    look_for: list[str]
    highlights: list[str]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DemoScenario:
        return cls(
            id=str(raw["id"]),
            title=str(raw["title"]),
            description=str(raw["description"]),
            tickers=[str(t).strip().upper() for t in raw["tickers"]],
            goal=str(raw["goal"]).strip(),
            look_for=[str(x).strip() for x in raw.get("look_for", [])],
            highlights=[str(x).strip() for x in raw.get("highlights", [])],
        )


def scenarios_path() -> Path:
    return _SCENARIOS_FILE


def load_demo_catalog() -> tuple[int, str, list[DemoScenario]]:
    """
    Load ``scenarios.json``.

    Returns ``(schema_version, default_scenario_id, scenarios)``.
    """
    data = json.loads(_SCENARIOS_FILE.read_text(encoding="utf-8"))
    version = int(data.get("schema_version", 1))
    default_id = str(data.get("default_scenario", "")).strip()
    raw_list = data.get("scenarios", [])
    if not isinstance(raw_list, list):
        raise ValueError("scenarios.json: 'scenarios' must be a list")
    scenarios = [DemoScenario.from_dict(item) for item in raw_list]
    return version, default_id, scenarios


def get_demo_scenario(scenario_id: str | None) -> DemoScenario:
    """
    Resolve ``scenario_id`` to a scenario, or use catalog default when None/empty.

    Raises ``KeyError`` if id is unknown.
    """
    version, default_id, scenarios = load_demo_catalog()
    _ = version
    by_id = {s.id: s for s in scenarios}
    sid = (scenario_id or default_id or "").strip()
    if not sid:
        raise KeyError("no scenario id and no default_scenario in catalog")
    if sid not in by_id:
        raise KeyError(sid)
    return by_id[sid]


def list_demo_scenario_ids() -> list[str]:
    _, _, scenarios = load_demo_catalog()
    return [s.id for s in scenarios]
