"""Merge helpers for ``analysis_run.meta_json['ai_agents']`` (no imports from other agent modules)."""

from __future__ import annotations

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
