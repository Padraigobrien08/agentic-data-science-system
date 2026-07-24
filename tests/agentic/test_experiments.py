"""
Tests for the deterministic experiment system.

Covers: registry lookup, capability validation, invalid-parameter rejection,
deterministic repeatability, structured failure, artifact generation, and EDGAR
experiment compatibility. All offline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, EDGARAdapter, InMemoryDatasetAdapter
from agentic.domain.enums import ColumnRole, ExperimentStatus
from agentic.experiments import (
    ExperimentContext,
    ExperimentToolDescriptor,
    InMemoryArtifactSink,
    UnknownExperimentError,
    build_default_registry,
)
from agentic.experiments.errors import ExperimentError

REPO = Path(__file__).resolve().parents[2]
EDGAR_FIXTURE = REPO / "edgar_project/evaluation/fixtures/data/01_simple_anomaly_features.csv"


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "period": ["2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4"] * 2,
            "x": [1.0, 2, 3, 4, 1, 2, 3, 4],
            "y": [2.0, 4.1, 5.9, 8.2, 1, 2, 3, 50],
            "grp": ["g1", "g1", "g2", "g2", "g1", "g1", "g2", "g2"],
        }
    )


def _manifest(df: pd.DataFrame | None = None):
    df = _panel() if df is None else df
    return InMemoryDatasetAdapter(
        frame=df, time_field="period", entity_id_fields=["entity"],
        role_hints={"x": ColumnRole.metric, "y": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


def _run(registry, tool: str, params: dict, *, frame=None, manifest=None):
    frame = _panel() if frame is None else frame
    manifest = _manifest(frame) if manifest is None else manifest
    ctx = ExperimentContext(manifest=manifest, frame=frame, raw_params=params, artifact_sink=InMemoryArtifactSink())
    return registry.get(tool).run(ctx)


@pytest.fixture(scope="module")
def registry():
    return build_default_registry()


# --- registry lookup --------------------------------------------------------


def test_registry_lookup(registry) -> None:
    names = registry.names()
    assert "profile_dataset" in names
    assert "edgar_peer_comparison" in names
    assert len(names) >= 16
    assert registry.has("detect_outliers")
    assert registry.get("detect_outliers").descriptor().name == "detect_outliers"


def test_registry_unknown_tool_is_structured(registry) -> None:
    with pytest.raises(UnknownExperimentError) as ei:
        registry.get("does_not_exist")
    assert ei.value.code == "UNKNOWN_EXPERIMENT"


def test_every_tool_declares_full_descriptor(registry) -> None:
    for desc in registry.descriptors():
        assert isinstance(desc, ExperimentToolDescriptor)
        assert desc.name and desc.version and desc.purpose
        assert desc.supported_input_modalities
        assert desc.required_capabilities is not None
        assert isinstance(desc.parameter_schema, dict)
        assert desc.deterministic is True
        assert isinstance(desc.artifact_types, list)
        # known_limitations declared for every tool
        assert isinstance(desc.known_limitations, list)


# --- capability validation --------------------------------------------------


def test_capability_validation_missing_metric(registry) -> None:
    # correlation needs >= 2 metric columns
    one_metric = InMemoryDatasetAdapter(
        frame=_panel()[["entity", "x"]], role_hints={"x": ColumnRole.metric}
    ).build_manifest(AdapterRequest())
    result = registry.get("analyze_correlation").validate(params={}, manifest=one_metric)
    assert not result.ok
    assert any(i.code == "INSUFFICIENT_METRICS" for i in result.issues)


def test_capability_validation_requires_temporal(registry) -> None:
    # a manifest with no time index fails a trend tool's temporal requirement
    no_time = InMemoryDatasetAdapter(
        frame=_panel()[["entity", "y"]], role_hints={"y": ColumnRole.metric}
    ).build_manifest(AdapterRequest())
    result = registry.get("analyze_time_series_trend").validate(params={"value_column": "y"}, manifest=no_time)
    assert not result.ok
    assert any(i.code in ("NO_TEMPORAL", "NO_TIME_COLUMN") for i in result.issues)


def test_capability_validation_passes_for_valid_manifest(registry) -> None:
    result = registry.get("summarize_distribution").validate(params={"column": "y"}, manifest=_manifest())
    assert result.ok
    assert result.issues == []


# --- invalid parameter rejection --------------------------------------------


def test_invalid_parameter_type_rejected(registry) -> None:
    result = registry.get("detect_outliers").validate(
        params={"column": "y", "threshold": "notanumber"}, manifest=_manifest()
    )
    assert not result.ok
    assert any(i.code == "BAD_PARAMETER" for i in result.issues)


def test_unknown_column_rejected(registry) -> None:
    result = registry.get("summarize_distribution").validate(params={"column": "nope"}, manifest=_manifest())
    assert not result.ok
    assert any(i.code == "UNKNOWN_COLUMN" for i in result.issues)


def test_missing_required_param_rejected(registry) -> None:
    result = registry.get("summarize_distribution").validate(params={}, manifest=_manifest())
    assert not result.ok


# --- structured failure -----------------------------------------------------


def test_run_with_invalid_params_returns_failed_record(registry) -> None:
    rec = _run(registry, "summarize_distribution", {"column": "does_not_exist"})
    assert rec.status is ExperimentStatus.failed
    assert rec.error is not None
    assert rec.error.code == "EXPERIMENT_VALIDATION"
    # a failed record still has identity + provenance
    assert rec.input_fingerprint
    assert rec.provenance.source.value == "deterministic_tool"


def test_experiment_error_is_structured() -> None:
    err = ExperimentError("boom", detail="d")
    info = err.to_info()
    assert info.code == "EXPERIMENT_ERROR"
    assert info.message == "boom"


# --- deterministic repeatability --------------------------------------------


@pytest.mark.parametrize(
    "tool,params",
    [
        ("profile_dataset", {}),
        ("summarize_distribution", {"column": "y"}),
        ("detect_outliers", {"column": "y", "method": "iqr", "threshold": 1.5}),
        ("analyze_correlation", {}),
        ("compare_groups", {"value_column": "y", "group_column": "grp"}),
        ("analyze_time_series_trend", {"value_column": "y"}),
        ("detect_change_points", {"value_column": "y"}),
        ("fit_simple_regression", {"x_column": "x", "y_column": "y"}),
        ("test_association", {"column_a": "entity", "column_b": "grp"}),
        ("rank_entities", {"metric_column": "y"}),
        ("generate_deterministic_chart", {"chart_type": "line", "x_column": "period", "y_column": "y"}),
    ],
)
def test_deterministic_repeatability(registry, tool, params) -> None:
    r1 = _run(registry, tool, params)
    r2 = _run(registry, tool, params)
    assert r1.status is ExperimentStatus.succeeded
    assert r1.output_fingerprint == r2.output_fingerprint
    assert r1.input_fingerprint == r2.input_fingerprint
    # metrics are byte-identical across runs
    assert r1.metrics == r2.metrics


def test_different_params_change_input_fingerprint(registry) -> None:
    a = _run(registry, "detect_outliers", {"column": "y", "threshold": 2.0})
    b = _run(registry, "detect_outliers", {"column": "y", "threshold": 3.0})
    assert a.input_fingerprint != b.input_fingerprint


# --- artifact generation ----------------------------------------------------


def test_artifacts_generated_and_addressed(registry) -> None:
    sink = InMemoryArtifactSink()
    ctx = ExperimentContext(manifest=_manifest(), frame=_panel(),
                            raw_params={"column": "y"}, artifact_sink=sink)
    rec = registry.get("summarize_distribution").run(ctx)
    assert rec.artifacts
    for art in rec.artifacts:
        assert art.fingerprint.startswith("sha256:")
        assert art.byte_size > 0
        assert art.id in sink.contents  # bytes were actually stored
    # identical run -> identical artifact fingerprints
    sink2 = InMemoryArtifactSink()
    ctx2 = ExperimentContext(manifest=_manifest(), frame=_panel(),
                             raw_params={"column": "y"}, artifact_sink=sink2)
    rec2 = registry.get("summarize_distribution").run(ctx2)
    assert [a.fingerprint for a in rec.artifacts] == [a.fingerprint for a in rec2.artifacts]


def test_statistical_output_fields_present(registry) -> None:
    rec = _run(registry, "fit_simple_regression", {"x_column": "x", "y_column": "y"})
    assert rec.statistics
    s = rec.statistics[0]
    assert s.sample_size is not None
    assert s.effect_size is not None and s.effect_size_kind == "r2"
    assert s.uncertainty is not None
    assert s.assumptions
    # evidence carries bounded strength derived from the statistics
    ev = rec.evidence[0]
    assert 0.0 <= ev.strength <= 1.0 and 0.0 <= ev.reliability <= 1.0 and 0.0 <= ev.coverage <= 1.0
    assert ev.statistics is not None


def test_record_maps_to_domain_result(registry) -> None:
    rec = _run(registry, "detect_outliers", {"column": "y", "method": "zscore", "threshold": 1.0})
    result = rec.to_domain_result()
    assert result.tool_name == "detect_outliers"
    assert result.produced_evidence_ids == [e.id for e in rec.evidence]
    assert result.artifact_ids == [a.id for a in rec.artifacts]
    # whole record round-trips as JSON
    from agentic.experiments import ExperimentExecutionRecord

    restored = ExperimentExecutionRecord.model_validate(rec.model_dump(mode="json"))
    assert restored.output_fingerprint == rec.output_fingerprint


# --- EDGAR experiment compatibility -----------------------------------------


def _edgar_ctx():
    frame = pd.read_csv(EDGAR_FIXTURE)
    manifest = EDGARAdapter().build_manifest(AdapterRequest(parameters={"panel_csv": str(EDGAR_FIXTURE)}))
    return frame, manifest


@pytest.mark.parametrize(
    "tool",
    ["edgar_peer_comparison", "edgar_trend_break_analysis",
     "edgar_revenue_growth_analysis", "edgar_margin_quality_analysis"],
)
def test_edgar_tools_run_on_fixture(registry, tool) -> None:
    frame, manifest = _edgar_ctx()
    ctx = ExperimentContext(manifest=manifest, frame=frame, raw_params={}, artifact_sink=InMemoryArtifactSink())
    rec = registry.get(tool).run(ctx)
    assert rec.status is ExperimentStatus.succeeded, rec.error
    assert rec.evidence  # produces at least one evidence record
    assert rec.artifacts  # wraps the deterministic output as an artifact
    assert rec.provenance.source.value == "deterministic_tool"


def test_edgar_tool_deterministic(registry) -> None:
    frame, manifest = _edgar_ctx()

    def once():
        ctx = ExperimentContext(manifest=manifest, frame=frame, raw_params={}, artifact_sink=InMemoryArtifactSink())
        return registry.get("edgar_revenue_growth_analysis").run(ctx)

    assert once().output_fingerprint == once().output_fingerprint


def test_edgar_tool_requires_edgar_columns(registry) -> None:
    # A generic manifest without the EDGAR feature column fails validation.
    frame = _panel()
    manifest = _manifest(frame)
    result = registry.get("edgar_margin_quality_analysis").validate(params={}, manifest=manifest)
    assert not result.ok
    assert any(i.code == "MISSING_EDGAR_COLUMN" for i in result.issues)
