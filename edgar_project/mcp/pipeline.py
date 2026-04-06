"""
Shared pipeline steps for MCP tools (calls repo-root ``src.*`` and ``config``).

Import ``config`` / ``src`` only after :func:`edgar_project.mcp.adapters.ensure_sys_path`.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from edgar_project.mcp.adapters import ensure_sys_path


def _import_config_and_src() -> None:
    ensure_sys_path()


def artifact_paths_dict() -> dict[str, Path]:
    """Phase 1 artifact paths (same as ``main.py``)."""
    _import_config_and_src()
    import config

    return {
        "panel": config.DATA_PROCESSED / "panel.csv",
        "features": config.DATA_PROCESSED / "features.csv",
        "anomalies": config.DATA_ARTIFACTS / "anomalies.csv",
        "report": config.DATA_ARTIFACTS / "report.md",
    }


def collect_long_frames(tickers: list[str], *, refresh: bool) -> list[pd.DataFrame]:
    """Fetch + extract_metrics for each ticker."""
    _import_config_and_src()
    import config
    from src.data_fetch import get_company_data
    from src.metric_extraction import extract_metrics

    out: list[pd.DataFrame] = []
    for t in tickers:
        d = get_company_data(t, refresh=refresh)
        out.append(extract_metrics(d["facts"], int(d["cik"]), years=config.YEARS_LOOKBACK))
    return out


def build_panel_dataframe(tickers: list[str], *, refresh: bool) -> pd.DataFrame:
    from src.normalization import build_panel

    frames = collect_long_frames(tickers, refresh=refresh)
    return build_panel(frames)


def compute_features_dataframe(panel: pd.DataFrame) -> pd.DataFrame:
    from src.features import compute_features

    return compute_features(panel)


def detect_anomalies_dataframe(features: pd.DataFrame) -> pd.DataFrame:
    from src.anomaly import detect_anomalies

    return detect_anomalies(features)


def write_panel_csv(panel: pd.DataFrame) -> Path:
    import config

    p = config.DATA_PROCESSED / "panel.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(p, index=False)
    return p.resolve()


def write_features_csv(features: pd.DataFrame) -> Path:
    import config

    p = config.DATA_PROCESSED / "features.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(p, index=False)
    return p.resolve()


def write_anomalies_csv(anomalies: pd.DataFrame) -> Path:
    import config

    p = config.DATA_ARTIFACTS / "anomalies.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(p, index=False)
    return p.resolve()


def write_report_md(report_md: str) -> Path:
    import config

    p = config.DATA_ARTIFACTS / "report.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report_md, encoding="utf-8")
    return p.resolve()


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
