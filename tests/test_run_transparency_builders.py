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
                "critic": {
                    "phase_status": "success",
                    "overall_confidence": "medium",
                    "blocking_caveats": ["Caveat one"],
                    "confidence_explainer": {
                        "supports": ["Findings align with the stated goal."],
                        "weakens": ["Peer validation is incomplete."],
                        "limits": ["Only eight quarters were available for comparison."],
                    },
                },
                "report": {
                    "phase_status": "success",
                    "key_takeaways_preview": ["Takeaway one", "Takeaway two"],
                    "narrative_answer": {
                        "mode": "full",
                        "thesis": "The evidence supports a cautious deterioration thesis.",
                        "sections": [
                            {
                                "heading": "What's happening",
                                "body": "Recent summarized rows show repeated revenue-growth weakening.",
                            },
                            {
                                "heading": "Why we think that",
                                "body": "The report anchors that view in the loaded findings summaries.",
                            },
                        ],
                        "fallback_reason": None,
                    },
                },
            },
        }
    }
    arts = [_fake_artifact(rid=e1, role="panel_csv")]
    out = build_run_transparency_summary(meta, model_call_count=3, artifacts=arts)
    assert out.model_call_count == 3
    assert out.evidence_artifact_ids == [e1, e2]
    assert out.evidence_artifacts_by_role == {"panel_csv": e1}
    assert out.prompt_versions == {"intent": "v1"}
    assert out.report_key_takeaways_preview == ["Takeaway one", "Takeaway two"]
    assert out.narrative_answer is not None
    assert out.narrative_answer.mode == "full"
    assert out.narrative_answer.thesis == "The evidence supports a cautious deterioration thesis."
    assert out.narrative_answer.sections[0].heading == "What's happening"
    assert out.critic_blocking_caveats == ["Caveat one"]
    assert out.critic_overall_confidence == "medium"
    assert out.critic_phase_status == "success"
    assert out.report_phase_status == "success"
    assert out.confidence_explainer is not None
    assert out.confidence_explainer.supports == ["Findings align with the stated goal."]
    assert out.confidence_explainer.weakens == ["Peer validation is incomplete."]
    assert out.confidence_explainer.limits == ["Only eight quarters were available for comparison."]


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


def test_build_run_transparency_partial_narrative_preview() -> None:
    meta = {
        "ai_agents": {
            "traceability": {
                "report": {
                    "phase_status": "success",
                    "key_takeaways_preview": ["The evidence is limited but points to weaker growth."],
                    "narrative_answer": {
                        "mode": "partial",
                        "thesis": "The evidence is limited but points to weaker growth.",
                        "sections": [
                            {
                                "heading": "What weakens the claim",
                                "body": "Peer validation is incomplete, so the conclusion is only partial.",
                            }
                        ],
                        "fallback_reason": "limited_evidence",
                    },
                }
            }
        }
    }
    out = build_run_transparency_summary(meta, model_call_count=0, artifacts=[])
    assert out.narrative_answer is not None
    assert out.narrative_answer.mode == "partial"
    assert out.narrative_answer.fallback_reason == "limited_evidence"
    assert out.narrative_answer.sections[0].heading == "What weakens the claim"


def test_build_run_transparency_parses_d04_safe_inline_charts() -> None:
    meta = {
        "ai_agents": {
            "traceability": {
                "report": {
                    "inline_charts": [
                        {
                            "chart_id": "trend-revenue-growth-line",
                            "kind": "line",
                            "metric_key": "revenue_growth_yoy",
                            "metric_label": "Revenue growth",
                            "caption": "Revenue growth turned down across the latest four quarters.",
                            "x_axis_label": "Quarter",
                            "y_axis_label": "Growth",
                            "value_format": "percent",
                            "series": [
                                {
                                    "key": "focal_company",
                                    "label": "Company",
                                    "color_token": "chart-1",
                                }
                            ],
                            "rows": [
                                {
                                    "x_value": "2024-Q1",
                                    "focal_company": -0.02,
                                },
                                {
                                    "x_value": "2024-Q2",
                                    "focal_company": -0.06,
                                },
                            ],
                            "markers": [
                                {
                                    "x_value": "2024-Q2",
                                    "label": "Strong shift",
                                }
                            ],
                            "source_artifact_roles": ["features_csv", "trend_break_signals_csv"],
                        }
                    ]
                }
            }
        }
    }
    out = build_run_transparency_summary(meta, model_call_count=0, artifacts=[])
    assert len(out.inline_charts) == 1
    chart = out.inline_charts[0]
    assert chart.chart_id == "trend-revenue-growth-line"
    assert chart.kind == "line"
    assert chart.metric_key == "revenue_growth_yoy"
    assert chart.metric_label == "Revenue growth"
    assert chart.caption == "Revenue growth turned down across the latest four quarters."
    assert chart.x_axis_label == "Quarter"
    assert chart.y_axis_label == "Growth"
    assert chart.value_format == "percent"
    assert chart.series[0].key == "focal_company"
    assert chart.series[0].label == "Company"
    assert chart.series[0].color_token == "chart-1"
    assert chart.rows[0].x_value == "2024-Q1"
    assert chart.rows[0].values == {"focal_company": -0.02}
    assert chart.markers[0].x_value == "2024-Q2"
    assert chart.markers[0].label == "Strong shift"
    assert chart.source_artifact_roles == ["features_csv", "trend_break_signals_csv"]


def test_build_run_transparency_inline_charts_fall_back_to_empty_list_for_malformed_data() -> None:
    meta = {
        "ai_agents": {
            "traceability": {
                "report": {
                    "inline_charts": [
                        {
                            "chart_id": "peer-margin-bars",
                            "kind": "scatter",
                            "metric_key": "gross_margin",
                            "metric_label": "Gross margin",
                            "caption": "Unsupported chart kind should be rejected.",
                            "x_axis_label": "Quarter",
                            "y_axis_label": "Margin",
                            "value_format": "percent",
                            "series": [
                                {
                                    "key": "company",
                                    "label": "Company",
                                    "color_token": "chart-9",
                                }
                            ],
                            "rows": [{"x_value": "2024-Q1", "company": 0.4}],
                            "markers": [],
                            "source_artifact_roles": ["peer_signals_csv"],
                        }
                    ]
                }
            }
        }
    }
    out = build_run_transparency_summary(meta, model_call_count=0, artifacts=[])
    assert out.inline_charts == []


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
