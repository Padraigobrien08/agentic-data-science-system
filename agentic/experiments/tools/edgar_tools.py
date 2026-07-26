"""
EDGAR domain experiment tools.

These wrap the existing deterministic EDGAR computations (``src.peer_signals``,
``src.trend_breaks``, ``src.anomaly`` via ``edgar_project.mcp.adapters``) as typed
experiment tools. They do **not** reimplement the numerics — they call the
established functions and translate their outputs into structured observations,
evidence, and artifacts.

Input is an EDGAR *features* frame (``cik``, ``period`` + metric columns). Build
the manifest with :class:`~agentic.adapters.EDGARAdapter` so ``period`` is typed
as the time index and the metrics carry their EDGAR semantics.

``edgar_segment_analysis`` is intentionally **not** implemented: the EDGAR panel
has no segment-level data to analyze (documented in the tool catalog).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel

from agentic.domain.common import DomainModel
from agentic.domain.enums import (
    ColumnRole,
    EvidenceDirection,
    EvidenceType,
    Modality,
    ObservationType,
)
from agentic.domain.experiment import CostEstimate
from agentic.domain.manifest import DatasetManifest

from ..base import BaseExperimentTool, ExperimentOutcome
from ..capability import ExperimentCapability, ValidationIssue
from ..context import ExperimentContext
from ..descriptor import ArtifactType, ExperimentToolDescriptor, OutputField
from ..errors import ParameterError
from ._helpers import make_evidence, make_observation, make_statistics, require_frame, source_ref

_TS = [Modality.time_series, Modality.tabular]
_COST = CostEstimate(compute_seconds=1.0)


def _ensure_edgar_columns(frame: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ParameterError(f"EDGAR features frame missing columns: {missing}", detail=",".join(missing))


def _require_edgar_columns_issues(manifest: DatasetManifest, required: list[str]) -> list[ValidationIssue]:
    present = {c.name for c in manifest.columns}
    return [
        ValidationIssue(code="MISSING_EDGAR_COLUMN", message=f"EDGAR column '{c}' required", field=c)
        for c in required
        if c not in present
    ]


class _EdgarBase(BaseExperimentTool):
    """Shared capability + no-parameter shape for EDGAR wrappers."""

    params_model: type[BaseModel] = DomainModel  # each subclass overrides
    required_columns: list[str] = ["cik", "period"]

    def _required_capability(self) -> ExperimentCapability:
        return ExperimentCapability(
            supported_modalities=_TS, required_roles=[ColumnRole.metric], requires_temporal=True, min_rows=2
        )

    def _check_params_against_manifest(self, params: BaseModel, manifest: DatasetManifest) -> list[ValidationIssue]:
        return _require_edgar_columns_issues(manifest, self.required_columns)


# ---------------------------------------------------------------------------
# edgar_peer_comparison  (wraps src.peer_signals.compute_peer_signals)
# ---------------------------------------------------------------------------


class _PeerParams(DomainModel):
    pass


class EdgarPeerComparisonTool(_EdgarBase):
    params_model = _PeerParams
    required_columns = ["cik", "period"]

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="edgar_peer_comparison",
            version="1.0",
            purpose="Cross-sectional peer comparison via the deterministic EDGAR peer-signals computation.",
            supported_input_modalities=_TS,
            required_capabilities=self._required_capability(),
            parameter_schema=_PeerParams.model_json_schema(),
            output_schema=[OutputField(name="peer_signals", kind="artifact"),
                           OutputField(name="peer_extremes", kind="evidence")],
            cost_estimate=_COST,
            artifact_types=[ArtifactType.table],
            known_limitations=["Requires >= PEER_MIN_FOR_Z distinct firms per period for z-based signals."],
        )

    def _compute(self, context: ExperimentContext, params: BaseModel) -> ExperimentOutcome:
        frame = require_frame(context)
        _ensure_edgar_columns(frame, self.required_columns)
        from edgar_project.mcp import adapters as edgar_adapters

        edgar_adapters.ensure_sys_path()
        from src.peer_signals import compute_peer_signals

        signals = compute_peer_signals(frame)
        prov = context.tool_provenance(self.name, self.version)
        table = context.artifact_sink.emit_table("peer_signals", signals)
        extremes = signals[signals.get("peer_alert", pd.Series(dtype=str)).isin(["extreme_high", "extreme_low"])] \
            if "peer_alert" in signals.columns else signals.iloc[0:0]
        n = int(len(signals))
        frac = (len(extremes) / n) if n else 0.0
        stat = make_statistics(sample_size=n, effect_size=round(frac, 6), effect_size_kind="signal_fraction",
                               coverage=round(frac, 6) if n else 0.0,
                               diagnostics={"extreme_count": float(len(extremes))})
        obs = [make_observation(statement=f"cik {int(r.cik)} {r.metric} is a peer {r.peer_alert} in {r.period}.",
                                provenance=prov, observation_type=ObservationType.outlier,
                                entity_ref=str(int(r.cik)), metric_ref=str(r.metric))
               for r in extremes.head(15).itertuples(index=False)]
        ev = make_evidence(evidence_type=EvidenceType.peer_comparison,
                           claim=f"{len(extremes)} of {n} peer-signal rows are cross-sectional extremes.",
                           direction=EvidenceDirection.supports if len(extremes) else EvidenceDirection.neutral,
                           provenance=prov, statistics=stat, source_reference=source_ref(context.manifest),
                           artifact_ids=[table.id])
        return ExperimentOutcome(observations=obs, evidence=[ev],
                                 metrics={"peer_rows": float(n), "extreme_count": float(len(extremes))},
                                 statistics=[stat], artifacts=[table],
                                 summary=f"Peer comparison: {len(extremes)} extreme signal(s).")


# ---------------------------------------------------------------------------
# edgar_trend_break_analysis  (wraps src.trend_breaks.compute_trend_break_signals)
# ---------------------------------------------------------------------------


class _TrendBreakParams(DomainModel):
    pass


class EdgarTrendBreakAnalysisTool(_EdgarBase):
    params_model = _TrendBreakParams
    required_columns = ["cik", "period"]

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="edgar_trend_break_analysis",
            version="1.0",
            purpose="Windowed trend-break detection via the deterministic EDGAR trend-break computation.",
            supported_input_modalities=_TS,
            required_capabilities=self._required_capability(),
            parameter_schema=_TrendBreakParams.model_json_schema(),
            output_schema=[OutputField(name="trend_break_signals", kind="artifact"),
                           OutputField(name="shifts", kind="evidence")],
            cost_estimate=_COST,
            artifact_types=[ArtifactType.table],
            known_limitations=["Needs enough trailing history per (cik, metric); short series are labeled short_history."],
        )

    def _compute(self, context: ExperimentContext, params: BaseModel) -> ExperimentOutcome:
        frame = require_frame(context)
        _ensure_edgar_columns(frame, self.required_columns)
        from edgar_project.mcp import adapters as edgar_adapters

        edgar_adapters.ensure_sys_path()
        from src.trend_breaks import compute_trend_break_signals

        signals = compute_trend_break_signals(frame)
        prov = context.tool_provenance(self.name, self.version)
        table = context.artifact_sink.emit_table("trend_break_signals", signals)
        if "signal_type" in signals.columns:
            shifts = signals[signals["signal_type"].isin(["strong_shift", "moderate_shift"])]
        else:
            shifts = signals.iloc[0:0]
        n = int(len(signals))
        stat = make_statistics(sample_size=n, effect_size=round(len(shifts) / n, 6) if n else 0.0,
                               effect_size_kind="signal_fraction",
                               diagnostics={"shift_count": float(len(shifts))},
                               coverage=round(len(shifts) / n, 6) if n else 0.0)
        obs = [make_observation(statement=f"cik {int(r.cik)} {r.metric}: {r.signal_type} at {r.period}.",
                                provenance=prov, observation_type=ObservationType.trend,
                                entity_ref=str(int(r.cik)), metric_ref=str(r.metric))
               for r in shifts.head(15).itertuples(index=False)]
        ev = make_evidence(evidence_type=EvidenceType.trend_break,
                           claim=f"{len(shifts)} of {n} trend-break rows are moderate/strong shifts.",
                           direction=EvidenceDirection.supports if len(shifts) else EvidenceDirection.neutral,
                           provenance=prov, statistics=stat, source_reference=source_ref(context.manifest),
                           artifact_ids=[table.id])
        return ExperimentOutcome(observations=obs, evidence=[ev],
                                 metrics={"trend_break_rows": float(n), "shift_count": float(len(shifts))},
                                 statistics=[stat], artifacts=[table],
                                 summary=f"Trend-break analysis: {len(shifts)} shift(s).")


# ---------------------------------------------------------------------------
# edgar anomaly-based metric tools (wrap detect_anomalies_dataframe)
# ---------------------------------------------------------------------------


class _MetricAnomalyParams(DomainModel):
    pass


class _EdgarAnomalyMetricTool(_EdgarBase):
    """Base for EDGAR tools that surface anomalies for one focal metric."""

    metric_name: str = ""
    evidence_type = EvidenceType.anomaly_flag

    def _compute(self, context: ExperimentContext, params: BaseModel) -> ExperimentOutcome:
        frame = require_frame(context)
        _ensure_edgar_columns(frame, ["cik", "period", self.metric_name])
        from edgar_project.mcp import adapters as edgar_adapters

        anomalies = edgar_adapters.detect_anomalies_dataframe(frame)
        prov = context.tool_provenance(self.name, self.version)
        if "metric" in anomalies.columns:
            focal = anomalies[anomalies["metric"] == self.metric_name]
        else:
            focal = anomalies.iloc[0:0]
        table = context.artifact_sink.emit_table(f"{self.metric_name}_anomalies", focal)
        values = pd.to_numeric(frame[self.metric_name], errors="coerce").to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        n = int(finite.size)
        count = int(len(focal))
        max_z = float(np.nanmax(np.abs(pd.to_numeric(focal.get("zscore", pd.Series(dtype=float)), errors="coerce")))) \
            if count and "zscore" in focal.columns else 0.0
        stat = make_statistics(
            sample_size=n, effect_size=round(count / n, 6) if n else 0.0, effect_size_kind="anomaly_fraction",
            coverage=round(n / len(frame), 6) if len(frame) else 0.0,
            diagnostics={"anomaly_count": float(count), "max_abs_z": round(max_z, 6)},
            assumptions=["Wraps the deterministic EDGAR self/peer anomaly detection."],
            warnings=["No anomalies detected."] if count == 0 else [],
        )
        obs = [make_observation(
            statement=f"cik {int(r.cik)} {self.metric_name} anomaly at {r.period} ({r.anomaly_category}).",
            provenance=prov, observation_type=ObservationType.outlier,
            entity_ref=str(int(r.cik)), metric_ref=self.metric_name,
            magnitude=float(getattr(r, "zscore", float("nan"))) if hasattr(r, "zscore") else None)
            for r in focal.head(15).itertuples(index=False)]
        ev = make_evidence(
            evidence_type=self.evidence_type,
            claim=f"{count} {self.metric_name} anomaly row(s) across {n} observations.",
            direction=EvidenceDirection.supports if count else EvidenceDirection.neutral,
            provenance=prov, statistics=stat, source_reference=source_ref(context.manifest, column=self.metric_name),
            artifact_ids=[table.id])
        return ExperimentOutcome(observations=obs, evidence=[ev],
                                 metrics={"anomaly_count": float(count), "observations": float(n)},
                                 statistics=[stat], artifacts=[table],
                                 summary=f"{self.metric_name}: {count} anomaly row(s).")


class EdgarRevenueGrowthAnalysisTool(_EdgarAnomalyMetricTool):
    params_model = _MetricAnomalyParams
    metric_name = "revenue_growth_qoq"
    required_columns = ["cik", "period", "revenue_growth_qoq"]

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="edgar_revenue_growth_analysis",
            version="1.0",
            purpose="Surface anomalous quarter-over-quarter revenue growth via the EDGAR anomaly pipeline.",
            supported_input_modalities=_TS,
            required_capabilities=self._required_capability(),
            parameter_schema=_MetricAnomalyParams.model_json_schema(),
            output_schema=[OutputField(name="revenue_growth_anomalies", kind="artifact"),
                           OutputField(name="anomaly_fraction", kind="statistic")],
            cost_estimate=_COST,
            artifact_types=[ArtifactType.table],
            known_limitations=["Requires the 'revenue_growth_qoq' feature column."],
        )


class EdgarMarginQualityAnalysisTool(_EdgarAnomalyMetricTool):
    params_model = _MetricAnomalyParams
    metric_name = "net_margin"
    required_columns = ["cik", "period", "net_margin"]

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="edgar_margin_quality_analysis",
            version="1.0",
            purpose="Surface anomalous net-margin behavior via the EDGAR self/peer anomaly pipeline.",
            supported_input_modalities=_TS,
            required_capabilities=self._required_capability(),
            parameter_schema=_MetricAnomalyParams.model_json_schema(),
            output_schema=[OutputField(name="net_margin_anomalies", kind="artifact"),
                           OutputField(name="anomaly_fraction", kind="statistic")],
            cost_estimate=_COST,
            artifact_types=[ArtifactType.table],
            known_limitations=["Requires the 'net_margin' feature column; margin 'quality' is proxied by anomaly signals."],
        )


def edgar_tools() -> list[BaseExperimentTool]:
    """First-party EDGAR domain experiment tools (wrappers over existing computations)."""
    return [
        EdgarPeerComparisonTool(),
        EdgarTrendBreakAnalysisTool(),
        EdgarRevenueGrowthAnalysisTool(),
        EdgarMarginQualityAnalysisTool(),
    ]
