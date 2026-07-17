"""
Experiment tool protocol and base class.

``ExperimentTool`` is the structural protocol every tool satisfies.
``BaseExperimentTool`` implements the shared scaffolding — parameter parsing,
capability validation, deterministic fingerprinting, structured failure — so a
concrete tool only declares a descriptor and implements ``_compute``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from agentic.domain.common import DomainModel
from agentic.domain.enums import ExperimentStatus
from agentic.domain.evidence import Evidence
from agentic.domain.manifest import DatasetManifest
from agentic.domain.observation import Observation
from agentic.domain.statistics import StatisticalSummary

from .artifacts import ArtifactRecord
from .capability import ExperimentValidationResult, ValidationIssue, check_capability
from .context import ExperimentContext
from .descriptor import ExperimentToolDescriptor
from .errors import ExperimentError, ExperimentExecutionError
from .fingerprint import input_fingerprint, output_fingerprint, params_fingerprint
from .record import ExperimentExecutionRecord


class NoParams(DomainModel):
    """Empty parameter model for tools that take no parameters."""


@dataclass
class ExperimentOutcome:
    """Transient result of a tool's deterministic computation."""

    observations: list[Observation] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    statistics: list[StatisticalSummary] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    diagnostics: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    status: ExperimentStatus = ExperimentStatus.succeeded


@runtime_checkable
class ExperimentTool(Protocol):
    """Structural contract for a deterministic experiment tool."""

    def descriptor(self) -> ExperimentToolDescriptor: ...

    def validate(self, *, params: dict, manifest: DatasetManifest) -> ExperimentValidationResult: ...

    def run(self, context: ExperimentContext) -> ExperimentExecutionRecord: ...


class BaseExperimentTool(ABC):
    """Shared scaffolding for deterministic experiment tools."""

    #: Parameter model (subclass of DomainModel); default: no parameters.
    params_model: type[BaseModel] = NoParams

    @abstractmethod
    def descriptor(self) -> ExperimentToolDescriptor:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.descriptor().name

    @property
    def version(self) -> str:
        return self.descriptor().version

    # -- validation ----------------------------------------------------------

    def validate(self, *, params: dict, manifest: DatasetManifest) -> ExperimentValidationResult:
        issues: list[ValidationIssue] = []
        parsed: BaseModel | None = None
        try:
            parsed = self.params_model.model_validate(params or {})
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err.get("loc", ())) or None
                issues.append(ValidationIssue(code="BAD_PARAMETER", message=err.get("msg", "invalid"), field=loc))
        desc = self.descriptor()
        issues.extend(check_capability(desc.required_capabilities, manifest))
        if parsed is not None:
            issues.extend(self._check_params_against_manifest(parsed, manifest))
        return ExperimentValidationResult(ok=not issues, issues=issues)

    def _check_params_against_manifest(self, params: BaseModel, manifest: DatasetManifest) -> list[ValidationIssue]:
        """Override to verify column params reference existing columns/roles."""
        return []

    # -- execution -----------------------------------------------------------

    def run(self, context: ExperimentContext) -> ExperimentExecutionRecord:
        desc = self.descriptor()
        provenance = context.tool_provenance(desc.name, desc.version)
        dataset_fp = context.manifest.fingerprint
        validation = self.validate(params=context.raw_params, manifest=context.manifest)
        if not validation.ok:
            detail = "; ".join(f"{i.code}:{i.message}" for i in validation.issues)
            return self._failed_record(context, provenance, dataset_fp, self._validation_error_info(detail))
        params = self.params_model.model_validate(context.raw_params or {})
        try:
            outcome = self._compute(context, params)
        except ExperimentError as exc:
            return self._failed_record(context, provenance, dataset_fp, exc.to_info())
        except Exception as exc:  # noqa: BLE001 - boundary: normalize to structured failure
            wrapped = ExperimentExecutionError(f"{desc.name} failed: {exc}", detail=f"{type(exc).__name__}: {exc}")
            return self._failed_record(context, provenance, dataset_fp, wrapped.to_info())

        params_dict = params.model_dump(mode="json")
        out_fp = output_fingerprint(
            observations=outcome.observations,
            evidence=outcome.evidence,
            metrics=outcome.metrics,
            artifacts=outcome.artifacts,
        )
        from agentic.domain.common import utc_now

        return ExperimentExecutionRecord(
            tool_name=desc.name,
            tool_version=desc.version,
            request_id=context.request_id,
            status=outcome.status,
            params=params_dict,
            dataset_fingerprint=dataset_fp,
            input_fingerprint=input_fingerprint(
                dataset_fingerprint=dataset_fp, tool_name=desc.name, tool_version=desc.version, params=params_dict
            ),
            output_fingerprint=out_fp,
            observations=outcome.observations,
            evidence=outcome.evidence,
            metrics=outcome.metrics,
            statistics=outcome.statistics,
            artifacts=outcome.artifacts,
            diagnostics=outcome.diagnostics,
            warnings=outcome.warnings,
            summary=outcome.summary,
            provenance=provenance,
            reproducibility=context.reproducibility or _default_reproducibility(desc),
            finished_at=utc_now(),
        )

    @staticmethod
    def _validation_error_info(detail: str):
        from .errors import ExperimentValidationError

        return ExperimentValidationError("experiment validation failed", detail=detail).to_info()

    def _failed_record(self, context, provenance, dataset_fp, error_info) -> ExperimentExecutionRecord:
        from agentic.domain.common import utc_now

        desc = self.descriptor()
        params_dict = context.raw_params if isinstance(context.raw_params, dict) else {}
        return ExperimentExecutionRecord(
            tool_name=desc.name,
            tool_version=desc.version,
            request_id=context.request_id,
            status=ExperimentStatus.failed,
            params=params_dict,
            dataset_fingerprint=dataset_fp,
            input_fingerprint=input_fingerprint(
                dataset_fingerprint=dataset_fp, tool_name=desc.name, tool_version=desc.version,
                params=_safe_params(params_dict),
            ),
            error=error_info,
            provenance=provenance,
            reproducibility=context.reproducibility or _default_reproducibility(desc),
            finished_at=utc_now(),
        )

    @abstractmethod
    def _compute(self, context: ExperimentContext, params: BaseModel) -> ExperimentOutcome:
        raise NotImplementedError


def _safe_params(params: dict) -> dict:
    try:
        params_fingerprint(params)
        return params
    except TypeError:
        return {}


def _default_reproducibility(desc: ExperimentToolDescriptor):
    from agentic.domain.provenance import ReproducibilityManifest

    return ReproducibilityManifest(tool_versions={desc.name: desc.version})
