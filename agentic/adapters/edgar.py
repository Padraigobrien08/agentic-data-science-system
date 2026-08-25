"""
EDGAR input adapter.

Wraps the existing deterministic EDGAR pipeline as a first-party input adapter so
EDGAR stays a one-click demo, a reference template, and a regression fixture. The
adapter only *describes* the dataset and injects EDGAR domain knowledge as
**hints**; the general profilers stay domain-agnostic. No numerical computation
is moved or rewritten here — data acquisition still lives in ``src`` /
``edgar_project`` and is reached offline for fixtures.

Manifest sources:

* ``parameters['panel_csv']`` — profile a materialized EDGAR panel file.
* otherwise — declare the canonical EDGAR panel schema (no data materialized).
"""

from __future__ import annotations

from pathlib import Path

from agentic.domain.enums import ColumnRole, DatasetKind, Modality, SemanticType
from agentic.domain.manifest import ColumnSpec, DatasetManifest, DatasetOrigin

from .base import AdapterInfo, AdapterRequest, InputAdapter
from .capabilities import PermittedOperation, SourceCapabilityDescriptor, SourceType
from .materialize import (
    DatasetMaterializer,
    SchemaOnlyMaterializer,
    TabularFileMaterializer,
)

ADAPTER_ID = "edgar"
ADAPTER_VERSION = "2"

# EDGAR domain knowledge, injected as hints (kept out of the general layer).
EDGAR_ROLE_HINTS: dict[str, ColumnRole] = {
    "ticker": ColumnRole.entity_id,
    "cik": ColumnRole.identifier,
    "company_name": ColumnRole.dimension,
    "period": ColumnRole.time_index,
}
EDGAR_SEMANTIC_HINTS: dict[str, SemanticType] = {
    "ticker": SemanticType.identifier,
    "cik": SemanticType.identifier,
    "company_name": SemanticType.categorical,
    "period": SemanticType.temporal,
    "revenue": SemanticType.monetary,
    "net_income": SemanticType.monetary,
    "revenue_growth_qoq": SemanticType.percentage,
    "net_margin": SemanticType.percentage,
    "current_ratio": SemanticType.real,
    "debt_to_assets": SemanticType.percentage,
}
EDGAR_UNIT_HINTS: dict[str, str] = {
    "revenue": "USD",
    "net_income": "USD",
    "revenue_growth_qoq": "ratio",
    "net_margin": "ratio",
    "current_ratio": "ratio",
    "debt_to_assets": "ratio",
}

_IDENTITY_COLUMNS: tuple[tuple[str, str, ColumnRole], ...] = (
    ("ticker", "str", ColumnRole.entity_id),
    ("cik", "int", ColumnRole.identifier),
    ("company_name", "str", ColumnRole.dimension),
    ("period", "period", ColumnRole.time_index),
)


def _feature_cols() -> list[str]:
    from src.anomaly import FEATURE_COLS

    return list(FEATURE_COLS)


def _default_tickers() -> list[str]:
    import config

    return [str(t).strip().upper() for t in config.DEFAULT_TICKERS if str(t).strip()]


class EDGARAdapter(InputAdapter):
    """First-party adapter describing the SEC EDGAR financial panel."""

    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def capabilities(self) -> SourceCapabilityDescriptor:
        return SourceCapabilityDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            supported_source_types=[SourceType.edgar, SourceType.csv],
            supported_modalities=[Modality.tabular, Modality.time_series],
            permitted_operations=[
                PermittedOperation.materialize,
                PermittedOperation.profile_schema,
                PermittedOperation.profile_quality,
                PermittedOperation.fingerprint,
                PermittedOperation.full_scan,
            ],
            supports_temporal=True,
            supports_entity_ids=True,
            notes="Wraps the deterministic EDGAR pipeline; entity=ticker, time=fiscal period.",
        )

    def describe(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id=ADAPTER_ID,
            version=ADAPTER_VERSION,
            title="SEC EDGAR financial panel",
            description=(
                "Deterministic EDGAR pipeline exposed as an input adapter: entity x period "
                "financial metrics resolved from SEC companyfacts."
            ),
            default_dataset_kind=DatasetKind.tabular_panel.value,
        )

    def materializer(self, request: AdapterRequest) -> DatasetMaterializer:
        panel_csv = request.parameters.get("panel_csv")
        if panel_csv:
            return TabularFileMaterializer(
                Path(panel_csv),
                adapter_id=ADAPTER_ID,
                source_type=SourceType.edgar.value,
                name=f"EDGAR panel ({Path(panel_csv).name})",
                modality=Modality.time_series,
                dataset_kind=DatasetKind.tabular_panel,
                role_hints=EDGAR_ROLE_HINTS,
                semantic_hints=EDGAR_SEMANTIC_HINTS,
                unit_hints=EDGAR_UNIT_HINTS,
                entity_id_fields=["ticker"],
                time_field="period",
            )
        return self._declared_materializer(request)

    def _declared_materializer(self, request: AdapterRequest) -> SchemaOnlyMaterializer:
        entities = [e.strip().upper() for e in request.entities if e.strip()] or _default_tickers()
        columns: list[ColumnSpec] = [
            ColumnSpec(
                name=name,
                dtype=dtype,
                role=role,
                semantic_type=EDGAR_SEMANTIC_HINTS.get(name, SemanticType.unknown),
                nullable=(role != ColumnRole.entity_id),
                unit=EDGAR_UNIT_HINTS.get(name),
            )
            for name, dtype, role in _IDENTITY_COLUMNS
        ]
        columns.extend(
            ColumnSpec(
                name=m,
                dtype="float",
                role=ColumnRole.metric,
                semantic_type=EDGAR_SEMANTIC_HINTS.get(m, SemanticType.real),
                nullable=True,
                unit=EDGAR_UNIT_HINTS.get(m),
            )
            for m in _feature_cols()
        )
        return SchemaOnlyMaterializer(
            adapter_id=ADAPTER_ID,
            source_type=SourceType.edgar.value,
            name="EDGAR financial panel",
            columns=columns,
            entities=entities,
            modality=Modality.time_series,
            dataset_kind=DatasetKind.tabular_panel,
            provenance_parameters={"entities": ",".join(entities)},
        )

    def build_manifest(self, request: AdapterRequest) -> DatasetManifest:
        """Build a manifest, recording the EDGAR panel path in provenance when used."""
        materialized = self.materializer(request).materialize()
        extra: dict[str, str] = {}
        panel_csv = request.parameters.get("panel_csv")
        if panel_csv:
            extra["panel_csv"] = panel_csv
        return self._manifest_builder().build(
            materialized,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            description="EDGAR panel manifest.",
            extra_provenance=extra,
            # These are real filings. Saying so explicitly is what lets the showcase label a
            # run over live SEC data as live, and a run over generated rows as generated,
            # instead of leaving a reader to infer it from the dataset's name.
            origin=DatasetOrigin.live,
        )


# Backward-compatible alias (earlier name).
EdgarInputAdapter = EDGARAdapter
