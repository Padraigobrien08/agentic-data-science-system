"""JSON-safe tool params for :class:`ToolCallStep` (shared by planner output and executor)."""

from __future__ import annotations

from edgar_project.orchestration.schemas import JsonDict, ToolParamValue


def json_safe_tool_params(tool_input: JsonDict) -> dict[str, ToolParamValue]:
    """Map a planned step ``tool_input`` to JSON-serializable ``ToolCallStep.params``."""
    out: dict[str, ToolParamValue] = {}
    for k, v in tool_input.items():
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = v
        elif isinstance(v, int):
            out[k] = v
        elif isinstance(v, float):
            out[k] = v
        elif isinstance(v, str):
            out[k] = v
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            out[k] = v
    return out
