"""Shared helpers for experiment tools (column resolution, evidence assembly)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agentic.domain.enums import EvidenceDirection, EvidenceType, ObservationType, ReferenceKind
from agentic.domain.evidence import Evidence, SourceReference
from agentic.domain.manifest import DatasetManifest
from agentic.domain.observation import Observation
from agentic.domain.provenance import Provenance
from agentic.domain.statistics import StatisticalSummary, Uncertainty

from ..capability import ValidationIssue
from ..context import ExperimentContext
from ..errors import ExperimentExecutionError, ParameterError
from ..stats import evidence_strength


def require_frame(context: ExperimentContext) -> pd.DataFrame:
    if context.frame is None:
        raise ExperimentExecutionError("this experiment requires a tabular dataset (no frame materialized)")
    return context.frame


def manifest_column_names(manifest: DatasetManifest) -> set[str]:
    return {c.name for c in manifest.columns}


def ensure_columns(names: list[str], manifest: DatasetManifest) -> list[ValidationIssue]:
    present = manifest_column_names(manifest)
    return [
        ValidationIssue(code="UNKNOWN_COLUMN", message=f"column '{n}' not in dataset", field=n)
        for n in names
        if n and n not in present
    ]


def default_time_column(manifest: DatasetManifest) -> str | None:
    col = manifest.time_index_column()
    return col.name if col else None


def default_entity_column(manifest: DatasetManifest) -> str | None:
    col = manifest.entity_id_column()
    return col.name if col else None


def numeric_array(frame: pd.DataFrame, column: str) -> np.ndarray:
    if column not in frame.columns:
        raise ParameterError(f"column '{column}' not present at runtime", detail=column)
    return pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)


def nonnull_coverage(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or len(frame) == 0:
        return 0.0
    return float(frame[column].notna().sum()) / float(len(frame))


def source_ref(manifest: DatasetManifest, *, column: str | None = None) -> SourceReference:
    return SourceReference(
        kind=ReferenceKind.dataset,
        ref=manifest.name,
        locator=(f"column={column}" if column else (manifest.fingerprint or None)),
    )


def make_statistics(
    *,
    sample_size: int | None = None,
    effect_size: float | None = None,
    effect_size_kind: str | None = None,
    p_value: float | None = None,
    uncertainty: Uncertainty | None = None,
    assumptions: list[str] | None = None,
    diagnostics: dict[str, float] | None = None,
    coverage: float | None = None,
    warnings: list[str] | None = None,
) -> StatisticalSummary:
    def _clean(x):
        if x is None:
            return None
        return None if isinstance(x, float) and not np.isfinite(x) else x

    return StatisticalSummary(
        sample_size=sample_size,
        effect_size=_clean(effect_size),
        effect_size_kind=effect_size_kind,
        p_value=_clean(p_value),
        uncertainty=uncertainty,
        assumptions=assumptions or [],
        diagnostics={k: float(v) for k, v in (diagnostics or {}).items() if np.isfinite(v)},
        coverage=coverage,
        warnings=warnings or [],
    )


def make_observation(
    *,
    statement: str,
    provenance: Provenance,
    observation_type: ObservationType = ObservationType.value,
    magnitude: float | None = None,
    entity_ref: str | None = None,
    metric_ref: str | None = None,
    data_reference: SourceReference | None = None,
) -> Observation:
    mag = magnitude
    if mag is not None and (not np.isfinite(mag)):
        mag = None
    return Observation(
        statement=statement,
        observation_type=observation_type,
        magnitude=mag,
        entity_ref=entity_ref,
        metric_ref=metric_ref,
        data_reference=data_reference,
        provenance=provenance,
    )


def make_evidence(
    *,
    evidence_type: EvidenceType,
    claim: str,
    direction: EvidenceDirection,
    provenance: Provenance,
    statistics: StatisticalSummary | None = None,
    source_reference: SourceReference,
    artifact_ids: list[str] | None = None,
) -> Evidence:
    if statistics is not None:
        strength, reliability, coverage = evidence_strength(statistics)
    else:
        strength, reliability, coverage = 0.5, 0.5, 1.0
    return Evidence(
        evidence_type=evidence_type,
        source_reference=source_reference,
        claim=claim,
        direction=direction,
        strength=strength,
        reliability=reliability,
        coverage=coverage,
        artifact_ids=artifact_ids or [],
        statistics=statistics,
        provenance=provenance,
    )
