"""Unit tests for typed transparency projections (Sprint 3 API helpers)."""

from __future__ import annotations

from uuid import UUID, uuid4

from backend.models.artifact import Artifact
from backend.models.enums import ArtifactKind
from backend.schemas.run_transparency import (
    build_run_step_transparency,
    build_run_transparency_summary,
)


def _fake_artifact(*, rid: UUID, role: str) -> Artifact:
    a = Artifact()
    a.id = rid
    a.role_key = role
    a.kind = ArtifactKind.tabular
    a.analysis_run_id = uuid4()
    a.evaluation_run_id = None
    a.run_step_id = None
    a.mime_type = "text/csv"
    a.byte_size = 1
    a.content_sha256 = "a" * 64
    a.storage_uri = "local:x"
    return a


def test_build_run_transparency_from_traceability() -> None:
    e1, e2 = uuid4(), uuid4()
    meta = {
        "ai_agents": {
            "prompt_versions": {"intent": "v1"},
            "traceability": {
                "evidence_artifact_ids": [str(e1), str(e2)],
                "evidence_artifacts_by_role": {"panel_csv": str(e1)},
            },
        }
    }
    arts = [_fake_artifact(rid=e1, role="panel_csv")]
    out = build_run_transparency_summary(meta, model_call_count=3, artifacts=arts)
    assert out.model_call_count == 3
    assert out.evidence_artifact_ids == [e1, e2]
    assert out.evidence_artifacts_by_role == {"panel_csv": e1}
    assert out.prompt_versions == {"intent": "v1"}


def test_build_run_transparency_fallback_uses_artifact_table() -> None:
    r1, r2 = uuid4(), uuid4()
    arts = [_fake_artifact(rid=r1, role="a"), _fake_artifact(rid=r2, role="b")]
    out = build_run_transparency_summary({}, model_call_count=0, artifacts=arts)
    assert out.evidence_artifact_ids == [r1, r2]
    assert out.evidence_artifacts_by_role == {"a": r1, "b": r2}


def test_build_run_transparency_empty_explicit_ids_not_replaced() -> None:
    """When traceability includes an empty evidence list, do not substitute all artifacts."""
    meta = {"ai_agents": {"traceability": {"evidence_artifact_ids": []}}}
    r1 = uuid4()
    arts = [_fake_artifact(rid=r1, role="x")]
    out = build_run_transparency_summary(meta, model_call_count=0, artifacts=arts)
    assert out.evidence_artifact_ids == []


def test_build_run_step_transparency_critic_phase_output() -> None:
    sid = uuid4()
    meta = {
        "trace": "critic_agent",
        "phase": "llm",
        "model_call_id": str(sid),
        "phase_output": {
            "issue_count": 2,
            "overall_confidence": "low",
            "phase_status": "degraded",
            "weak_evidence_signals": ["thin_panel"],
        },
    }
    linked = [uuid4()]
    out = build_run_step_transparency(meta, linked)
    assert out.trace == "critic_agent"
    assert out.model_call_id == sid
    assert out.output_summary is not None
    assert out.output_summary.issue_count == 2
    assert out.output_summary.overall_confidence == "low"
    assert out.output_summary.weak_evidence_signals == ["thin_panel"]
    assert out.linked_artifact_ids == linked
