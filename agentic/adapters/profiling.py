"""
General schema and data-quality profilers.

These are strictly **domain-agnostic**: they infer column semantics and quality
from values alone and never reference any dataset's business vocabulary. Domain
knowledge (which column is an entity id, which is a monetary amount, and so on)
enters only through *hints* on the :class:`MaterializedDataset`, supplied by the
adapter — never hard-coded here.

Determinism: :func:`compute_fingerprint` is a pure content hash — identical
inputs produce identical fingerprints.
"""

from __future__ import annotations

import hashlib

import pandas as pd

from agentic.domain.enums import ColumnRole, QualitySeverity, SemanticType
from agentic.domain.manifest import ColumnSpec
from agentic.domain.profiles import (
    ColumnMissingness,
    DatasetDimensions,
    DuplicateSummary,
    MissingnessSummary,
    QualityWarning,
    TemporalCoverage,
)

from .materialize import MaterializedDataset

# Cardinality below which an object column is treated as categorical rather than text.
_CATEGORICAL_MAX_DISTINCT = 20
_CATEGORICAL_MAX_RATIO = 0.5


# ---------------------------------------------------------------------------
# Fingerprinting (deterministic content hash)
# ---------------------------------------------------------------------------


def _hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def compute_fingerprint(materialized: MaterializedDataset) -> str:
    """Deterministic content fingerprint of a materialized dataset."""
    if materialized.is_tabular():
        frame = materialized.frame
        assert frame is not None
        header = ",".join(f"{c}:{frame[c].dtype}" for c in frame.columns)
        body = frame.to_csv(index=False)
        return "sha256:" + _hash("tabular", header, body)
    if materialized.is_documents():
        docs = materialized.documents or []
        rows = sorted(f"{d.id}:{_hash(d.text)}" for d in docs)
        return "sha256:" + _hash("documents", *rows)
    # schema-only: fingerprint the declared schema.
    cols = materialized.declared_columns or []
    parts = [f"{c.name}:{c.role.value}:{c.semantic_type.value}:{c.dtype}" for c in cols]
    return "sha256:" + _hash("schema_only", *parts)


# ---------------------------------------------------------------------------
# Schema profiling
# ---------------------------------------------------------------------------


def _infer_semantic_type(series: pd.Series) -> SemanticType:
    """Infer a generic semantic type from values (no domain vocabulary)."""
    if pd.api.types.is_bool_dtype(series):
        return SemanticType.boolean
    if pd.api.types.is_integer_dtype(series):
        return SemanticType.integer
    if pd.api.types.is_float_dtype(series):
        return SemanticType.real
    if pd.api.types.is_datetime64_any_dtype(series):
        return SemanticType.temporal
    non_null = series.dropna()
    n = len(non_null)
    if n == 0:
        return SemanticType.unknown
    distinct = int(non_null.nunique())
    ratio = distinct / n
    if n > 1 and ratio == 1.0:
        return SemanticType.identifier
    if distinct <= _CATEGORICAL_MAX_DISTINCT or ratio <= _CATEGORICAL_MAX_RATIO:
        return SemanticType.categorical
    return SemanticType.text


def _role_from_semantic(sem: SemanticType) -> ColumnRole:
    """Map a generic semantic type to a generic column role."""
    if sem is SemanticType.temporal:
        return ColumnRole.time_index
    if sem is SemanticType.identifier:
        return ColumnRole.identifier
    if sem in (
        SemanticType.integer,
        SemanticType.real,
        SemanticType.monetary,
        SemanticType.percentage,
        SemanticType.count,
    ):
        return ColumnRole.metric
    if sem in (SemanticType.categorical, SemanticType.text, SemanticType.boolean):
        return ColumnRole.dimension
    return ColumnRole.unknown


class SchemaProfiler:
    """Infers a typed column schema from materialized data (domain-agnostic)."""

    def profile(self, materialized: MaterializedDataset) -> list[ColumnSpec]:
        if materialized.is_schema_only():
            return list(materialized.declared_columns or [])
        if materialized.is_documents():
            return self._profile_documents(materialized)
        return self._profile_frame(materialized)

    def _profile_frame(self, materialized: MaterializedDataset) -> list[ColumnSpec]:
        frame = materialized.frame
        assert frame is not None
        columns: list[ColumnSpec] = []
        for raw in frame.columns:
            name = str(raw)
            series = frame[raw]
            sem = materialized.semantic_hints.get(name) or _infer_semantic_type(series)
            if name == materialized.time_field:
                role = ColumnRole.time_index
            elif name in materialized.entity_id_fields:
                role = ColumnRole.entity_id
            else:
                role = _role_from_semantic(sem)
            role = materialized.role_hints.get(name, role)
            columns.append(
                ColumnSpec(
                    name=name,
                    dtype=str(series.dtype),
                    role=role,
                    semantic_type=sem,
                    nullable=bool(series.isna().any()),
                    unit=materialized.unit_hints.get(name),
                )
            )
        return columns

    def _profile_documents(self, materialized: MaterializedDataset) -> list[ColumnSpec]:
        docs = materialized.documents or []
        metadata_keys: list[str] = []
        for d in docs:
            for k in d.metadata:
                if k not in metadata_keys:
                    metadata_keys.append(k)
        columns = [
            ColumnSpec(name="doc_id", dtype="str", role=ColumnRole.identifier, semantic_type=SemanticType.identifier, nullable=False),
            ColumnSpec(name="text", dtype="str", role=ColumnRole.dimension, semantic_type=SemanticType.text),
        ]
        for k in metadata_keys:
            columns.append(
                ColumnSpec(
                    name=k,
                    dtype="str",
                    role=materialized.role_hints.get(k, ColumnRole.dimension),
                    semantic_type=materialized.semantic_hints.get(k, SemanticType.categorical),
                    nullable=True,
                )
            )
        return columns


# ---------------------------------------------------------------------------
# Data-quality profiling
# ---------------------------------------------------------------------------


class QualityProfile:
    """Bundle of computed quality descriptors (transient, not serialized)."""

    def __init__(
        self,
        *,
        dimensions: DatasetDimensions,
        missingness: MissingnessSummary,
        duplicates: DuplicateSummary,
        temporal_coverage: TemporalCoverage | None,
        warnings: list[QualityWarning],
    ) -> None:
        self.dimensions = dimensions
        self.missingness = missingness
        self.duplicates = duplicates
        self.temporal_coverage = temporal_coverage
        self.warnings = warnings


class DataQualityProfiler:
    """Computes dimensions, missingness, duplicates, temporal bounds, warnings."""

    def profile(self, materialized: MaterializedDataset, columns: list[ColumnSpec]) -> QualityProfile:
        if materialized.is_documents():
            return self._profile_documents(materialized, columns)
        if materialized.is_schema_only():
            return self._empty_profile(columns)
        return self._profile_frame(materialized, columns)

    def _empty_profile(self, columns: list[ColumnSpec]) -> QualityProfile:
        return QualityProfile(
            dimensions=DatasetDimensions(row_count=0, column_count=len(columns)),
            missingness=MissingnessSummary(),
            duplicates=DuplicateSummary(),
            temporal_coverage=None,
            warnings=[
                QualityWarning(
                    code="SCHEMA_ONLY",
                    severity=QualitySeverity.info,
                    message="Manifest declared from schema only; no data was materialized.",
                )
            ],
        )

    def _profile_frame(self, materialized: MaterializedDataset, columns: list[ColumnSpec]) -> QualityProfile:
        frame = materialized.frame
        assert frame is not None
        n = len(frame)
        warnings: list[QualityWarning] = []

        # Missingness
        by_col: list[ColumnMissingness] = []
        missing_cells = 0
        for raw in frame.columns:
            name = str(raw)
            miss = int(frame[raw].isna().sum())
            missing_cells += miss
            ratio = (miss / n) if n else 0.0
            by_col.append(ColumnMissingness(column=name, missing_count=miss, missing_ratio=ratio))
            if n and miss == n:
                warnings.append(
                    QualityWarning(code="COLUMN_ALL_NULL", severity=QualitySeverity.error,
                                   message=f"Column '{name}' is entirely null.", column=name)
                )
            elif n and ratio > 0.5:
                warnings.append(
                    QualityWarning(code="HIGH_MISSINGNESS", severity=QualitySeverity.warning,
                                   message=f"Column '{name}' is {ratio:.0%} null.", column=name)
                )
            if n > 1 and int(frame[raw].nunique(dropna=True)) == 1:
                warnings.append(
                    QualityWarning(code="CONSTANT_COLUMN", severity=QualitySeverity.info,
                                   message=f"Column '{name}' has a single distinct value.", column=name)
                )
        total_cells = n * frame.shape[1]
        missingness = MissingnessSummary(
            total_cells=total_cells,
            missing_cells=missing_cells,
            overall_missing_ratio=(missing_cells / total_cells) if total_cells else 0.0,
            by_column=by_col,
        )

        # Duplicates (full-row + key-based when entity+time roles exist)
        dup_rows = int(frame.duplicated(keep="first").sum())
        entity_cols = [c.name for c in columns if c.role == ColumnRole.entity_id]
        time_cols = [c.name for c in columns if c.role == ColumnRole.time_index]
        key_fields = entity_cols + time_cols
        dup_keys: int | None = None
        if key_fields and all(k in frame.columns for k in key_fields):
            dup_keys = int(frame.duplicated(subset=key_fields, keep="first").sum())
        duplicates = DuplicateSummary(
            duplicate_row_count=dup_rows,
            duplicate_row_ratio=(dup_rows / n) if n else 0.0,
            key_fields=key_fields,
            duplicate_key_count=dup_keys,
        )
        if dup_rows:
            warnings.append(
                QualityWarning(code="DUPLICATE_ROWS", severity=QualitySeverity.warning,
                               message=f"{dup_rows} duplicate row(s) detected.")
            )
        if dup_keys:
            warnings.append(
                QualityWarning(code="DUPLICATE_KEYS", severity=QualitySeverity.warning,
                               message=f"{dup_keys} duplicate key row(s) on {key_fields}.")
            )
        if n == 1:
            warnings.append(
                QualityWarning(code="SINGLE_ROW", severity=QualitySeverity.info,
                               message="Dataset has a single row.")
            )

        # Temporal coverage
        temporal: TemporalCoverage | None = None
        time_col = time_cols[0] if time_cols else materialized.time_field
        if time_col and time_col in frame.columns:
            col = frame[time_col].dropna()
            if len(col):
                as_str = col.astype(str)
                temporal = TemporalCoverage(
                    field=time_col,
                    minimum=str(as_str.min()),
                    maximum=str(as_str.max()),
                    distinct_periods=int(col.nunique()),
                )

        # Dimensions
        entity_count: int | None = None
        if entity_cols and entity_cols[0] in frame.columns:
            entity_count = int(frame[entity_cols[0]].nunique(dropna=True))
        dimensions = DatasetDimensions(
            row_count=n,
            column_count=frame.shape[1],
            entity_count=entity_count,
            period_count=(temporal.distinct_periods if temporal else None),
        )
        return QualityProfile(
            dimensions=dimensions,
            missingness=missingness,
            duplicates=duplicates,
            temporal_coverage=temporal,
            warnings=warnings,
        )

    def _profile_documents(self, materialized: MaterializedDataset, columns: list[ColumnSpec]) -> QualityProfile:
        docs = materialized.documents or []
        n = len(docs)
        warnings: list[QualityWarning] = []
        empty_text = sum(1 for d in docs if not d.text.strip())
        if empty_text:
            warnings.append(
                QualityWarning(code="EMPTY_DOCUMENTS", severity=QualitySeverity.warning,
                               message=f"{empty_text} document(s) have empty text.")
            )
        # Duplicate documents by text hash.
        seen: set[str] = set()
        dup_docs = 0
        for d in docs:
            key = _hash(d.text)
            if key in seen:
                dup_docs += 1
            seen.add(key)
        if dup_docs:
            warnings.append(
                QualityWarning(code="DUPLICATE_DOCUMENTS", severity=QualitySeverity.warning,
                               message=f"{dup_docs} duplicate document(s) by text.")
            )
        missingness = MissingnessSummary(
            total_cells=n, missing_cells=empty_text,
            overall_missing_ratio=(empty_text / n) if n else 0.0,
            by_column=[ColumnMissingness(column="text", missing_count=empty_text,
                                         missing_ratio=(empty_text / n) if n else 0.0)],
        )
        duplicates = DuplicateSummary(
            duplicate_row_count=dup_docs,
            duplicate_row_ratio=(dup_docs / n) if n else 0.0,
        )
        dimensions = DatasetDimensions(row_count=n, column_count=len(columns))
        return QualityProfile(
            dimensions=dimensions,
            missingness=missingness,
            duplicates=duplicates,
            temporal_coverage=None,
            warnings=warnings,
        )
