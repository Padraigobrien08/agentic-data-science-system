"""
Artifact roles the critic prioritizes (findings, caveats, trustworthiness-adjacent outputs).

Paths come from :attr:`~edgar_project.orchestration.schemas.OrchestrationOutput.artifact_paths`.
"""

from __future__ import annotations

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_MANUAL_VALIDATION,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
)

from backend.agents.artifact_excerpts import read_text_excerpt

# Primary keys (stable MCP role strings).
CRITIC_PRIMARY_ARTIFACT_KEYS: tuple[str, ...] = (
    ARTIFACT_KEY_UNIFIED_FINDINGS,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_MANUAL_VALIDATION,
)


def collect_critic_excerpts(
    artifact_paths: dict[str, str],
    *,
    max_chars_per_file: int = 8000,
) -> dict[str, str]:
    """Role → excerpt text; includes any path whose key mentions ``trustworthiness``."""
    out: dict[str, str] = {}
    for key in CRITIC_PRIMARY_ARTIFACT_KEYS:
        p = artifact_paths.get(key)
        if p:
            ex = read_text_excerpt(p, max_chars=max_chars_per_file)
            if ex:
                out[key] = ex
    for role, p in sorted(artifact_paths.items()):
        if "trustworthiness" in role.lower() and role not in out:
            ex = read_text_excerpt(p, max_chars=max_chars_per_file)
            if ex:
                out[role] = ex
    return out
