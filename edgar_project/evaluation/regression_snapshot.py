"""
Compact regression snapshots for benchmark outputs (sparse golden JSON files).

Category rules mirror :meth:`EvaluationRunner._derive_finding_categories` — keep in sync when that logic changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

REGRESSION_SCHEMA_VERSION = 1

_TRUST_KEYS = ("data_quality_csv", "metric_coverage_summary_csv", "manual_validation_csv")


def derive_finding_category_counts(
    unified_findings: pd.DataFrame,
    artifacts: dict[str, str],
) -> dict[str, int]:
    """Match evaluation runner category tagging (for stable golden files)."""
    counts: dict[str, int] = {}
    if unified_findings is not None and not unified_findings.empty:
        for _, row in unified_findings.iterrows():
            source = str(row.get("finding_source", ""))
            ftype = str(row.get("finding_type", ""))
            direction = str(row.get("direction", ""))
            caveats = str(row.get("caveat_codes", "none"))
            if source == "trend_break" or ftype in {"strong_shift", "moderate_shift"}:
                cat = "trend_break"
            elif ftype == "peer_relative":
                cat = "peer_outlier"
            elif "deteriorat" in direction or direction in {"low", "down"}:
                cat = "deterioration"
            elif caveats and caveats != "none":
                cat = "data_limitations"
            else:
                cat = "other"
            counts[cat] = counts.get(cat, 0) + 1
            if caveats and caveats != "none":
                counts["data_limitations"] = counts.get("data_limitations", 0) + 1

    if any(k in artifacts for k in _TRUST_KEYS):
        counts["trustworthiness"] = max(1, counts.get("trustworthiness", 0))
    return dict(sorted(counts.items()))


def _overlap_stats(unified_findings: pd.DataFrame) -> dict[str, Any]:
    if unified_findings is None or unified_findings.empty or "overlap_count" not in unified_findings.columns:
        return {
            "row_count": 0,
            "rows_overlap_ge_2": 0,
            "max_overlap_count": 0,
            "any_multi_source_overlap": False,
        }
    oc = pd.to_numeric(unified_findings["overlap_count"], errors="coerce").fillna(0).astype(int)
    mx = int(oc.max()) if len(oc) else 0
    ge2 = int((oc >= 2).sum())
    multi = False
    if "overlap_sources" in unified_findings.columns:
        multi = bool(unified_findings["overlap_sources"].astype(str).str.contains(";", regex=False).any())
    return {
        "row_count": int(len(unified_findings)),
        "rows_overlap_ge_2": ge2,
        "max_overlap_count": mx,
        "any_multi_source_overlap": multi,
    }


def _finding_type_counts(unified_findings: pd.DataFrame) -> dict[str, int]:
    if unified_findings is None or unified_findings.empty or "finding_type" not in unified_findings.columns:
        return {}
    vc = unified_findings["finding_type"].astype(str).value_counts().to_dict()
    return dict(sorted((str(k), int(v)) for k, v in vc.items()))


def _data_quality_fingerprint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False}
    df = pd.read_csv(path)
    out: dict[str, Any] = {"present": True, "row_count": int(len(df))}
    if "category" in df.columns:
        cats = sorted(df["category"].astype(str).unique().tolist())
        out["category_values"] = cats[:20]
        out["category_count"] = len(cats)
    return out


def build_regression_blob(
    *,
    case_id: str,
    unified_findings: pd.DataFrame | None,
    artifacts: dict[str, str],
) -> dict[str, Any]:
    """Stable, compact dict for golden JSON comparison (JSON-serializable, sorted keys at dump)."""
    uf = unified_findings if unified_findings is not None else pd.DataFrame()
    trust = {k: bool(k in artifacts and str(artifacts.get(k, "")).strip()) for k in _TRUST_KEYS}
    blob: dict[str, Any] = {
        "schema_version": REGRESSION_SCHEMA_VERSION,
        "case_id": case_id,
        "unified_findings": {
            "row_count": int(len(uf)),
            "finding_type_counts": _finding_type_counts(uf),
            "category_counts": derive_finding_category_counts(uf, artifacts),
            "overlap": _overlap_stats(uf),
            "column_names": sorted(uf.columns.astype(str).tolist()) if not uf.empty else [],
        },
        "trust_artifacts_present": dict(sorted(trust.items())),
    }
    dq_path_str = artifacts.get("data_quality_csv")
    if dq_path_str:
        blob["data_quality_summary"] = _data_quality_fingerprint(Path(dq_path_str))
    return blob


def dump_sorted_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def compare_regression_golden(actual: dict[str, Any], golden: dict[str, Any], *, path_label: str) -> list[str]:
    """
    Golden is a **subset**: every key path in golden must match actual.

    Supports nested dicts; lists must match exactly.
    """
    failures: list[str] = []

    def walk(g: Any, a: Any, prefix: str) -> None:
        if isinstance(g, dict):
            if not isinstance(a, dict):
                failures.append(f"{path_label}{prefix or '.'}: expected dict, got {type(a).__name__}")
                return
            for k, gv in sorted(g.items()):
                nk = f"{prefix}.{k}" if prefix else k
                if k not in a:
                    failures.append(f"{path_label}{nk}: missing in actual")
                    continue
                walk(gv, a[k], nk)
            return
        if g != a:
            failures.append(f"{path_label}{prefix or '.'}: expected {g!r}, got {a!r}")

    walk(golden, actual, "")
    return failures


def load_golden(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
