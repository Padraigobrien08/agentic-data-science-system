"""Merge helpers for ``analysis_run.meta_json['ai_agents']`` (no imports from other agent modules)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.services.analysis_run_service import AnalysisRunService


def merge_ai_agents_meta(session: Session, analysis_run_id: UUID, key: str, payload: object) -> None:
    """Merge ``payload`` under ``analysis_run.meta_json['ai_agents'][key]`` (preserves sibling keys)."""
    run_svc = AnalysisRunService(session)
    row = run_svc.require(analysis_run_id)
    base = row.meta_json if isinstance(row.meta_json, dict) else {}
    ai = dict(base.get("ai_agents") or {})
    ai[key] = payload
    run_svc.merge_meta_json(analysis_run_id, {"ai_agents": ai})


def merge_completion_models_entries(
    session: Session,
    analysis_run_id: UUID,
    entries: dict[str, Any],
) -> None:
    """Shallow-merge keys into ``meta_json['ai_agents']['completion_models']`` (keeps other agent keys)."""
    if not entries:
        return
    run_svc = AnalysisRunService(session)
    row = run_svc.require(analysis_run_id)
    base = row.meta_json if isinstance(row.meta_json, dict) else {}
    ai = dict(base.get("ai_agents") or {})
    cm = dict(ai.get("completion_models") or {})
    cm.update(entries)
    ai["completion_models"] = cm
    run_svc.merge_meta_json(analysis_run_id, {"ai_agents": ai})
