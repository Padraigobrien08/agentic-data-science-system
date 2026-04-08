"""
MCP tool implementations — return :class:`ToolResponseEnvelope` only.

All exceptions are converted to ``status=error`` with structured ``errors[]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
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
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_TREND_BREAKS,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
    ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_MANUAL_VALIDATION,
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


def _trustworthiness_artifact_path_map(**role_to_path: object) -> dict[str, str]:
    """Stable role key → filesystem path; omit missing or empty (downstream convenience map)."""
    out: dict[str, str] = {}
    for role, p in role_to_path.items():
        if p is None:
            continue
        s = str(p).strip()
        if s:
            out[role] = s
    return out


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
        import config

        peer_sig: pd.DataFrame | None = None
        dq_df: pd.DataFrame | None = None
        excl_df: pd.DataFrame | None = None
        phase1_ap: dict[str, Path] | None = None
        if inp.use_default_artifact_paths:
            phase1_ap = ad.phase1_paths()
            feats = ad.read_features_csv(phase1_ap["features"])
            anom = ad.read_anomalies_csv(phase1_ap["anomalies"])
            art = _phase1_artifact_dict(phase1_ap)
            psp = phase1_ap.get("peer_signals")
            if psp is not None and psp.is_file():
                peer_sig = ad.read_peer_signals_csv(psp)
                art = {**art, ARTIFACT_KEY_PEER_SIGNALS: str(psp)}
            dq_p = phase1_ap.get("data_quality")
            if dq_p is not None and dq_p.is_file():
                dq_df = pd.read_csv(dq_p)
            ex_p = phase1_ap.get("exclusions")
            if ex_p is not None and ex_p.is_file():
                excl_df = pd.read_csv(ex_p)
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
        mv_path = config.PROJECT_ROOT / "validation" / "manual_validation.csv"
        md = ad.generate_report_markdown(
            anom,
            feats,
            peer_signals=peer_sig,
            data_quality=dq_df,
            exclusions=excl_df,
            manual_validation_path=mv_path,
        )
        path = ad.write_report_md(md)
        src_paths = {
            ARTIFACT_KEY_FEATURES: str(art[ARTIFACT_KEY_FEATURES]),
            ARTIFACT_KEY_ANOMALIES: str(art[ARTIFACT_KEY_ANOMALIES]),
        }
        sources_detail: dict[str, Any] = {
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
        dq_path_data: str | None = None
        ex_path_data: str | None = None
        peer_path_data: str | None = None
        mc_sum_p = mc_co_p = mc_pe_p = None
        cave_ext_path_data = cave_pan_path_data = None
        trend_breaks_path_data: str | None = None
        unified_findings_path_data: str | None = None
        fs_company_path_data: str | None = None
        fs_metric_path_data: str | None = None
        fs_period_path_data: str | None = None
        cov_sum_for_tw = cov_co_for_tw = cov_pe_for_tw = None
        cave_ext_for_tw = cave_pan_for_tw = None
        extraction_caveat_rows_for_summary: int | None = None
        panel_caveat_rows_for_summary: int | None = None
        if phase1_ap is not None:
            dq_p = phase1_ap.get("data_quality")
            if dq_p is not None and dq_p.is_file() and dq_df is not None:
                src_paths[ARTIFACT_KEY_DATA_QUALITY] = str(dq_p)
                dq_path_data = str(dq_p)
                sources_detail[ARTIFACT_KEY_DATA_QUALITY] = ad.artifact_info(
                    dq_p, row_count=len(dq_df), columns=[str(c) for c in dq_df.columns]
                )
            ex_p = phase1_ap.get("exclusions")
            if ex_p is not None and ex_p.is_file() and excl_df is not None:
                src_paths[ARTIFACT_KEY_EXCLUSIONS] = str(ex_p)
                ex_path_data = str(ex_p)
                sources_detail[ARTIFACT_KEY_EXCLUSIONS] = ad.artifact_info(
                    ex_p, row_count=len(excl_df), columns=[str(c) for c in excl_df.columns]
                )
            psp = phase1_ap.get("peer_signals")
            if psp is not None and psp.is_file() and peer_sig is not None:
                src_paths[ARTIFACT_KEY_PEER_SIGNALS] = str(psp)
                peer_path_data = str(psp)
                sources_detail[ARTIFACT_KEY_PEER_SIGNALS] = ad.artifact_info(
                    psp, row_count=len(peer_sig), columns=[str(c) for c in peer_sig.columns]
                )
            cov_sum_for_tw = phase1_ap.get("metric_coverage_summary")
            cov_co_for_tw = phase1_ap.get("metric_coverage_by_company")
            cov_pe_for_tw = phase1_ap.get("metric_coverage_by_period")
            cave_ext_for_tw = phase1_ap.get("metric_caveats_extraction")
            cave_pan_for_tw = phase1_ap.get("metric_caveats_panel")
            tb_p = phase1_ap.get("trend_breaks")
            if tb_p is not None and tb_p.is_file():
                try:
                    tb_df = pd.read_csv(tb_p)
                    trend_breaks_path_data = str(tb_p)
                    src_paths[ARTIFACT_KEY_TREND_BREAKS] = trend_breaks_path_data
                    sources_detail[ARTIFACT_KEY_TREND_BREAKS] = ad.artifact_info(
                        tb_p, row_count=len(tb_df), columns=[str(c) for c in tb_df.columns]
                    )
                except Exception:
                    trend_breaks_path_data = str(tb_p)
                    src_paths[ARTIFACT_KEY_TREND_BREAKS] = trend_breaks_path_data
                    sources_detail[ARTIFACT_KEY_TREND_BREAKS] = ad.artifact_info(tb_p)
            uf_p = phase1_ap.get("unified_findings")
            if uf_p is not None and uf_p.is_file():
                try:
                    uf_df = pd.read_csv(uf_p)
                    unified_findings_path_data = str(uf_p)
                    src_paths[ARTIFACT_KEY_UNIFIED_FINDINGS] = unified_findings_path_data
                    sources_detail[ARTIFACT_KEY_UNIFIED_FINDINGS] = ad.artifact_info(
                        uf_p, row_count=len(uf_df), columns=[str(c) for c in uf_df.columns]
                    )
                except Exception:
                    unified_findings_path_data = str(uf_p)
                    src_paths[ARTIFACT_KEY_UNIFIED_FINDINGS] = unified_findings_path_data
                    sources_detail[ARTIFACT_KEY_UNIFIED_FINDINGS] = ad.artifact_info(uf_p)
            fsc_p = phase1_ap.get("findings_summary_by_company")
            if fsc_p is not None and fsc_p.is_file():
                try:
                    fsc_df = pd.read_csv(fsc_p)
                    fs_company_path_data = str(fsc_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = fs_company_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = ad.artifact_info(
                        fsc_p, row_count=len(fsc_df), columns=[str(c) for c in fsc_df.columns]
                    )
                except Exception:
                    fs_company_path_data = str(fsc_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = fs_company_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = ad.artifact_info(fsc_p)
            fsm_p = phase1_ap.get("findings_summary_by_metric")
            if fsm_p is not None and fsm_p.is_file():
                try:
                    fsm_df = pd.read_csv(fsm_p)
                    fs_metric_path_data = str(fsm_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = fs_metric_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = ad.artifact_info(
                        fsm_p, row_count=len(fsm_df), columns=[str(c) for c in fsm_df.columns]
                    )
                except Exception:
                    fs_metric_path_data = str(fsm_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = fs_metric_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = ad.artifact_info(fsm_p)
            fsp_p = phase1_ap.get("findings_summary_by_period")
            if fsp_p is not None and fsp_p.is_file():
                try:
                    fsp_df = pd.read_csv(fsp_p)
                    fs_period_path_data = str(fsp_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = fs_period_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = ad.artifact_info(
                        fsp_p, row_count=len(fsp_df), columns=[str(c) for c in fsp_df.columns]
                    )
                except Exception:
                    fs_period_path_data = str(fsp_p)
                    src_paths[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = fs_period_path_data
                    sources_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = ad.artifact_info(fsp_p)
            cs_p = cov_sum_for_tw
            if cs_p is not None and cs_p.is_file():
                try:
                    cs_df = pd.read_csv(cs_p)
                    mc_sum_p = str(cs_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = mc_sum_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = ad.artifact_info(
                        cs_p, row_count=len(cs_df), columns=[str(c) for c in cs_df.columns]
                    )
                except Exception:
                    mc_sum_p = str(cs_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = mc_sum_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = ad.artifact_info(cs_p)
            cc_p = cov_co_for_tw
            if cc_p is not None and cc_p.is_file():
                try:
                    cc_df = pd.read_csv(cc_p)
                    mc_co_p = str(cc_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = mc_co_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = ad.artifact_info(
                        cc_p, row_count=len(cc_df), columns=[str(c) for c in cc_df.columns]
                    )
                except Exception:
                    mc_co_p = str(cc_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = mc_co_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = ad.artifact_info(cc_p)
            cpe_p = cov_pe_for_tw
            if cpe_p is not None and cpe_p.is_file():
                try:
                    cpe_df = pd.read_csv(cpe_p)
                    mc_pe_p = str(cpe_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = mc_pe_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = ad.artifact_info(
                        cpe_p, row_count=len(cpe_df), columns=[str(c) for c in cpe_df.columns]
                    )
                except Exception:
                    mc_pe_p = str(cpe_p)
                    src_paths[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = mc_pe_p
                    sources_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = ad.artifact_info(cpe_p)
            ce_p = cave_ext_for_tw
            if ce_p is not None and ce_p.is_file():
                try:
                    ced = pd.read_csv(ce_p)
                    extraction_caveat_rows_for_summary = len(ced)
                    cave_ext_path_data = str(ce_p)
                    src_paths[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = cave_ext_path_data
                    sources_detail[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = ad.artifact_info(
                        ce_p, row_count=len(ced), columns=[str(c) for c in ced.columns]
                    )
                except Exception:
                    extraction_caveat_rows_for_summary = None
                    cave_ext_path_data = str(ce_p)
                    src_paths[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = cave_ext_path_data
                    sources_detail[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = ad.artifact_info(ce_p)
            cp_p = cave_pan_for_tw
            if cp_p is not None and cp_p.is_file():
                try:
                    cpd = pd.read_csv(cp_p)
                    panel_caveat_rows_for_summary = len(cpd)
                    cave_pan_path_data = str(cp_p)
                    src_paths[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = cave_pan_path_data
                    sources_detail[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = ad.artifact_info(
                        cp_p, row_count=len(cpd), columns=[str(c) for c in cpd.columns]
                    )
                except Exception:
                    panel_caveat_rows_for_summary = None
                    cave_pan_path_data = str(cp_p)
                    src_paths[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = cave_pan_path_data
                    sources_detail[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = ad.artifact_info(cp_p)
        art_out = {**art, ARTIFACT_KEY_REPORT: str(path)}
        if mv_path.is_file():
            art_out[ARTIFACT_KEY_MANUAL_VALIDATION] = str(mv_path.resolve())
            try:
                mv_df = pd.read_csv(mv_path)
                sources_detail[ARTIFACT_KEY_MANUAL_VALIDATION] = ad.artifact_info(
                    mv_path.resolve(), row_count=len(mv_df), columns=[str(c) for c in mv_df.columns]
                )
            except Exception:
                sources_detail[ARTIFACT_KEY_MANUAL_VALIDATION] = ad.artifact_info(mv_path.resolve())

        manual_str = str(mv_path.resolve()) if mv_path.is_file() else None
        if mc_sum_p:
            art_out[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = mc_sum_p
        if mc_co_p:
            art_out[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = mc_co_p
        if mc_pe_p:
            art_out[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = mc_pe_p
        if cave_ext_path_data:
            art_out[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = cave_ext_path_data
        if cave_pan_path_data:
            art_out[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = cave_pan_path_data
        if trend_breaks_path_data:
            art_out[ARTIFACT_KEY_TREND_BREAKS] = trend_breaks_path_data
        if unified_findings_path_data:
            art_out[ARTIFACT_KEY_UNIFIED_FINDINGS] = unified_findings_path_data
        if fs_company_path_data:
            art_out[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = fs_company_path_data
        if fs_metric_path_data:
            art_out[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = fs_metric_path_data
        if fs_period_path_data:
            art_out[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = fs_period_path_data

        tw_summary: dict[str, int | None] = {}
        if cave_ext_for_tw is not None and cave_ext_for_tw.is_file():
            tw_summary["extraction_caveat_rows"] = extraction_caveat_rows_for_summary
        if cave_pan_for_tw is not None and cave_pan_for_tw.is_file():
            tw_summary["panel_caveat_rows"] = panel_caveat_rows_for_summary

        tw_paths = _trustworthiness_artifact_path_map(
            **{
                ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY: cov_sum_for_tw,
                ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY: cov_co_for_tw,
                ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD: cov_pe_for_tw,
                ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION: cave_ext_for_tw,
                ARTIFACT_KEY_METRIC_CAVEATS_PANEL: cave_pan_for_tw,
                ARTIFACT_KEY_MANUAL_VALIDATION: manual_str,
            }
        )

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
                "data_quality_summary_path": dq_path_data,
                "exclusions_summary_path": ex_path_data,
                "peer_signals_path": peer_path_data,
                "metric_coverage_summary_path": mc_sum_p,
                "metric_coverage_by_company_path": mc_co_p,
                "metric_coverage_by_period_path": mc_pe_p,
                "metric_caveats_extraction_path": cave_ext_path_data,
                "metric_caveats_panel_path": cave_pan_path_data,
                "trend_break_signals_path": trend_breaks_path_data,
                "unified_findings_path": unified_findings_path_data,
                "findings_summary_by_company_path": fs_company_path_data,
                "findings_summary_by_metric_path": fs_metric_path_data,
                "findings_summary_by_period_path": fs_period_path_data,
                "manual_validation_path": manual_str,
                "trustworthiness_artifact_paths": tw_paths,
                "trustworthiness_summary": tw_summary,
            },
            artifacts=art_out,
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
        panel, feats, anom, md, dq_df, ex_df, peer_df, cave_long = ad.run_full_pipeline(
            tickers, refresh=inp.refresh
        )
        prov = _provenance_tickers(tickers)
        an_meta = ad.anomaly_detection_params()
        peer_meta = ad.peer_signal_params()
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
                    **peer_meta,
                },
                artifacts={},
            )
        paths = ad.write_all_phase1_artifacts(
            panel,
            feats,
            anom,
            md,
            data_quality=dq_df,
            exclusions=ex_df,
            peer_signals=peer_df,
            extraction_caveats_long=cave_long,
        )
        pcols = [str(c) for c in panel.columns]
        fcols = [str(c) for c in feats.columns]
        acols = [str(c) for c in anom.columns]
        dq_path = paths.get("data_quality")
        ex_path = paths.get("exclusions")
        peer_path = paths.get("peer_signals")
        cov_sum_path = paths.get("metric_coverage_summary")
        cov_co_path = paths.get("metric_coverage_by_company")
        cov_pe_path = paths.get("metric_coverage_by_period")
        cave_ext_path = paths.get("metric_caveats_extraction")
        cave_pan_path = paths.get("metric_caveats_panel")
        trend_breaks_path = paths.get("trend_breaks")
        unified_findings_path = paths.get("unified_findings")
        fs_company_path = paths.get("findings_summary_by_company")
        fs_metric_path = paths.get("findings_summary_by_metric")
        fs_period_path = paths.get("findings_summary_by_period")
        extraction_caveat_rows_for_summary: int | None = None
        panel_caveat_rows_for_summary: int | None = None
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
        if peer_path is not None:
            pscols = [str(c) for c in peer_df.columns]
            artifacts_detail[ARTIFACT_KEY_PEER_SIGNALS] = ad.artifact_info(
                peer_path, row_count=len(peer_df), columns=pscols
            )
        if trend_breaks_path is not None and trend_breaks_path.is_file():
            try:
                tbd = pd.read_csv(trend_breaks_path)
                artifacts_detail[ARTIFACT_KEY_TREND_BREAKS] = ad.artifact_info(
                    trend_breaks_path, row_count=len(tbd), columns=[str(c) for c in tbd.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_TREND_BREAKS] = ad.artifact_info(trend_breaks_path)
        if unified_findings_path is not None and unified_findings_path.is_file():
            try:
                ufd = pd.read_csv(unified_findings_path)
                artifacts_detail[ARTIFACT_KEY_UNIFIED_FINDINGS] = ad.artifact_info(
                    unified_findings_path, row_count=len(ufd), columns=[str(c) for c in ufd.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_UNIFIED_FINDINGS] = ad.artifact_info(unified_findings_path)
        if fs_company_path is not None and fs_company_path.is_file():
            try:
                fcd = pd.read_csv(fs_company_path)
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = ad.artifact_info(
                    fs_company_path, row_count=len(fcd), columns=[str(c) for c in fcd.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY] = ad.artifact_info(fs_company_path)
        if fs_metric_path is not None and fs_metric_path.is_file():
            try:
                fmd = pd.read_csv(fs_metric_path)
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = ad.artifact_info(
                    fs_metric_path, row_count=len(fmd), columns=[str(c) for c in fmd.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC] = ad.artifact_info(fs_metric_path)
        if fs_period_path is not None and fs_period_path.is_file():
            try:
                fpd = pd.read_csv(fs_period_path)
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = ad.artifact_info(
                    fs_period_path, row_count=len(fpd), columns=[str(c) for c in fpd.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD] = ad.artifact_info(fs_period_path)
        if cov_sum_path is not None and cov_sum_path.is_file():
            try:
                cov_sum_df = pd.read_csv(cov_sum_path)
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = ad.artifact_info(
                    cov_sum_path,
                    row_count=len(cov_sum_df),
                    columns=[str(c) for c in cov_sum_df.columns],
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY] = ad.artifact_info(cov_sum_path)
        if cov_co_path is not None and cov_co_path.is_file():
            try:
                cov_co_df = pd.read_csv(cov_co_path)
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = ad.artifact_info(
                    cov_co_path,
                    row_count=len(cov_co_df),
                    columns=[str(c) for c in cov_co_df.columns],
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY] = ad.artifact_info(cov_co_path)
        if cov_pe_path is not None and cov_pe_path.is_file():
            try:
                cov_pe_df = pd.read_csv(cov_pe_path)
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = ad.artifact_info(
                    cov_pe_path,
                    row_count=len(cov_pe_df),
                    columns=[str(c) for c in cov_pe_df.columns],
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD] = ad.artifact_info(cov_pe_path)
        if cave_ext_path is not None and cave_ext_path.is_file():
            try:
                ced = pd.read_csv(cave_ext_path)
                extraction_caveat_rows_for_summary = len(ced)
                artifacts_detail[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = ad.artifact_info(
                    cave_ext_path,
                    row_count=len(ced),
                    columns=[str(c) for c in ced.columns],
                )
            except Exception:
                extraction_caveat_rows_for_summary = None
                artifacts_detail[ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION] = ad.artifact_info(cave_ext_path)
        if cave_pan_path is not None and cave_pan_path.is_file():
            try:
                cpd = pd.read_csv(cave_pan_path)
                panel_caveat_rows_for_summary = len(cpd)
                artifacts_detail[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = ad.artifact_info(
                    cave_pan_path,
                    row_count=len(cpd),
                    columns=[str(c) for c in cpd.columns],
                )
            except Exception:
                panel_caveat_rows_for_summary = None
                artifacts_detail[ARTIFACT_KEY_METRIC_CAVEATS_PANEL] = ad.artifact_info(cave_pan_path)
        import config

        mv_path = (config.PROJECT_ROOT / "validation" / "manual_validation.csv").resolve()
        mv_in_artifacts: dict[str, str] = {}
        manual_path_data: str | None = None
        if mv_path.is_file():
            manual_path_data = str(mv_path)
            mv_in_artifacts[ARTIFACT_KEY_MANUAL_VALIDATION] = manual_path_data
            try:
                mv_df = pd.read_csv(mv_path)
                artifacts_detail[ARTIFACT_KEY_MANUAL_VALIDATION] = ad.artifact_info(
                    mv_path, row_count=len(mv_df), columns=[str(c) for c in mv_df.columns]
                )
            except Exception:
                artifacts_detail[ARTIFACT_KEY_MANUAL_VALIDATION] = ad.artifact_info(mv_path)

        tw_paths = _trustworthiness_artifact_path_map(
            **{
                ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY: cov_sum_path,
                ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY: cov_co_path,
                ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD: cov_pe_path,
                ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION: cave_ext_path,
                ARTIFACT_KEY_METRIC_CAVEATS_PANEL: cave_pan_path,
                ARTIFACT_KEY_MANUAL_VALIDATION: manual_path_data,
            }
        )
        tw_summary: dict[str, int | None] = {}
        if cave_ext_path is not None and cave_ext_path.is_file():
            tw_summary["extraction_caveat_rows"] = extraction_caveat_rows_for_summary
        if cave_pan_path is not None and cave_pan_path.is_file():
            tw_summary["panel_caveat_rows"] = panel_caveat_rows_for_summary

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
                "peer_signals_path": str(peer_path) if peer_path is not None else None,
                "trend_break_signals_path": str(trend_breaks_path) if trend_breaks_path is not None else None,
                "unified_findings_path": str(unified_findings_path) if unified_findings_path is not None else None,
                "findings_summary_by_company_path": str(fs_company_path) if fs_company_path is not None else None,
                "findings_summary_by_metric_path": str(fs_metric_path) if fs_metric_path is not None else None,
                "findings_summary_by_period_path": str(fs_period_path) if fs_period_path is not None else None,
                "metric_coverage_summary_path": str(cov_sum_path) if cov_sum_path is not None else None,
                "metric_coverage_by_company_path": str(cov_co_path) if cov_co_path is not None else None,
                "metric_coverage_by_period_path": str(cov_pe_path) if cov_pe_path is not None else None,
                "metric_caveats_extraction_path": str(cave_ext_path) if cave_ext_path is not None else None,
                "metric_caveats_panel_path": str(cave_pan_path) if cave_pan_path is not None else None,
                "manual_validation_path": manual_path_data,
                "trustworthiness_artifact_paths": tw_paths,
                "trustworthiness_summary": tw_summary,
                **an_meta,
                **peer_meta,
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
                **(
                    {ARTIFACT_KEY_PEER_SIGNALS: str(peer_path)}
                    if peer_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_TREND_BREAKS: str(trend_breaks_path)}
                    if trend_breaks_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_UNIFIED_FINDINGS: str(unified_findings_path)}
                    if unified_findings_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY: str(fs_company_path)}
                    if fs_company_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC: str(fs_metric_path)}
                    if fs_metric_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD: str(fs_period_path)}
                    if fs_period_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY: str(cov_sum_path)}
                    if cov_sum_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY: str(cov_co_path)}
                    if cov_co_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD: str(cov_pe_path)}
                    if cov_pe_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION: str(cave_ext_path)}
                    if cave_ext_path is not None
                    else {}
                ),
                **(
                    {ARTIFACT_KEY_METRIC_CAVEATS_PANEL: str(cave_pan_path)}
                    if cave_pan_path is not None
                    else {}
                ),
                **mv_in_artifacts,
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
