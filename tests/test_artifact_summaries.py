"""Deterministic artifact summary bundle for LLM phases."""

from __future__ import annotations

import json
from pathlib import Path

from backend.agents.artifact_summaries import (
    SUMMARIES_CONTRACT,
    audit_summaries_bundle,
    build_artifact_summaries_for_llm,
    summarize_anomalies_csv,
)
from edgar_project.mcp.schemas import ARTIFACT_KEY_ANOMALIES, ARTIFACT_KEY_UNIFIED_FINDINGS


def test_summarize_anomalies_top_by_abs_z(tmp_path: Path) -> None:
    p = tmp_path / "a.csv"
    p.write_text(
        "cik,period,metric,abs_z,anomaly_category\n"
        "1,2020,x,0.1,cat_a\n"
        "1,2021,y,9.0,cat_b\n"
        "1,2022,z,2.0,cat_a\n",
        encoding="utf-8",
    )
    s = summarize_anomalies_csv(str(p))
    assert s["csv_data_rows_total"] == 3
    assert s["rows_selected_for_summary"] <= 3
    assert s["selection_rule"] == "top_rows_by_max_abs_zscore_or_abs_z"
    assert s["top_rows"][0].get("abs_z") == "9.0"
    assert "cat_a" in (s.get("anomaly_category_counts") or {})


def test_build_bundle_deterministic_order_and_index(tmp_path: Path) -> None:
    ano = tmp_path / "ano.csv"
    ano.write_text(
        "cik,metric,abs_z\n1,m1,1\n2,m2,3\n",
        encoding="utf-8",
    )
    uni = tmp_path / "uni.csv"
    uni.write_text(
        "ticker,score_adjusted\n"
        "A,10\n"
        "B,1\n",
        encoding="utf-8",
    )
    paths = {
        ARTIFACT_KEY_UNIFIED_FINDINGS: str(uni),
        ARTIFACT_KEY_ANOMALIES: str(ano),
    }
    b1 = build_artifact_summaries_for_llm(paths)
    b2 = build_artifact_summaries_for_llm(paths)
    assert b1["contract_version"] == SUMMARIES_CONTRACT
    assert b1 == b2
    roles = list((b1.get("by_role") or {}).keys())
    assert ARTIFACT_KEY_ANOMALIES in roles
    assert ARTIFACT_KEY_UNIFIED_FINDINGS in roles
    idx = b1.get("artifact_index") or []
    assert len(idx) >= 2
    for e in idx:
        assert "artifact_role" in e
        assert "selection_rule" in e


def test_audit_summaries_bundle_keys() -> None:
    bundle = {
        "contract_version": SUMMARIES_CONTRACT,
        "by_role": {"anomalies_csv": {"kind": "anomalies_csv"}},
    }
    a = audit_summaries_bundle(bundle)
    assert a["contract_version"] == SUMMARIES_CONTRACT
    assert a["roles_with_summaries"] == ["anomalies_csv"]
    assert a["approx_json_chars"] == len(json.dumps(bundle["by_role"], ensure_ascii=False))


def test_missing_path_produces_empty_summary() -> None:
    b = build_artifact_summaries_for_llm({ARTIFACT_KEY_ANOMALIES: "/no/such/path.csv"})
    s = (b.get("by_role") or {}).get(ARTIFACT_KEY_ANOMALIES)
    assert s is not None
    assert s.get("csv_data_rows_total") == 0
    assert s.get("selection_rule") == "none_empty"


def test_trustworthiness_role_gets_text_preview(tmp_path: Path) -> None:
    p = tmp_path / "trust.txt"
    p.write_text("x" * 5000, encoding="utf-8")
    b = build_artifact_summaries_for_llm({"run_trustworthiness_notes": str(p)})
    role = b["by_role"].get("run_trustworthiness_notes")
    assert role is not None
    assert role.get("kind") == "text_excerpt"
    assert role.get("truncated") is True
