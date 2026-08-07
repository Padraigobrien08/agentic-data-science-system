"""
The worked example from ``docs/extending.md``, executed.

Documentation that shows code nobody runs rots quietly: the API drifts and the guide keeps
claiming otherwise. This file *is* the guide's example, so if extending the platform stops
working the way the guide describes, the build fails.

Keep this in step with ``docs/extending.md``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pydantic import Field

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent import InMemoryInvestigationStore, InvestigationLoop
from agentic.domain.common import DomainModel
from agentic.domain.enums import ColumnRole, EvidenceDirection
from agentic.experiments import ExperimentRegistry, build_default_registry
from agentic.experiments.base import BaseExperimentTool, ExperimentOutcome
from agentic.experiments.capability import ExperimentCapability
from agentic.experiments.descriptor import ArtifactType, ExperimentToolDescriptor, OutputField
from agentic.experiments.errors import ParameterError
from agentic.experiments.tools._helpers import (
    ensure_columns,
    make_statistics,
    numeric_array,
    require_frame,
)

# --- Step 1: declare the parameters the tool accepts -------------------------


class CoefficientOfVariationParams(DomainModel):
    """Typed parameters. Validation failures become structured issues, not exceptions."""

    column: str = Field(..., min_length=1, description="Numeric column to measure.")


# --- Step 2: implement the tool ----------------------------------------------


class CoefficientOfVariationTool(BaseExperimentTool):
    """Relative variability (std / mean) — a volatility measure the registry does not ship.

    Deterministic: same frame in, same numbers out. No model call, no network.
    """

    params_model = CoefficientOfVariationParams

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="coefficient_of_variation",
            version="1.0",
            purpose="Relative variability of a numeric column (std / mean).",
            supported_input_modalities=["tabular", "time_series"],
            required_capabilities=ExperimentCapability(
                supported_modalities=["tabular", "time_series"],
                required_roles=[ColumnRole.metric],
                min_rows=2,
            ),
            parameter_schema=CoefficientOfVariationParams.model_json_schema(),
            output_schema=[OutputField(name="cv", kind="statistic", description="std / mean")],
            artifact_types=[ArtifactType.json],
            known_limitations=["Undefined when the mean is zero."],
        )

    def _check_params_against_manifest(self, params, manifest):
        return ensure_columns([params.column], manifest)

    def _compute(self, context, params) -> ExperimentOutcome:
        frame = require_frame(context)
        values = numeric_array(frame, params.column)
        finite = values[np.isfinite(values)]
        if finite.size < 2:
            raise ParameterError(f"column '{params.column}' has fewer than 2 numeric values")

        mean = float(np.mean(finite))
        if abs(mean) < 1e-12:
            raise ParameterError(f"coefficient of variation is undefined for a zero mean in '{params.column}'")
        cv = float(np.std(finite, ddof=1)) / abs(mean)

        artifact = context.artifact_sink.emit_json(
            "coefficient_of_variation", {"column": params.column, "cv": round(cv, 6)}
        )
        statistics = make_statistics(
            sample_size=int(finite.size), coverage=1.0,
            diagnostics={"cv": round(cv, 6), "mean": round(mean, 6)},
        )
        return ExperimentOutcome(
            summary=f"Coefficient of variation for '{params.column}' is {cv:.3f}.",
            metrics={"cv": round(cv, 6)},
            statistics=[statistics],
            artifacts=[artifact],
        )


# --- the guide's claims, verified --------------------------------------------


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "entity": ["A"] * 8,
        "period": [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(8)],
        "value": [10.0 + 2.0 * i for i in range(8)],
    })


def _manifest(frame: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=frame, time_field="period", entity_id_fields=["entity"],
        role_hints={"value": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


def _registry_with_example() -> ExperimentRegistry:
    registry = build_default_registry()
    registry.register(CoefficientOfVariationTool())
    return registry


def test_a_new_tool_registers_alongside_the_built_ins() -> None:
    registry = _registry_with_example()
    assert "coefficient_of_variation" in registry.names()
    # The built-ins are untouched.
    assert "analyze_time_series_trend" in registry.names()


def test_registering_a_duplicate_name_is_rejected() -> None:
    """Names are the tool's identity, so a collision is an error rather than a silent shadow."""
    registry = _registry_with_example()
    with pytest.raises(ValueError, match="already registered"):
        registry.register(CoefficientOfVariationTool())


def test_the_tool_validates_against_a_manifest_before_it_runs() -> None:
    registry = _registry_with_example()
    tool = registry.get("coefficient_of_variation")
    manifest = _manifest(_frame())

    assert tool.validate(params={"column": "value"}, manifest=manifest).ok
    # A column the dataset does not have is a structured issue, not a crash.
    assert not tool.validate(params={"column": "missing"}, manifest=manifest).ok
    assert not tool.validate(params={}, manifest=manifest).ok


def test_the_tool_computes_deterministically() -> None:
    from agentic.experiments import ExperimentContext, InMemoryArtifactSink

    frame = _frame()
    registry = _registry_with_example()

    def run_once():
        ctx = ExperimentContext(
            manifest=_manifest(frame), frame=frame, raw_params={"column": "value"},
            artifact_sink=InMemoryArtifactSink(), request_id="req-1",
        )
        return registry.get("coefficient_of_variation").run(ctx)

    first, second = run_once(), run_once()
    assert first.status is second.status
    assert first.metrics["cv"] == second.metrics["cv"]


def test_a_failed_parameter_is_reported_not_raised() -> None:
    """The failure model: a tool reports failure through its record, it does not raise."""
    from agentic.experiments import ExperimentContext, InMemoryArtifactSink

    frame = pd.DataFrame({"entity": ["A", "A"], "period": ["p1", "p2"], "value": [0.0, 0.0]})
    ctx = ExperimentContext(
        manifest=_manifest(frame), frame=frame, raw_params={"column": "value"},
        artifact_sink=InMemoryArtifactSink(), request_id="req-2",
    )
    record = _registry_with_example().get("coefficient_of_variation").run(ctx)
    assert record.status.value == "failed"
    assert record.error, "a failed record must carry the reason"
    assert "zero mean" in record.error.message


def test_a_custom_registry_drives_a_real_investigation() -> None:
    """The payoff: a loop built on the extended registry runs end to end."""
    frame = _frame()
    investigation = InvestigationLoop(registry=_registry_with_example()).start(
        "value is increasing over time", manifest=_manifest(frame), frame=frame,
        seed="extension-example", store=InMemoryInvestigationStore(),
    )
    assert investigation.is_terminal()
    assert investigation.state.completed_experiments


def test_evidence_direction_vocabulary_is_the_domain_enum() -> None:
    """A tool that emits evidence must use the typed direction, never a free string."""
    assert {d.value for d in EvidenceDirection} >= {"supports", "refutes", "neutral"}
