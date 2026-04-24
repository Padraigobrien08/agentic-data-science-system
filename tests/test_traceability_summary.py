"""Runtime traceability bundle (decision summaries, tools, critic caveats)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
    StepStatusEntry,
)

from backend.agents.traceability_summary import (
    TRACEABILITY_CONTRACT_VERSION,
    _blocking_caveats_from_critic_patch,
    build_runtime_traceability_bundle,
)


def test_blocking_caveats_skipped_critic() -> None:
    caveats, conf = _blocking_caveats_from_critic_patch(
        {"skipped": True, "reason": "llm_provider_unavailable"},
    )
    assert "llm_provider_unavailable" in caveats
    assert conf is None


def test_blocking_caveats_success_low_confidence() -> None:
    caveats, conf = _blocking_caveats_from_critic_patch(
        {
            "skipped": False,
            "result": {
                "findings_assessment": "a",
                "caveat_coverage": "b",
                "trustworthiness_notes": "c",
                "issues": ["gap in data"],
                "overall_confidence": "low",
            },
        },
    )
    assert conf == "low"
    assert any("low" in x for x in caveats)
    assert "gap in data" in caveats


def test_build_runtime_traceability_bundle_shape() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="End-to-end",
        user_goal_text="run all",
    )
    tools = [{"order": 0, "tool_name": "resolve_company", "label": "r"}]
    out = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=ig,
        step_statuses=[
            StepStatusEntry(order=0, tool_name="resolve_company", mcp_status="success", label="r"),
        ],
        artifact_paths={"panel_csv": "/tmp/panel.csv"},
    )
    critic_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "findings_assessment": "f",
            "caveat_coverage": "c",
            "trustworthiness_notes": "t",
            "issues": [],
            "overall_confidence": "high",
        },
    }
    report_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "user_report_markdown": "# Hi",
            "key_takeaways": ["One", "Two"],
            "narrative_thesis": "A cautious deterioration signal is present in revenue growth.",
            "narrative_whats_happening": "Multiple periods show weaker revenue-growth rows in the summarized evidence.",
            "narrative_why_we_think_that": "The report ties the thesis to repeated period-level deterioration signals.",
            "narrative_what_weakens_claim": "Peer support is limited, so the claim is directional rather than conclusive.",
        },
    }
    full, c_step, r_step = build_runtime_traceability_bundle(
        interpreted_goal=ig,
        planning_source="deterministic_rules",
        selected_tools=tools,
        orch_out=out,
        mcp_step_count=1,
        base_idx=1,
        critic_patch=critic_patch,
        report_patch=report_patch,
        critic_summary_roles=["unified_findings_csv"],
    )
    assert full["contract_version"] == TRACEABILITY_CONTRACT_VERSION
    assert full["planning"]["selected_tools"] == tools
    assert "resolve_company" in full["planning"]["decision_summary"]
    assert full["intent"]["planning_transparency"]["present"] is True
    assert full["planning"]["planning_transparency"]["present"] is True
    assert full["critic"]["plan_alignment_findings"] == []
    assert full["critic"]["plan_alignment_codes"] == []
    assert full["critic"]["confidence_explainer"]["supports"]
    assert "f" in full["critic"]["confidence_explainer"]["supports"]
    assert full["critic"]["confidence_explainer"]["weakens"] == ["c"]
    assert full["critic"]["confidence_explainer"]["limits"] == ["t"]
    assert full["report"]["narrative_answer"]["mode"] == "full"
    assert full["report"]["narrative_answer"]["sections"][0]["heading"] == "What's happening"
    assert full["step_indices"]["critic"] == 1
    assert full["evidence_artifact_refs"][0]["role"] == "panel_csv"
    assert c_step["blocking_caveats"] == []
    assert r_step["key_takeaways_preview"]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> str:
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def _base_interpreted_goal() -> InterpretedGoal:
    return InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="End-to-end",
        user_goal_text="run all",
    )


def _base_traceability_inputs() -> tuple[InterpretedGoal, list[dict[str, str]], dict[str, object], dict[str, object]]:
    ig = _base_interpreted_goal()
    tools = [{"order": 0, "tool_name": "run_pipeline", "label": "pipeline"}]
    critic_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "findings_assessment": "f",
            "caveat_coverage": "c",
            "trustworthiness_notes": "t",
            "issues": [],
            "overall_confidence": "high",
        },
    }
    report_patch = {
        "phase_status": "success",
        "skipped": False,
        "result": {
            "user_report_markdown": "# Hi",
            "key_takeaways": ["One", "Two"],
            "narrative_thesis": "A cautious deterioration signal is present in revenue growth.",
            "narrative_whats_happening": "Multiple periods show weaker revenue-growth rows in the summarized evidence.",
            "narrative_why_we_think_that": "The report ties the thesis to repeated period-level deterioration signals.",
            "narrative_what_weakens_claim": "Peer support is limited, so the claim is directional rather than conclusive.",
        },
    }
    return ig, tools, critic_patch, report_patch


def _write_supported_chart_artifacts(
    tmp_path: Path,
    *,
    short_history: bool = False,
    weak_peer_coverage: bool = False,
    extra_candidates: bool = False,
) -> dict[str, str]:
    features_rows = [
        {"cik": 1, "period": "2024-Q1", "revenue_growth_qoq": 0.12, "net_margin": 0.18},
        {"cik": 1, "period": "2024-Q2", "revenue_growth_qoq": 0.08, "net_margin": 0.14},
        {"cik": 1, "period": "2024-Q3", "revenue_growth_qoq": -0.02, "net_margin": 0.1},
        {"cik": 1, "period": "2024-Q4", "revenue_growth_qoq": -0.08, "net_margin": 0.06},
        {"cik": 2, "period": "2024-Q1", "revenue_growth_qoq": 0.1, "net_margin": 0.12},
        {"cik": 2, "period": "2024-Q2", "revenue_growth_qoq": 0.09, "net_margin": 0.11},
        {"cik": 2, "period": "2024-Q3", "revenue_growth_qoq": 0.07, "net_margin": 0.1},
        {"cik": 2, "period": "2024-Q4", "revenue_growth_qoq": 0.06, "net_margin": 0.11},
        {"cik": 3, "period": "2024-Q1", "revenue_growth_qoq": 0.11, "net_margin": 0.13},
        {"cik": 3, "period": "2024-Q2", "revenue_growth_qoq": 0.1, "net_margin": 0.12},
        {"cik": 3, "period": "2024-Q3", "revenue_growth_qoq": 0.08, "net_margin": 0.11},
        {"cik": 3, "period": "2024-Q4", "revenue_growth_qoq": 0.07, "net_margin": 0.1},
    ]
    if short_history:
        features_rows = [
            row
            for row in features_rows
            if not (row["cik"] == 1 and row["period"] == "2024-Q1")
        ]

    trend_rows = [
        {
            "cik": 1,
            "period": "2024-Q4",
            "metric": "revenue_growth_qoq",
            "value": -0.08,
            "history_points": 3 if short_history else 4,
            "window_prior": 2,
            "window_recent": 2,
            "prior_mean": 0.1,
            "recent_mean": -0.05,
            "mean_shift": -0.15,
            "prior_slope": -0.01,
            "recent_slope": -0.03,
            "slope_shift": -0.02,
            "consecutive_direction": "deteriorating",
            "consecutive_len": 2,
            "short_history_flag": short_history,
            "trend_score": 2.8,
            "trend_signal_type": "strong_shift",
            "explanation": "revenue growth broke lower",
        },
        {
            "cik": 1,
            "period": "2024-Q3",
            "metric": "revenue_growth_qoq",
            "value": -0.02,
            "history_points": 4,
            "window_prior": 2,
            "window_recent": 2,
            "prior_mean": 0.11,
            "recent_mean": 0.03,
            "mean_shift": -0.08,
            "prior_slope": -0.01,
            "recent_slope": -0.02,
            "slope_shift": -0.01,
            "consecutive_direction": "deteriorating",
            "consecutive_len": 2,
            "short_history_flag": False,
            "trend_score": 2.1,
            "trend_signal_type": "strong_shift",
            "explanation": "revenue growth already weakened",
        },
    ]
    if extra_candidates:
        trend_rows.append(
            {
                "cik": 1,
                "period": "2024-Q4",
                "metric": "net_margin",
                "value": 0.06,
                "history_points": 4,
                "window_prior": 2,
                "window_recent": 2,
                "prior_mean": 0.16,
                "recent_mean": 0.08,
                "mean_shift": -0.08,
                "prior_slope": -0.01,
                "recent_slope": -0.02,
                "slope_shift": -0.01,
                "consecutive_direction": "deteriorating",
                "consecutive_len": 2,
                "short_history_flag": False,
                "trend_score": 2.4,
                "trend_signal_type": "strong_shift",
                "explanation": "margin weakened",
            }
        )

    peer_rows = [
        {
            "cik": 1,
            "period": "2024-Q4",
            "metric": "net_margin",
            "value": 0.06,
            "peer_group_n": 3,
            "peer_coverage": "rank_only" if weak_peer_coverage else "full",
            "peer_pct_rank": 5.0,
            "peer_z": -2.4,
            "peer_rank_signal": "low",
            "peer_z_signal": "low",
            "peer_alert": "extreme_low",
        },
    ]
    if extra_candidates:
        peer_rows.append(
            {
                "cik": 1,
                "period": "2024-Q3",
                "metric": "revenue_growth_qoq",
                "value": -0.02,
                "peer_group_n": 3,
                "peer_coverage": "full",
                "peer_pct_rank": 6.0,
                "peer_z": -2.2,
                "peer_rank_signal": "low",
                "peer_z_signal": "low",
                "peer_alert": "extreme_low",
            }
        )

    return {
        "features_csv": _write_csv(tmp_path / "features.csv", features_rows),
        "trend_break_signals_csv": _write_csv(tmp_path / "trend_breaks.csv", trend_rows),
        "peer_signals_csv": _write_csv(tmp_path / "peer_signals.csv", peer_rows),
    }


def test_build_inline_chart_previews_returns_line_and_grouped_bar(tmp_path: Path) -> None:
    from backend.agents.inline_chart_preview import build_inline_chart_previews

    artifact_paths = _write_supported_chart_artifacts(tmp_path)
    previews = build_inline_chart_previews(artifact_paths)

    assert len(previews) == 2
    assert previews[0]["kind"] == "line"
    assert previews[0]["chart_id"] == "trend-revenue_growth_qoq-line"
    assert previews[0]["source_artifact_roles"] == ["features_csv", "trend_break_signals_csv"]
    assert previews[0]["markers"][0]["label"] == "Strong shift"
    assert previews[1]["kind"] == "grouped_bar"
    assert previews[1]["chart_id"] == "peer-net_margin-grouped_bar"
    assert previews[1]["source_artifact_roles"] == ["features_csv", "peer_signals_csv"]


def test_build_inline_chart_previews_caps_results_to_one_per_family(tmp_path: Path) -> None:
    from backend.agents.inline_chart_preview import build_inline_chart_previews

    artifact_paths = _write_supported_chart_artifacts(tmp_path, extra_candidates=True)
    previews = build_inline_chart_previews(artifact_paths)

    assert len(previews) == 2
    assert [preview["kind"] for preview in previews] == ["line", "grouped_bar"]


def test_build_inline_chart_previews_suppresses_weak_peer_and_short_history(tmp_path: Path) -> None:
    from backend.agents.inline_chart_preview import build_inline_chart_previews

    artifact_paths = _write_supported_chart_artifacts(
        tmp_path,
        short_history=True,
        weak_peer_coverage=True,
    )
    previews = build_inline_chart_previews(artifact_paths)
    assert previews == []


def test_build_runtime_traceability_bundle_persists_inline_charts(tmp_path: Path) -> None:
    ig, tools, critic_patch, report_patch = _base_traceability_inputs()
    artifact_paths = _write_supported_chart_artifacts(tmp_path)
    out = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=ig,
        step_statuses=[
            StepStatusEntry(order=0, tool_name="run_pipeline", mcp_status="success", label="pipeline"),
        ],
        artifact_paths=artifact_paths,
    )

    full, _c_step, _r_step = build_runtime_traceability_bundle(
        interpreted_goal=ig,
        planning_source="deterministic_rules",
        selected_tools=tools,
        orch_out=out,
        mcp_step_count=1,
        base_idx=1,
        critic_patch=critic_patch,
        report_patch=report_patch,
        critic_summary_roles=["features_csv", "peer_signals_csv"],
    )

    assert len(full["report"]["inline_charts"]) == 2
    assert full["report"]["inline_charts"][0]["kind"] == "line"
    assert full["report"]["inline_charts"][1]["kind"] == "grouped_bar"
