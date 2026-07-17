"""
EDGAR input adapter.

Wraps the existing deterministic EDGAR pipeline as a first-party input adapter,
so the generalized platform keeps EDGAR working as a demo, a reference template,
and a regression fixture. This adapter only *describes* the dataset; the actual
SEC fetch and numerical computation stay in ``src`` and ``edgar_project`` and
are reached through the established MCP tooling — no computation moves here.

The manifest is built offline. When a panel CSV path is supplied via
``parameters['panel_csv']`` the columns/entities/row_count are derived from that
materialized file; otherwise the canonical EDGAR panel schema is declared from
the pipeline's known metric contract.
"""

from __future__ import annotations

from pathlib import Path

from agentic.domain.enums import ColumnRole, DatasetKind
from agentic.domain.manifest import ColumnSpec, DatasetManifest, DatasetProvenance

from .base import AdapterInfo, AdapterRequest, InputAdapter

ADAPTER_ID = "edgar"
ADAPTER_VERSION = "1"

# Canonical identity columns of the EDGAR panel (metrics are added from the
# pipeline's FEATURE_COLS contract so this stays truthful if that list changes).
_IDENTITY_COLUMNS: tuple[tuple[str, str, ColumnRole, str | None], ...] = (
    ("ticker", "str", ColumnRole.entity_id, None),
    ("cik", "int", ColumnRole.identifier, None),
    ("company_name", "str", ColumnRole.dimension, None),
    ("period", "period", ColumnRole.time_index, None),
)

# Units for known EDGAR metrics (best-effort; unknown metrics default to None).
_METRIC_UNITS: dict[str, str] = {
    "revenue": "USD",
    "net_income": "USD",
    "revenue_growth_qoq": "ratio",
    "net_margin": "ratio",
    "current_ratio": "ratio",
    "debt_to_assets": "ratio",
}


def _feature_cols() -> list[str]:
    """EDGAR metric columns from the deterministic pipeline contract (offline import)."""
    from src.anomaly import FEATURE_COLS

    return list(FEATURE_COLS)


def _default_tickers() -> list[str]:
    import config

    return [str(t).strip().upper() for t in config.DEFAULT_TICKERS if str(t).strip()]


def _infer_role(name: str, metric_names: set[str]) -> tuple[ColumnRole, str, str | None]:
    """Map a raw panel column to (role, dtype, unit) using EDGAR conventions."""
    lname = name.lower()
    if lname == "ticker":
        return ColumnRole.entity_id, "str", None
    if lname == "cik":
        return ColumnRole.identifier, "int", None
    if lname == "company_name":
        return ColumnRole.dimension, "str", None
    if lname == "period":
        return ColumnRole.time_index, "period", None
    if lname in metric_names:
        return ColumnRole.metric, "float", _METRIC_UNITS.get(lname)
    return ColumnRole.dimension, "str", None


class EdgarInputAdapter(InputAdapter):
    """First-party adapter describing the SEC EDGAR financial panel."""

    adapter_id = ADAPTER_ID

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

    def build_manifest(self, request: AdapterRequest) -> DatasetManifest:
        metric_names = _feature_cols()
        panel_csv = request.parameters.get("panel_csv")
        if panel_csv:
            return self._manifest_from_panel(Path(panel_csv), request, metric_names)
        return self._manifest_declared(request, metric_names)

    # -- offline manifest builders ------------------------------------------

    def _manifest_declared(
        self,
        request: AdapterRequest,
        metric_names: list[str],
    ) -> DatasetManifest:
        entities = [e.strip().upper() for e in request.entities if e.strip()] or _default_tickers()
        columns: list[ColumnSpec] = [
            ColumnSpec(name=name, dtype=dtype, role=role, nullable=(role != ColumnRole.entity_id), unit=unit)
            for name, dtype, role, unit in _IDENTITY_COLUMNS
        ]
        columns.extend(
            ColumnSpec(name=m, dtype="float", role=ColumnRole.metric, nullable=True, unit=_METRIC_UNITS.get(m))
            for m in metric_names
        )
        return DatasetManifest(
            name="EDGAR financial panel",
            description="Declared EDGAR panel schema (no data materialized).",
            dataset_kind=DatasetKind.tabular_panel,
            columns=columns,
            entities=entities,
            row_count=None,
            provenance=self._provenance(request, source="SEC EDGAR companyfacts (declared schema)"),
        )

    def _manifest_from_panel(
        self,
        panel_csv: Path,
        request: AdapterRequest,
        metric_names: list[str],
    ) -> DatasetManifest:
        import pandas as pd

        if not panel_csv.is_file():
            raise FileNotFoundError(f"panel_csv not found: {panel_csv}")
        df = pd.read_csv(panel_csv)
        metric_set = {m.lower() for m in metric_names}
        columns: list[ColumnSpec] = []
        for raw in df.columns:
            name = str(raw)
            role, dtype, unit = _infer_role(name, metric_set)
            columns.append(ColumnSpec(name=name, dtype=dtype, role=role, nullable=True, unit=unit))

        entities = [e.strip().upper() for e in request.entities if e.strip()]
        if not entities and "ticker" in {str(c).lower() for c in df.columns}:
            ticker_col = next(c for c in df.columns if str(c).lower() == "ticker")
            entities = sorted({str(v).strip().upper() for v in df[ticker_col].dropna().unique() if str(v).strip()})

        return DatasetManifest(
            name=f"EDGAR financial panel ({panel_csv.name})",
            description="EDGAR panel manifest derived from a materialized panel CSV.",
            dataset_kind=DatasetKind.tabular_panel,
            columns=columns,
            entities=entities,
            row_count=int(len(df)),
            provenance=self._provenance(
                request,
                source=f"EDGAR panel CSV: {panel_csv}",
                extra={"panel_csv": str(panel_csv)},
            ),
        )

    def _provenance(
        self,
        request: AdapterRequest,
        *,
        source: str,
        extra: dict[str, str] | None = None,
    ) -> DatasetProvenance:
        params: dict[str, str] = {
            "entities": ",".join(request.entities),
            **request.parameters,
        }
        if extra:
            params.update(extra)
        return DatasetProvenance(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source=source,
            parameters=params,
        )
