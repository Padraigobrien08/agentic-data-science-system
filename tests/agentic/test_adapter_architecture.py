"""
Tests for the input-adapter architecture.

Proves: the EDGAR fixture path still works; CSV/Parquet inputs produce manifests;
identical inputs produce identical fingerprints; malformed inputs produce
structured failures; and the general layer holds no domain-specific assumptions.
All offline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agentic.adapters import (
    AdapterRequest,
    DocumentRecord,
    EDGARAdapter,
    EmptyDatasetError,
    InMemoryDatasetAdapter,
    LocalTabularAdapter,
    MalformedDatasetError,
    SchemaProfiler,
    SourceCapabilityDescriptor,
    SourceNotFoundError,
    SourceType,
    UnsupportedSourceError,
    build_default_registry,
)
from agentic.adapters.materialize import InMemoryMaterializer
from agentic.domain.enums import ColumnRole, Modality, SemanticType

REPO = Path(__file__).resolve().parents[2]
EDGAR_FIXTURE = REPO / "edgar_project/evaluation/fixtures/data/01_simple_anomaly_features.csv"


def _panel_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT"],
            "period": ["2023-Q1", "2023-Q2", "2023-Q1"],
            "revenue": [100.0, 110.0, 50.0],
            "net_margin": [0.12, 0.13, 0.20],
        }
    )


# --- EDGAR fixture path preserved ------------------------------------------


def test_edgar_fixture_panel_still_produces_manifest() -> None:
    assert EDGAR_FIXTURE.is_file(), "EDGAR regression fixture missing"
    manifest = EDGARAdapter().build_manifest(
        AdapterRequest(parameters={"panel_csv": str(EDGAR_FIXTURE)})
    )
    by_name = {c.name: c for c in manifest.columns}
    assert by_name["cik"].role is ColumnRole.identifier
    assert by_name["period"].role is ColumnRole.time_index
    assert by_name["revenue"].role is ColumnRole.metric
    assert by_name["revenue"].semantic_type is SemanticType.monetary
    assert manifest.row_count and manifest.row_count > 0
    assert manifest.temporal_coverage is not None
    assert manifest.provenance.adapter_id == "edgar"


def test_registry_registers_edgar_and_local_tabular() -> None:
    reg = build_default_registry()
    assert "edgar" in reg.ids()
    assert "local_tabular" in reg.ids()


# --- CSV / Parquet manifests -----------------------------------------------


def test_csv_and_parquet_inputs_produce_manifests(tmp_path: Path) -> None:
    df = _panel_df()
    csv = tmp_path / "p.csv"
    pq = tmp_path / "p.parquet"
    df.to_csv(csv, index=False)
    df.to_parquet(pq)
    adapter = LocalTabularAdapter()

    for path in (csv, pq):
        m = adapter.build_manifest(AdapterRequest(parameters={"path": str(path)}))
        assert m.dimensions.row_count == 3
        assert m.dimensions.column_count == 4
        assert set(m.available_fields()) == {"ticker", "period", "revenue", "net_margin"}
        assert m.fingerprint and m.fingerprint.startswith("sha256:")
        assert m.missingness is not None
        assert m.duplicates is not None


def test_manifest_contains_all_required_contents(tmp_path: Path) -> None:
    csv = tmp_path / "p.csv"
    _panel_df().to_csv(csv, index=False)
    m = LocalTabularAdapter().build_manifest(
        AdapterRequest(parameters={"path": str(csv), "time_field": "period", "entity_id_fields": "ticker"})
    )
    # source identity / fingerprint / schema / semantic types / dimensions
    assert m.source_identity is not None and m.source_identity.adapter_id == "local_tabular"
    assert m.fingerprint
    assert m.columns and all(c.semantic_type is not None for c in m.columns)
    assert m.dimensions is not None
    # temporal bounds (time_field supplied)
    assert m.temporal_coverage is not None and m.temporal_coverage.field == "period"
    # missingness / duplicates / quality warnings / provenance / adapter version
    assert m.missingness is not None
    assert m.duplicates is not None
    assert isinstance(m.quality_warnings, list)
    assert m.provenance.adapter_id == "local_tabular"
    assert m.adapter_version == "1"


def test_quality_warnings_are_structured(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 1], "b": [None, None], "id": [1, 1]})
    csv = tmp_path / "q.csv"
    df.to_csv(csv, index=False)
    m = LocalTabularAdapter().build_manifest(AdapterRequest(parameters={"path": str(csv)}))
    codes = {w.code for w in m.quality_warnings}
    assert "COLUMN_ALL_NULL" in codes          # column b
    assert "DUPLICATE_ROWS" in codes           # rows are identical
    assert m.duplicates.duplicate_row_count == 1


# --- Fingerprint determinism ------------------------------------------------


def test_identical_inputs_produce_identical_fingerprints(tmp_path: Path) -> None:
    df = _panel_df()
    csv1 = tmp_path / "a.csv"
    csv2 = tmp_path / "b.csv"
    pq = tmp_path / "a.parquet"
    df.to_csv(csv1, index=False)
    df.to_csv(csv2, index=False)
    df.to_parquet(pq)
    adapter = LocalTabularAdapter()

    fp1 = adapter.build_manifest(AdapterRequest(parameters={"path": str(csv1)})).fingerprint
    fp2 = adapter.build_manifest(AdapterRequest(parameters={"path": str(csv2)})).fingerprint
    fp_pq = adapter.build_manifest(AdapterRequest(parameters={"path": str(pq)})).fingerprint
    fp_mem = InMemoryDatasetAdapter(frame=df).build_manifest(AdapterRequest()).fingerprint

    # same content across files, formats, and in-memory -> same fingerprint
    assert fp1 == fp2 == fp_pq == fp_mem


def test_different_content_produces_different_fingerprint(tmp_path: Path) -> None:
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    _panel_df().to_csv(a, index=False)
    df2 = _panel_df()
    df2.loc[0, "revenue"] = 999.0
    df2.to_csv(b, index=False)
    adapter = LocalTabularAdapter()
    fa = adapter.build_manifest(AdapterRequest(parameters={"path": str(a)})).fingerprint
    fb = adapter.build_manifest(AdapterRequest(parameters={"path": str(b)})).fingerprint
    assert fa != fb


# --- Malformed inputs -> structured failures --------------------------------


def test_missing_file_is_structured_and_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(SourceNotFoundError) as ei:
        LocalTabularAdapter().build_manifest(AdapterRequest(parameters={"path": str(tmp_path / "nope.csv")}))
    assert ei.value.code == "SOURCE_NOT_FOUND"
    assert ei.value.to_dict()["code"] == "SOURCE_NOT_FOUND"
    # back-compat: also a FileNotFoundError
    assert isinstance(ei.value, FileNotFoundError)


def test_unsupported_extension_is_structured(tmp_path: Path) -> None:
    bad = tmp_path / "data.xlsx"
    bad.write_text("nonsense")
    with pytest.raises(UnsupportedSourceError) as ei:
        LocalTabularAdapter().build_manifest(AdapterRequest(parameters={"path": str(bad)}))
    assert ei.value.code == "UNSUPPORTED_SOURCE"


def test_empty_and_malformed_csv_are_structured(tmp_path: Path) -> None:
    header_only = tmp_path / "h.csv"
    header_only.write_text("a,b,c\n")
    with pytest.raises(EmptyDatasetError):
        LocalTabularAdapter().build_manifest(AdapterRequest(parameters={"path": str(header_only)}))

    truly_empty = tmp_path / "e.csv"
    truly_empty.write_text("")
    with pytest.raises(MalformedDatasetError):
        LocalTabularAdapter().build_manifest(AdapterRequest(parameters={"path": str(truly_empty)}))


def test_missing_path_param_is_structured() -> None:
    with pytest.raises(UnsupportedSourceError):
        LocalTabularAdapter().build_manifest(AdapterRequest())


# --- Capability declarations ------------------------------------------------


def test_adapters_declare_capabilities() -> None:
    for adapter in (EDGARAdapter(), LocalTabularAdapter(), InMemoryDatasetAdapter(frame=_panel_df())):
        cap = adapter.capabilities()
        assert isinstance(cap, SourceCapabilityDescriptor)
        assert cap.supported_source_types
        assert cap.supported_modalities
        assert cap.permitted_operations
    assert EDGARAdapter().capabilities().supports_source_type(SourceType.edgar)
    assert LocalTabularAdapter().capabilities().supports_source_type(SourceType.parquet)


# --- Document modality ------------------------------------------------------


def test_in_memory_document_collection() -> None:
    docs = [
        DocumentRecord(id="1", text="alpha beta", metadata={"lang": "en"}),
        DocumentRecord(id="2", text="alpha beta"),  # duplicate text
        DocumentRecord(id="3", text=""),            # empty
    ]
    m = InMemoryDatasetAdapter(documents=docs).build_manifest(AdapterRequest())
    assert m.modality is Modality.document
    assert m.dimensions.row_count == 3
    codes = {w.code for w in m.quality_warnings}
    assert "EMPTY_DOCUMENTS" in codes
    assert "DUPLICATE_DOCUMENTS" in codes
    assert "doc_id" in m.available_fields()


# --- No domain leakage into the general layer -------------------------------


def test_general_schema_profiler_makes_no_edgar_assumptions() -> None:
    """The general profiler must not know 'ticker' is an entity or 'revenue' is money."""
    materialized = InMemoryMaterializer(frame=_panel_df()).materialize()  # no hints
    columns = {c.name: c for c in SchemaProfiler().profile(materialized)}
    # ticker is NOT promoted to entity_id without a hint
    assert columns["ticker"].role is not ColumnRole.entity_id
    # revenue is generic 'real', NOT 'monetary'
    assert columns["revenue"].semantic_type is SemanticType.real
    # '2023-Q1' style periods are NOT recognized as temporal by the general layer
    assert columns["period"].role is not ColumnRole.time_index


def test_edgar_hints_only_apply_through_the_adapter() -> None:
    """Same frame: EDGAR adapter applies roles/units; local tabular does not."""
    df = _panel_df()
    edgar = InMemoryDatasetAdapter(
        frame=df,
        role_hints={"ticker": ColumnRole.entity_id},
        semantic_hints={"revenue": SemanticType.monetary},
        unit_hints={"revenue": "USD"},
        time_field="period",
        entity_id_fields=["ticker"],
    ).build_manifest(AdapterRequest())
    plain = InMemoryDatasetAdapter(frame=df).build_manifest(AdapterRequest())

    e = {c.name: c for c in edgar.columns}
    p = {c.name: c for c in plain.columns}
    assert e["ticker"].role is ColumnRole.entity_id and p["ticker"].role is not ColumnRole.entity_id
    assert e["revenue"].semantic_type is SemanticType.monetary
    assert p["revenue"].semantic_type is SemanticType.real
    assert e["revenue"].unit == "USD" and p["revenue"].unit is None


def test_general_processing_modules_contain_no_domain_vocabulary() -> None:
    """Static guard: the generic data-processing layer names no dataset domain."""
    domain_tokens = ("ticker", "cik", "revenue", "net_margin", "net_income", "companyfacts", "edgar")
    for mod in ("profiling.py", "manifest_builder.py", "materialize.py"):
        text = (REPO / "agentic/adapters" / mod).read_text().lower()
        leaked = [t for t in domain_tokens if t in text]
        assert not leaked, f"{mod} leaks domain tokens: {leaked}"
