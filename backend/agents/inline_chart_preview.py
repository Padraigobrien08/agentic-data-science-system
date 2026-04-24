"""
Deterministic inline chart previews derived from trusted pipeline artifacts.

The backend owns D-01/D-04/D-05 chart eligibility so chat rendering stays read-only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_TREND_BREAKS,
)
from src.metric_extraction import sort_period_key

_TREND_SIGNAL_PRIORITY = {
    "strong_shift": 0,
    "moderate_shift": 1,
}
_PEER_ALERT_PRIORITY = {
    "extreme_high": 0,
    "extreme_low": 1,
}
_METRIC_LABELS = {
    "revenue": "Revenue",
    "revenue_growth_qoq": "Revenue growth (QoQ)",
    "revenue_growth_yoy": "Revenue growth",
    "net_margin": "Net margin",
    "current_ratio": "Current ratio",
    "debt_to_assets": "Debt to assets",
}
_VALUE_FORMATS = {
    "revenue": "currency",
    "revenue_growth_qoq": "percent",
    "revenue_growth_yoy": "percent",
    "net_margin": "percent",
    "current_ratio": "ratio",
    "debt_to_assets": "ratio",
}
_TREND_CHART_PERIOD_LIMIT = 6
_PEER_CHART_PERIOD_LIMIT = 3


def _read_artifact_csv(artifact_paths: dict[str, str], role_key: str) -> pd.DataFrame | None:
    path_str = artifact_paths.get(role_key)
    if not isinstance(path_str, str) or not path_str.strip():
        return None
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _period_key(period: Any) -> tuple[int, int]:
    key = sort_period_key(pd.Series([str(period)])).iloc[0]
    return key if isinstance(key, tuple) else (0, 0)


def _sort_frame_by_period(frame: pd.DataFrame, *, ascending: bool = True) -> pd.DataFrame:
    if frame.empty or "period" not in frame.columns:
        return frame
    out = frame.copy()
    out["_period_key"] = sort_period_key(out["period"].astype(str))
    out = out.sort_values("_period_key", ascending=ascending, kind="mergesort")
    return out.drop(columns="_period_key")


def _as_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def _metric_label(metric_key: str) -> str:
    return _METRIC_LABELS.get(metric_key, metric_key.replace("_", " ").title())


def _value_format(metric_key: str) -> str:
    return _VALUE_FORMATS.get(metric_key, "number")


def _feature_metric_rows(
    features_df: pd.DataFrame,
    *,
    cik: int,
    metric_key: str,
    limit: int,
) -> pd.DataFrame:
    required = {"cik", "period"}
    if not required.issubset(features_df.columns) or metric_key not in features_df.columns:
        return pd.DataFrame()
    frame = features_df.loc[features_df["cik"] == cik, ["period", metric_key]].copy()
    frame[metric_key] = pd.to_numeric(frame[metric_key], errors="coerce")
    frame = frame.dropna(subset=[metric_key])
    if frame.empty:
        return frame
    frame = _sort_frame_by_period(frame)
    if len(frame) > limit:
        frame = frame.iloc[-limit:].reset_index(drop=True)
    return frame.reset_index(drop=True)


def _trend_sort_key(row: dict[str, Any]) -> tuple[int, float, tuple[int, int], str, int]:
    signal = str(row.get("trend_signal_type") or "")
    trend_score = _as_float(row.get("trend_score")) or 0.0
    period_key = _period_key(row.get("period"))
    metric = str(row.get("metric") or "")
    cik = _as_int(row.get("cik")) or 0
    return (
        _TREND_SIGNAL_PRIORITY.get(signal, 99),
        -trend_score,
        (-period_key[0], -period_key[1]),
        metric,
        cik,
    )


def _build_trend_line_preview(
    features_df: pd.DataFrame | None,
    trend_df: pd.DataFrame | None,
) -> dict[str, Any] | None:
    if features_df is None or trend_df is None or trend_df.empty:
        return None

    candidate_rows: list[dict[str, Any]] = []
    for row in trend_df.to_dict("records"):
        signal = str(row.get("trend_signal_type") or "")
        if signal not in _TREND_SIGNAL_PRIORITY:
            continue
        if _as_bool(row.get("short_history_flag")) is not False:
            continue
        history_points = _as_int(row.get("history_points"))
        cik = _as_int(row.get("cik"))
        metric_key = str(row.get("metric") or "")
        if history_points is None or history_points < 4 or cik is None or not metric_key:
            continue
        feature_rows = _feature_metric_rows(
            features_df,
            cik=cik,
            metric_key=metric_key,
            limit=_TREND_CHART_PERIOD_LIMIT,
        )
        if len(feature_rows) < 4:
            continue
        row["_feature_rows"] = feature_rows
        candidate_rows.append(row)

    if not candidate_rows:
        return None

    selected = sorted(candidate_rows, key=_trend_sort_key)[0]
    metric_key = str(selected["metric"])
    cik = int(selected["cik"])
    feature_rows = selected["_feature_rows"]
    periods = feature_rows["period"].astype(str).tolist()

    marker_rows: list[dict[str, str]] = []
    seen_marker_periods: set[str] = set()
    for row in trend_df.to_dict("records"):
        if _as_int(row.get("cik")) != cik:
            continue
        if str(row.get("metric") or "") != metric_key:
            continue
        if str(row.get("trend_signal_type") or "") != "strong_shift":
            continue
        period = str(row.get("period") or "")
        if period not in periods or period in seen_marker_periods:
            continue
        seen_marker_periods.add(period)
        marker_rows.append({"x_value": period, "label": "Strong shift"})
    marker_rows = sorted(marker_rows, key=lambda row: _period_key(row["x_value"]))

    row_values = feature_rows[metric_key].tolist()
    direction = "lower" if row_values[-1] < row_values[0] else "higher"
    metric_label = _metric_label(metric_key)

    return {
        "chart_id": f"trend-{metric_key}-line",
        "kind": "line",
        "metric_key": metric_key,
        "metric_label": metric_label,
        "caption": (
            f"{metric_label} moved {direction} across recent periods, supporting the reported trend shift."
        ),
        "x_axis_label": "Period",
        "y_axis_label": metric_label,
        "value_format": _value_format(metric_key),
        "series": [
            {
                "key": "focal_company",
                "label": "Company",
                "color_token": "chart-1",
            }
        ],
        "rows": [
            {
                "x_value": str(row["period"]),
                "values": {"focal_company": float(row[metric_key])},
            }
            for row in feature_rows.to_dict("records")
        ],
        "markers": marker_rows,
        "source_artifact_roles": [ARTIFACT_KEY_FEATURES, ARTIFACT_KEY_TREND_BREAKS],
    }


def _peer_sort_key(row: dict[str, Any]) -> tuple[int, float, tuple[int, int], str, int]:
    alert = str(row.get("peer_alert") or "")
    peer_z = abs(_as_float(row.get("peer_z")) or 0.0)
    period_key = _period_key(row.get("period"))
    metric = str(row.get("metric") or "")
    cik = _as_int(row.get("cik")) or 0
    return (
        _PEER_ALERT_PRIORITY.get(alert, 99),
        -peer_z,
        (-period_key[0], -period_key[1]),
        metric,
        cik,
    )


def _build_peer_rows(
    features_df: pd.DataFrame,
    *,
    cik: int,
    metric_key: str,
) -> list[dict[str, Any]]:
    required = {"cik", "period"}
    if not required.issubset(features_df.columns) or metric_key not in features_df.columns:
        return []

    frame = features_df.loc[:, ["cik", "period", metric_key]].copy()
    frame[metric_key] = pd.to_numeric(frame[metric_key], errors="coerce")
    frame = frame.dropna(subset=[metric_key])
    if frame.empty:
        return []

    period_rows: list[dict[str, Any]] = []
    for period, group in frame.groupby("period", sort=False):
        focal = group.loc[group["cik"] == cik, metric_key]
        peer_values = group.loc[group["cik"] != cik, metric_key]
        if focal.empty or peer_values.shape[0] < 2:
            continue
        period_rows.append(
            {
                "x_value": str(period),
                "values": {
                    "focal_company": float(focal.iloc[0]),
                    "peer_median": float(peer_values.median()),
                },
            }
        )

    if len(period_rows) < 2:
        return []
    period_rows = sorted(period_rows, key=lambda row: _period_key(row["x_value"]))
    if len(period_rows) > _PEER_CHART_PERIOD_LIMIT:
        period_rows = period_rows[-_PEER_CHART_PERIOD_LIMIT :]
    return period_rows


def _build_peer_grouped_bar_preview(
    features_df: pd.DataFrame | None,
    peer_df: pd.DataFrame | None,
) -> dict[str, Any] | None:
    if features_df is None or peer_df is None or peer_df.empty:
        return None

    candidate_rows: list[dict[str, Any]] = []
    for row in peer_df.to_dict("records"):
        if str(row.get("peer_coverage") or "") != "full":
            continue
        alert = str(row.get("peer_alert") or "")
        if alert not in _PEER_ALERT_PRIORITY:
            continue
        cik = _as_int(row.get("cik"))
        metric_key = str(row.get("metric") or "")
        peer_group_n = _as_int(row.get("peer_group_n"))
        if cik is None or not metric_key or peer_group_n is None or peer_group_n < 3:
            continue
        rows = _build_peer_rows(features_df, cik=cik, metric_key=metric_key)
        if len(rows) < 2:
            continue
        row["_peer_rows"] = rows
        candidate_rows.append(row)

    if not candidate_rows:
        return None

    selected = sorted(candidate_rows, key=_peer_sort_key)[0]
    metric_key = str(selected["metric"])
    alert = str(selected["peer_alert"])
    relation = "above" if alert == "extreme_high" else "below"
    metric_label = _metric_label(metric_key)

    return {
        "chart_id": f"peer-{metric_key}-grouped_bar",
        "kind": "grouped_bar",
        "metric_key": metric_key,
        "metric_label": metric_label,
        "caption": (
            f"{metric_label} stayed {relation} the peer median across recent common periods, grounding the peer comparison."
        ),
        "x_axis_label": "Period",
        "y_axis_label": metric_label,
        "value_format": _value_format(metric_key),
        "series": [
            {
                "key": "focal_company",
                "label": "Company",
                "color_token": "chart-1",
            },
            {
                "key": "peer_median",
                "label": "Peer median",
                "color_token": "chart-2",
            },
        ],
        "rows": list(selected["_peer_rows"]),
        "markers": [],
        "source_artifact_roles": [ARTIFACT_KEY_FEATURES, ARTIFACT_KEY_PEER_SIGNALS],
    }


def build_inline_chart_previews(
    artifact_paths: dict[str, str],
    *,
    max_charts: int = 2,
) -> list[dict[str, Any]]:
    """
    Build at most one D-10 trend line chart and one D-11 grouped peer bar chart.

    Weak or underspecified inputs fail closed to ``[]`` rather than speculative visuals.
    """
    if max_charts <= 0:
        return []

    features_df = _read_artifact_csv(artifact_paths, ARTIFACT_KEY_FEATURES)
    trend_df = _read_artifact_csv(artifact_paths, ARTIFACT_KEY_TREND_BREAKS)
    peer_df = _read_artifact_csv(artifact_paths, ARTIFACT_KEY_PEER_SIGNALS)

    previews: list[dict[str, Any]] = []

    trend_preview = _build_trend_line_preview(features_df, trend_df)
    if trend_preview is not None and len(previews) < max_charts:
        previews.append(trend_preview)

    peer_preview = _build_peer_grouped_bar_preview(features_df, peer_df)
    if peer_preview is not None and len(previews) < max_charts:
        previews.append(peer_preview)

    return previews
