"""Tests for the input-adapter seam and the first-party EDGAR adapter.

These run fully offline: no SEC network access is required to build a manifest.
"""

from __future__ import annotations

import pytest

from agentic.adapters import (
    AdapterRegistry,
    AdapterRequest,
    EdgarInputAdapter,
    InputAdapter,
    build_default_registry,
    default_registry,
)
from agentic.domain.enums import ColumnRole, DatasetKind
from agentic.domain.manifest import DatasetManifest


def test_default_registry_has_edgar() -> None:
    reg = build_default_registry()
    assert "edgar" in reg.ids()
    assert isinstance(reg.get("edgar"), EdgarInputAdapter)
    assert reg.has("edgar")


def test_default_registry_is_shared_singleton() -> None:
    assert default_registry() is default_registry()


def test_registry_rejects_duplicate_and_unknown() -> None:
    reg = AdapterRegistry()
    reg.register(EdgarInputAdapter())
    with pytest.raises(ValueError):
        reg.register(EdgarInputAdapter())
    reg.register(EdgarInputAdapter(), replace=True)  # replace is allowed
    with pytest.raises(KeyError):
        reg.get("does-not-exist")


def test_edgar_adapter_is_input_adapter() -> None:
    adapter = EdgarInputAdapter()
    assert isinstance(adapter, InputAdapter)
    info = adapter.describe()
    assert info.adapter_id == "edgar"
    assert info.default_dataset_kind == DatasetKind.tabular_panel.value


def test_edgar_declared_manifest_uses_requested_entities_offline() -> None:
    adapter = EdgarInputAdapter()
    manifest = adapter.build_manifest(AdapterRequest(entities=["aapl", " msft "]))
    assert isinstance(manifest, DatasetManifest)
    assert manifest.entities == ["AAPL", "MSFT"]
    assert manifest.dataset_kind is DatasetKind.tabular_panel
    # identity + metric roles present
    assert manifest.entity_id_column().name == "ticker"
    assert manifest.time_index_column().name == "period"
    assert "revenue" in manifest.metric_names()
    assert manifest.row_count is None
    assert manifest.provenance.adapter_id == "edgar"


def test_edgar_declared_manifest_falls_back_to_default_tickers() -> None:
    manifest = EdgarInputAdapter().build_manifest(AdapterRequest())
    import config

    assert manifest.entities == [t.upper() for t in config.DEFAULT_TICKERS]


def test_edgar_manifest_from_panel_csv(tmp_path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text(
        "cik,period,revenue,net_margin\n"
        "1001,2023-Q1,100.0,0.12\n"
        "1001,2023-Q2,110.0,0.13\n"
        "1002,2023-Q1,50.0,0.20\n"
    )
    manifest = EdgarInputAdapter().build_manifest(
        AdapterRequest(parameters={"panel_csv": str(panel)})
    )
    assert manifest.row_count == 3
    by_name = {c.name: c for c in manifest.columns}
    assert by_name["cik"].role is ColumnRole.identifier
    assert by_name["period"].role is ColumnRole.time_index
    assert by_name["revenue"].role is ColumnRole.metric
    assert by_name["net_margin"].role is ColumnRole.metric
    assert manifest.provenance.parameters["panel_csv"] == str(panel)


def test_edgar_manifest_from_panel_csv_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        EdgarInputAdapter().build_manifest(
            AdapterRequest(parameters={"panel_csv": str(tmp_path / "nope.csv")})
        )
