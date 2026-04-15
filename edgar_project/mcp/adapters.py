"""
Thin adapters between MCP tools and Phase 1 code.

- Path / sys.path helpers
- Delegation to ``src.pipeline_runner`` and ``src.data_fetch`` (no duplicated business logic)
- CSV I/O for optional artifact inputs
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import requests
from edgar_project.run_workspace import RunWorkspace

from .schemas import (
    ARTIFACT_KEY_CACHE_COMPANYFACTS,
    ARTIFACT_KEY_CACHE_SUBMISSIONS,
    ArtifactSummary,
    CODE_SEC_FETCH,
    CODE_VALIDATION,
    ErrorInfo,
    TabularPreview,
    ToolResponseEnvelope,
    ToolStatus,
)


def repo_root() -> Path:
    """
    Repository root (parent of the ``edgar_project`` package).

    ``<repo>/edgar_project/mcp/adapters.py`` → ``parents[2] == <repo>``.
    """
    return Path(__file__).resolve().parents[2]


def ensure_sys_path() -> None:
    """Ensure repo root is importable as ``config`` + ``src``."""
    import sys

    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def phase1_paths(
    *,
    workspace: RunWorkspace | None = None,
    use_legacy_shared_paths: bool = False,
) -> dict[str, Path]:
    """Delegate to the workspace-aware Phase 1 registry.

    Shared repo-global paths remain available only via the explicit
    ``use_legacy_shared_paths=True`` compatibility branch.
    """
    ensure_sys_path()
    from src.pipeline_runner import legacy_phase1_paths as _legacy_paths
    from src.pipeline_runner import phase1_paths as _paths

    if workspace is not None:
        return _paths(workspace)
    if use_legacy_shared_paths:
        return _legacy_paths()
    raise ValueError("phase1_paths requires a workspace unless use_legacy_shared_paths=True")


def cache_paths_from_fetch_result(payload: dict[str, Any]) -> dict[str, str]:
    """
    Stable JSON cache paths for a ``get_company_data`` return dict.

    Keys match :mod:`edgar_project.mcp.schemas` artifact constants.
    """
    ensure_sys_path()
    import config

    cik10 = payload["cik10"]
    ticker_u = payload["ticker"]
    tdir = config.DATA_RAW / ticker_u
    sub = tdir / f"CIK{cik10}_submissions.json"
    fac = tdir / f"CIK{cik10}_companyfacts.json"
    return {
        ARTIFACT_KEY_CACHE_SUBMISSIONS: str(sub.resolve()),
        ARTIFACT_KEY_CACHE_COMPANYFACTS: str(fac.resolve()),
    }


def envelope_success(
    *,
    message: str = "",
    data: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> ToolResponseEnvelope:
    """``status=success`` with ``errors=[]``."""
    return ToolResponseEnvelope(
        status=ToolStatus.success,
        message=message,
        data=dict(data or {}),
        artifacts=dict(artifacts or {}),
        errors=[],
    )


def envelope_no_data(
    message: str,
    *,
    data: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> ToolResponseEnvelope:
    """``status=no_data`` — e.g. no extractable metrics for requested companies/periods."""
    return ToolResponseEnvelope(
        status=ToolStatus.no_data,
        message=message,
        data=dict(data or {}),
        artifacts=dict(artifacts or {}),
        errors=[],
    )


def envelope_error(
    message: str,
    errors: list[ErrorInfo],
    *,
    data: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> ToolResponseEnvelope:
    """``status=error`` with non-empty ``errors``."""
    if not errors:
        raise ValueError("envelope_error requires at least one ErrorInfo")
    return ToolResponseEnvelope(
        status=ToolStatus.error,
        message=message,
        data=dict(data or {}),
        artifacts=dict(artifacts or {}),
        errors=errors,
    )


def err_one(
    code: str,
    message: str,
    *,
    detail: str | None = None,
    http_status: int | None = None,
    exc_type: str | None = None,
) -> list[ErrorInfo]:
    """Build a one-element error list."""
    return [
        ErrorInfo(
            code=code,
            message=message,
            detail=detail,
            http_status=http_status,
            exc_type=exc_type,
        )
    ]


def err_from_http(exc: requests.HTTPError, *, code: str = CODE_SEC_FETCH) -> list[ErrorInfo]:
    st = exc.response.status_code if exc.response is not None else None
    return [
        ErrorInfo(
            code=code,
            message=f"SEC HTTP request failed ({st})" if st else "SEC HTTP request failed",
            detail=str(exc),
            http_status=st,
            exc_type=type(exc).__name__,
        )
    ]


def err_from_exception(exc: Exception, *, code: str, message: str | None = None) -> list[ErrorInfo]:
    return [
        ErrorInfo(
            code=code,
            message=message or type(exc).__name__,
            detail=str(exc),
            exc_type=type(exc).__name__,
        )
    ]


def envelope_from_validation(exc: Any) -> ToolResponseEnvelope:
    """Pydantic :class:`ValidationError` → error envelope (import lazily)."""
    from pydantic import ValidationError

    if not isinstance(exc, ValidationError):
        raise TypeError("expected ValidationError")
    return envelope_error(
        "Input validation failed",
        [
            ErrorInfo(
                code=CODE_VALIDATION,
                message="Invalid tool arguments",
                detail=exc.json(),
                exc_type="ValidationError",
            )
        ],
    )


def provenance_from_resolve(r: dict[str, Any]) -> dict[str, Any]:
    """
    Provenance block for a single ``resolve_company`` / ``get_company_data`` payload.

    Matches the shape produced by :func:`ticker_cik_pairs` for one ticker.
    """
    t = str(r["ticker"]).upper()
    c = int(r["cik"])
    return {
        "input_tickers": [t],
        "resolved_ciks": [{"ticker": t, "cik": c}],
        "ciks": [c],
    }


def resolve_company_dict(ticker: str) -> dict[str, Any]:
    """Delegate to :func:`src.data_fetch.resolve_company`."""
    ensure_sys_path()
    from src.data_fetch import resolve_company

    return resolve_company(ticker.strip())


def fetch_company_data_dict(ticker: str, *, refresh: bool) -> dict[str, Any]:
    """Delegate to :func:`src.data_fetch.get_company_data`."""
    ensure_sys_path()
    from src.data_fetch import get_company_data

    return get_company_data(ticker.strip(), refresh=refresh)


def build_panel_dataframe(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    """Delegate to :func:`src.pipeline_runner.build_panel_from_tickers`."""
    ensure_sys_path()
    from src.pipeline_runner import build_panel_from_tickers

    return build_panel_from_tickers(tickers, refresh=refresh)


def compute_features_dataframe(panel: pd.DataFrame) -> pd.DataFrame:
    """Delegate to :func:`src.features.compute_features`."""
    ensure_sys_path()
    from src.features import compute_features

    return compute_features(panel)


def detect_anomalies_dataframe(features: pd.DataFrame) -> pd.DataFrame:
    """Delegate to :func:`src.anomaly.detect_anomalies` with peer_signals precomputed."""
    ensure_sys_path()
    from src.anomaly import detect_anomalies
    from src.peer_signals import compute_peer_signals

    ps = compute_peer_signals(features)
    return detect_anomalies(features, peer_signals=ps)


def generate_report_markdown(
    anomalies: pd.DataFrame,
    features: pd.DataFrame,
    *,
    peer_signals: pd.DataFrame | None = None,
    data_quality: pd.DataFrame | None = None,
    exclusions: pd.DataFrame | None = None,
    manual_validation_path: Path | None = None,
) -> str:
    """Delegate to :func:`src.report.generate_report`."""
    ensure_sys_path()
    from src.report import generate_report

    return generate_report(
        anomalies,
        features,
        peer_signals=peer_signals,
        data_quality=data_quality,
        exclusions=exclusions,
        manual_validation_path=manual_validation_path,
        top_n=5,
    )


def run_full_pipeline(
    tickers: list[str],
    *,
    refresh: bool,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    str,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Delegate to :func:`src.pipeline_runner.run_pipeline_computation`."""
    ensure_sys_path()
    from src.pipeline_runner import run_pipeline_computation

    return run_pipeline_computation(tickers, refresh=refresh)


def write_panel_csv(panel: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_panel_csv as _w

    return _w(panel)


def write_features_csv(features: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_features_csv as _w

    return _w(features)


def write_anomalies_csv(anomalies: pd.DataFrame) -> Path:
    from src.pipeline_runner import write_anomalies_csv as _w

    return _w(anomalies)


def write_report_md(text: str) -> Path:
    from src.pipeline_runner import write_report_md as _w

    return _w(text)


def write_all_phase1_artifacts(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    anomalies: pd.DataFrame,
    report_markdown: str,
    *,
    data_quality: pd.DataFrame | None = None,
    exclusions: pd.DataFrame | None = None,
    peer_signals: pd.DataFrame | None = None,
    extraction_caveats_long: pd.DataFrame | None = None,
) -> dict[str, Path]:
    from src.pipeline_runner import write_all_phase1_artifacts as _w

    return _w(
        panel,
        features,
        anomalies,
        report_markdown,
        data_quality=data_quality,
        exclusions=exclusions,
        peer_signals=peer_signals,
        extraction_caveats_long=extraction_caveats_long,
    )


def read_panel_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_features_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_anomalies_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_peer_signals_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def peer_signal_params() -> dict[str, Any]:
    """Thresholds and metric list for :func:`src.peer_signals.compute_peer_signals`."""
    ensure_sys_path()
    from src.peer_signals import (
        PEER_MIN_FOR_RANK,
        PEER_MIN_FOR_Z,
        PEER_PCT_HIGH,
        PEER_PCT_LOW,
        PEER_SIGNAL_METRICS,
        PEER_Z_ALERT_THRESHOLD,
    )

    return {
        "metrics": list(PEER_SIGNAL_METRICS),
        "min_peers_for_rank": int(PEER_MIN_FOR_RANK),
        "min_peers_for_z": int(PEER_MIN_FOR_Z),
        "pct_high": float(PEER_PCT_HIGH),
        "pct_low": float(PEER_PCT_LOW),
        "z_alert_threshold": float(PEER_Z_ALERT_THRESHOLD),
        "peer_z_definition": "cross_section_includes_focal",
    }


def iso_mtime_utc(path: Path | str) -> str | None:
    """File mtime as ISO-8601 UTC, or None if missing."""
    p = Path(path).resolve()
    if not p.is_file():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()


def artifact_info(
    path: Path | str,
    *,
    row_count: int | None = None,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Compact metadata for one written artifact (path, mtime, optional shape)."""
    p = Path(path).resolve()
    out: dict[str, Any] = {"path": str(p)}
    ts = iso_mtime_utc(p)
    if ts:
        out["updated_at"] = ts
    if row_count is not None:
        out["row_count"] = row_count
    if columns is not None:
        out["columns"] = columns
    return out


def ticker_cik_pairs(tickers: list[str]) -> list[dict[str, Any]]:
    """Per-input ticker → CIK rows for provenance (uses SEC ticker map)."""
    out: list[dict[str, Any]] = []
    for t in tickers:
        d = resolve_company_dict(t)
        out.append({"ticker": d["ticker"], "cik": int(d["cik"])})
    return out


def sorted_unique_ciks(df: pd.DataFrame) -> list[int]:
    """Distinct CIKs from a panel/features frame."""
    if df.empty or "cik" not in df.columns:
        return []
    return sorted({int(x) for x in df["cik"].dropna().unique()})


def anomaly_detection_params() -> dict[str, Any]:
    """Rolling z-score settings and feature columns (see ``src.anomaly`` / ``config``)."""
    ensure_sys_path()
    import config
    from src.anomaly import FEATURE_COLS, MIN_PEER_GROUP

    return {
        "zscore_window": int(config.ZSCORE_WINDOW),
        "zscore_threshold": float(config.ZSCORE_THRESHOLD),
        "metrics_analyzed": list(FEATURE_COLS),
        "peer_min_group_size": int(MIN_PEER_GROUP),
    }


def dataframe_to_preview(
    df: pd.DataFrame,
    *,
    max_rows: int = 50,
) -> TabularPreview:
    """Convert a DataFrame to JSON-friendly rows (optional truncation)."""
    cols = [str(c) for c in df.columns]
    n = len(df)
    part = df.head(max_rows) if n > max_rows else df
    records = part.where(part.notna(), None).to_dict(orient="records")
    return TabularPreview(
        columns=cols,
        rows=records,
        row_count=n,
        truncated=n > max_rows,
    )


def summarize_path(path: Path) -> ArtifactSummary:
    exists = path.is_file()
    size = path.stat().st_size if exists else None
    return ArtifactSummary(path=str(path), exists=exists, size_bytes=size)


def read_json_records_from_csv(path: Path, *, max_rows: int = 100) -> TabularPreview:
    if not path.is_file():
        return TabularPreview(columns=[], rows=[], row_count=0, truncated=False)
    df = pd.read_csv(path)
    return dataframe_to_preview(df, max_rows=max_rows)
