"""
MCP tool implementations — return :class:`ToolResponseEnvelope` only.

All exceptions are converted to ``status=error`` with structured ``errors[]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from edgar_project.mcp import adapters as ad
from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_CACHE_COMPANYFACTS,
    ARTIFACT_KEY_CACHE_SUBMISSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_REPORT,
    BuildPanelInput,
    CODE_EMPTY_INPUT,
    CODE_FILE_NOT_FOUND,
    CODE_INTERNAL,
    CODE_SEC_FETCH,
    CODE_UNKNOWN_TICKER,
    CODE_VALIDATION,
    ComputeFeaturesInput,
    DetectAnomaliesInput,
    FetchCompanyDataInput,
    GenerateReportInput,
    ResolveCompanyInput,
    RunPipelineInput,
    ToolResponseEnvelope,
)

ad.ensure_sys_path()


def _envelope_sec_request_failed(exc: requests.RequestException) -> ToolResponseEnvelope:
    """HTTP and non-HTTP request failures (timeouts, TLS, connection) toward SEC endpoints."""
    if isinstance(exc, requests.HTTPError):
        return ad.envelope_error(
            "SEC fetch failed",
            ad.err_from_http(exc, code=CODE_SEC_FETCH),
        )
    return ad.envelope_error(
        "SEC request failed",
        ad.err_one(CODE_SEC_FETCH, str(exc), detail=str(exc)),
    )


def to_json_dict(env: ToolResponseEnvelope) -> dict[str, Any]:
    return env.model_dump(mode="json")


def _phase1_artifact_dict(ap: dict[str, Path]) -> dict[str, str]:
    return {
        ARTIFACT_KEY_PANEL: str(ap["panel"]),
        ARTIFACT_KEY_FEATURES: str(ap["features"]),
        ARTIFACT_KEY_ANOMALIES: str(ap["anomalies"]),
        ARTIFACT_KEY_REPORT: str(ap["report"]),
    }


def _provenance_tickers(tickers: list[str]) -> dict[str, Any]:
    pairs = ad.ticker_cik_pairs(tickers)
    ciks = sorted({int(p["cik"]) for p in pairs})
    return {
        "input_tickers": list(tickers),
        "resolved_ciks": pairs,
        "ciks": ciks,
    }


def resolve_company_tool(inp: ResolveCompanyInput) -> ToolResponseEnvelope:
    try:
        r = ad.resolve_company_dict(inp.ticker)
        return ad.envelope_success(
            message="Ticker resolved.",
            data={
                "ticker": r["ticker"],
                "cik": r["cik"],
                "company_name": r.get("company_name"),
                "provenance": ad.provenance_from_resolve(r),
            },
            artifacts={},
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except Exception as e:
        return ad.envelope_error(
            "resolve_company failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="resolve_company failed"),
        )


def fetch_company_data_tool(inp: FetchCompanyDataInput) -> ToolResponseEnvelope:
    try:
        d = ad.fetch_company_data_dict(inp.ticker, refresh=inp.refresh)
        paths = ad.cache_paths_from_fetch_result(d)
        sub_p = Path(paths[ARTIFACT_KEY_CACHE_SUBMISSIONS])
        fac_p = Path(paths[ARTIFACT_KEY_CACHE_COMPANYFACTS])
        return ad.envelope_success(
            message="SEC JSON cached or loaded.",
            data={
                "ticker": d["ticker"],
                "cik": int(d["cik"]),
                "refresh": inp.refresh,
                "provenance": ad.provenance_from_resolve(d),
                "artifacts_detail": {
                    ARTIFACT_KEY_CACHE_SUBMISSIONS: ad.artifact_info(sub_p),
                    ARTIFACT_KEY_CACHE_COMPANYFACTS: ad.artifact_info(fac_p),
                },
            },
            artifacts=dict(paths),
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except requests.RequestException as e:
        return _envelope_sec_request_failed(e)
    except Exception as e:
        return ad.envelope_error(
            "fetch_company_data failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="fetch_company_data failed"),
        )


def build_panel_tool(inp: BuildPanelInput) -> ToolResponseEnvelope:
    tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
    if not tickers:
        return ad.envelope_error(
            "No tickers after normalization",
            ad.err_one(CODE_EMPTY_INPUT, "tickers list is empty after normalization"),
        )
    try:
        panel = ad.build_panel_dataframe(tickers, refresh=inp.refresh)
        prov = _provenance_tickers(tickers)
        if panel.empty:
            return ad.envelope_no_data(
                "No extractable quarterly metrics for these tickers/periods (empty panel).",
                data={
                    "row_count": 0,
                    "columns": [],
                    **prov,
                },
                artifacts={},
            )
        path = ad.write_panel_csv(panel)
        cols = [str(c) for c in panel.columns]
        return ad.envelope_success(
            message="Panel written.",
            data={
                "row_count": len(panel),
                "columns": cols,
                **prov,
                "primary_artifact": ad.artifact_info(path, row_count=len(panel), columns=cols),
            },
            artifacts={ARTIFACT_KEY_PANEL: str(path)},
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except requests.RequestException as e:
        return _envelope_sec_request_failed(e)
    except Exception as e:
        return ad.envelope_error(
            "build_panel failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="build_panel failed"),
        )


def compute_features_tool(inp: ComputeFeaturesInput) -> ToolResponseEnvelope:
    try:
        if inp.panel_csv_path:
            panel = ad.read_panel_csv(Path(inp.panel_csv_path).expanduser().resolve())
            pcsv = Path(inp.panel_csv_path).resolve()
            src = {
                "source": "panel_csv",
                "panel_csv_path": str(pcsv),
                "input_tickers": [],
                "ciks": ad.sorted_unique_ciks(panel),
            }
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = ad.build_panel_dataframe(tickers, refresh=False)
            src = {
                "source": "tickers",
                **(_provenance_tickers(tickers)),
            }
        if panel.empty:
            return ad.envelope_no_data(
                "Panel is empty; cannot compute features.",
                data={**src, "row_count": 0, "columns": []},
                artifacts={},
            )
        feats = ad.compute_features_dataframe(panel)
        path = ad.write_features_csv(feats)
        cols = [str(c) for c in feats.columns]
        extra: dict[str, Any] = {}
        if inp.panel_csv_path:
            extra["panel_csv"] = ad.artifact_info(
                pcsv, row_count=len(panel), columns=[str(c) for c in panel.columns]
            )
        return ad.envelope_success(
            message="Features written.",
            data={
                **src,
                "row_count": len(feats),
                "columns": cols,
                "primary_artifact": ad.artifact_info(path, row_count=len(feats), columns=cols),
                **extra,
            },
            artifacts={ARTIFACT_KEY_FEATURES: str(path)},
        )
    except FileNotFoundError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_FILE_NOT_FOUND, str(e), detail=str(e)),
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except requests.RequestException as e:
        return _envelope_sec_request_failed(e)
    except Exception as e:
        return ad.envelope_error(
            "compute_features failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="compute_features failed"),
        )


def detect_anomalies_tool(inp: DetectAnomaliesInput) -> ToolResponseEnvelope:
    try:
        an_meta = ad.anomaly_detection_params()
        if inp.features_csv_path:
            feats = ad.read_features_csv(Path(inp.features_csv_path).expanduser().resolve())
            fcsv = Path(inp.features_csv_path).resolve()
            src = {
                "source": "features_csv",
                "features_csv_path": str(fcsv),
                "input_tickers": [],
                "ciks": ad.sorted_unique_ciks(feats),
            }
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = ad.build_panel_dataframe(tickers, refresh=False)
            if panel.empty:
                return ad.envelope_no_data(
                    "Panel empty after extraction; no features to score.",
                    data={
                        **_provenance_tickers(tickers),
                        "row_count": 0,
                        "anomaly_count": 0,
                        **an_meta,
                    },
                    artifacts={},
                )
            feats = ad.compute_features_dataframe(panel)
            src = {"source": "tickers", **_provenance_tickers(tickers)}
        anom = ad.detect_anomalies_dataframe(feats)
        path = ad.write_anomalies_csv(anom)
        fcols = [str(c) for c in feats.columns]
        acols = [str(c) for c in anom.columns]
        extra: dict[str, Any] = {
            **an_meta,
            "feature_row_count": len(feats),
            "anomaly_count": len(anom),
            "primary_artifact": ad.artifact_info(path, row_count=len(anom), columns=acols),
        }
        if inp.features_csv_path:
            extra["features_csv"] = ad.artifact_info(
                fcsv, row_count=len(feats), columns=fcols
            )
        return ad.envelope_success(
            message="Anomalies written.",
            data={**src, **extra},
            artifacts={ARTIFACT_KEY_ANOMALIES: str(path)},
        )
    except FileNotFoundError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_FILE_NOT_FOUND, str(e), detail=str(e)),
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except requests.RequestException as e:
        return _envelope_sec_request_failed(e)
    except Exception as e:
        return ad.envelope_error(
            "detect_anomalies failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="detect_anomalies failed"),
        )


def generate_report_tool(inp: GenerateReportInput) -> ToolResponseEnvelope:
    try:
        if inp.use_default_artifact_paths:
            ap = ad.phase1_paths()
            feats = ad.read_features_csv(ap["features"])
            anom = ad.read_anomalies_csv(ap["anomalies"])
            art = _phase1_artifact_dict(ap)
        else:
            assert inp.features_csv_path and inp.anomalies_csv_path
            fp = Path(inp.features_csv_path).expanduser().resolve()
            apath = Path(inp.anomalies_csv_path).expanduser().resolve()
            feats = ad.read_features_csv(fp)
            anom = ad.read_anomalies_csv(apath)
            art = {
                ARTIFACT_KEY_FEATURES: str(fp),
                ARTIFACT_KEY_ANOMALIES: str(apath),
            }
        if feats.empty:
            return ad.envelope_no_data(
                "Features input is empty; nothing to summarize.",
                data={
                    "feature_row_count": 0,
                    "sources": {k: ad.artifact_info(v) for k, v in art.items()},
                },
                artifacts=art,
            )
        md = ad.generate_report_markdown(anom, feats)
        path = ad.write_report_md(md)
        src_paths = {
            ARTIFACT_KEY_FEATURES: str(art[ARTIFACT_KEY_FEATURES]),
            ARTIFACT_KEY_ANOMALIES: str(art[ARTIFACT_KEY_ANOMALIES]),
        }
        sources_detail = {
            ARTIFACT_KEY_FEATURES: ad.artifact_info(
                src_paths[ARTIFACT_KEY_FEATURES],
                row_count=len(feats),
                columns=[str(c) for c in feats.columns],
            ),
            ARTIFACT_KEY_ANOMALIES: ad.artifact_info(
                src_paths[ARTIFACT_KEY_ANOMALIES],
                row_count=len(anom),
                columns=[str(c) for c in anom.columns],
            ),
        }
        return ad.envelope_success(
            message="Report written.",
            data={
                "feature_row_count": len(feats),
                "anomaly_row_count": len(anom),
                "report_chars": len(md),
                "ciks": ad.sorted_unique_ciks(feats),
                "report": ad.artifact_info(path),
                "sources": src_paths,
                "sources_detail": sources_detail,
            },
            artifacts={**art, ARTIFACT_KEY_REPORT: str(path)},
        )
    except FileNotFoundError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_FILE_NOT_FOUND, str(e), detail=str(e)),
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_VALIDATION, str(e), detail=str(e)),
        )
    except Exception as e:
        return ad.envelope_error(
            "generate_report failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="generate_report failed"),
        )


def run_pipeline_tool(inp: RunPipelineInput) -> ToolResponseEnvelope:
    tickers = [t.strip().upper() for t in (inp.tickers or []) if t.strip()]
    if not tickers:
        import config

        tickers = list(config.DEFAULT_TICKERS[:5])
    try:
        panel, feats, anom, md, dq_df, ex_df = ad.run_full_pipeline(tickers, refresh=inp.refresh)
        prov = _provenance_tickers(tickers)
        an_meta = ad.anomaly_detection_params()
        if panel.empty:
            return ad.envelope_no_data(
                "Pipeline produced an empty panel (no rows after extraction/normalization).",
                data={
                    **prov,
                    "refresh": inp.refresh,
                    "panel_rows": 0,
                    "feature_rows": int(len(feats)),
                    "anomaly_rows": int(len(anom)),
                    **an_meta,
                },
                artifacts={},
            )
        paths = ad.write_all_phase1_artifacts(
            panel, feats, anom, md, data_quality=dq_df, exclusions=ex_df
        )
        pcols = [str(c) for c in panel.columns]
        fcols = [str(c) for c in feats.columns]
        acols = [str(c) for c in anom.columns]
        dq_path = paths.get("data_quality")
        ex_path = paths.get("exclusions")
        artifacts_detail = {
            ARTIFACT_KEY_PANEL: ad.artifact_info(
                paths["panel"], row_count=len(panel), columns=pcols
            ),
            ARTIFACT_KEY_FEATURES: ad.artifact_info(
                paths["features"], row_count=len(feats), columns=fcols
            ),
            ARTIFACT_KEY_ANOMALIES: ad.artifact_info(
                paths["anomalies"], row_count=len(anom), columns=acols
            ),
            ARTIFACT_KEY_REPORT: ad.artifact_info(paths["report"]),
        }
        if dq_path is not None:
            dcols = [str(c) for c in dq_df.columns]
            artifacts_detail[ARTIFACT_KEY_DATA_QUALITY] = ad.artifact_info(
                dq_path, row_count=len(dq_df), columns=dcols
            )
        if ex_path is not None:
            xcols = [str(c) for c in ex_df.columns]
            artifacts_detail[ARTIFACT_KEY_EXCLUSIONS] = ad.artifact_info(
                ex_path, row_count=len(ex_df), columns=xcols
            )
        return ad.envelope_success(
            message="Full pipeline completed; artifacts written.",
            data={
                **prov,
                "refresh": inp.refresh,
                "panel_rows": len(panel),
                "feature_rows": len(feats),
                "anomaly_rows": len(anom),
                "report_chars": len(md),
                "data_quality_summary_path": str(dq_path) if dq_path is not None else None,
                "exclusions_summary_path": str(ex_path) if ex_path is not None else None,
                **an_meta,
                "artifacts_detail": artifacts_detail,
            },
            artifacts={
                ARTIFACT_KEY_PANEL: str(paths["panel"]),
                ARTIFACT_KEY_FEATURES: str(paths["features"]),
                ARTIFACT_KEY_ANOMALIES: str(paths["anomalies"]),
                ARTIFACT_KEY_REPORT: str(paths["report"]),
                **(
                    {ARTIFACT_KEY_DATA_QUALITY: str(dq_path)}
                    if dq_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_EXCLUSIONS: str(ex_path)}
                    if ex_path is not None
                    else {}
                ),
            },
        )
    except ValueError as e:
        return ad.envelope_error(
            str(e),
            ad.err_one(CODE_UNKNOWN_TICKER, str(e), detail=str(e)),
        )
    except requests.RequestException as e:
        return _envelope_sec_request_failed(e)
    except Exception as e:
        return ad.envelope_error(
            "run_pipeline failed",
            ad.err_from_exception(e, code=CODE_INTERNAL, message="run_pipeline failed"),
        )
