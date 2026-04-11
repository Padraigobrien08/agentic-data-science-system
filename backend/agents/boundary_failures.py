"""
Stable failure classes for LLM ↔ orchestration boundaries and trace persistence.

These strings are persisted on run steps / ``ai_agents`` meta for debugging and dashboards.
They are **not** HTTP codes — keep them lowercase snake_case.
"""

from __future__ import annotations

from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.llm.exceptions import ChatCompletionProviderError

# --- LLM agent output (intent / planning / critic / report) ---
MODEL_OUTPUT_EMPTY = "model_output_empty"
MODEL_OUTPUT_INVALID_JSON = "model_output_invalid_json"
MODEL_OUTPUT_SCHEMA_INVALID = "model_output_schema_invalid"
MODEL_OUTPUT_SEMANTIC_INVALID = "model_output_semantic_invalid"

# --- Provider / configuration (not MCP tools) ---
LLM_PROVIDER_TRANSPORT_ERROR = "llm_provider_transport_error"
LLM_NOT_CONFIGURED = "llm_not_configured"

# --- Post-execution LLM chain ---
CRITIC_BLOCKED_REPORT = "critic_blocked_report"

# --- Coordinator → executor (deterministic plan) ---
EXECUTION_HANDOFF_REJECTED = "execution_handoff_rejected"


def agent_failure_code_to_boundary_class(code: str) -> str:
    return {
        AgentFailureCode.MODEL_EMPTY: MODEL_OUTPUT_EMPTY,
        AgentFailureCode.MODEL_JSON: MODEL_OUTPUT_INVALID_JSON,
        AgentFailureCode.MODEL_SCHEMA: MODEL_OUTPUT_SCHEMA_INVALID,
        AgentFailureCode.MODEL_SEMANTIC: MODEL_OUTPUT_SEMANTIC_INVALID,
    }.get(code, MODEL_OUTPUT_SCHEMA_INVALID)


def classify_llm_phase_exception(exc: BaseException) -> str:
    """Map an exception from an LLM agent phase to a persisted boundary class."""
    if isinstance(exc, AgentOutputError):
        return agent_failure_code_to_boundary_class(exc.code)
    if isinstance(exc, ChatCompletionProviderError):
        return LLM_PROVIDER_TRANSPORT_ERROR
    return "unexpected_error"
