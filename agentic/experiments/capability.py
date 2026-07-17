"""
Experiment capability requirements and validation.

An :class:`ExperimentCapability` is what a tool *requires* of a dataset. It is
checked against a :class:`~agentic.domain.manifest.DatasetManifest` to produce an
:class:`ExperimentValidationResult`. Validation is deterministic and never calls
an LLM.
"""

from __future__ import annotations

from pydantic import Field

from agentic.domain.common import DomainModel
from agentic.domain.enums import ColumnRole, Modality
from agentic.domain.manifest import DatasetManifest


class ExperimentCapability(DomainModel):
    """Dataset requirements a tool declares in order to run."""

    supported_modalities: list[Modality] = Field(default_factory=lambda: [Modality.tabular])
    required_roles: list[ColumnRole] = Field(
        default_factory=list,
        description="Column roles that must be present at least once.",
    )
    min_rows: int = Field(default=1, ge=0)
    requires_temporal: bool = Field(default=False)
    requires_entity_id: bool = Field(default=False)
    min_metric_columns: int = Field(default=0, ge=0)


class ValidationIssue(DomainModel):
    """One structured validation problem."""

    code: str
    message: str
    field: str | None = Field(default=None)


class ExperimentValidationResult(DomainModel):
    """Outcome of validating a request against a tool's schema + capabilities."""

    ok: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            from .errors import ExperimentValidationError

            detail = "; ".join(f"{i.code}:{i.message}" for i in self.issues)
            raise ExperimentValidationError("experiment validation failed", detail=detail)


def check_capability(capability: ExperimentCapability, manifest: DatasetManifest) -> list[ValidationIssue]:
    """Deterministically check a manifest against a capability requirement."""
    issues: list[ValidationIssue] = []

    if capability.supported_modalities and manifest.modality not in capability.supported_modalities:
        issues.append(
            ValidationIssue(
                code="MODALITY_UNSUPPORTED",
                message=f"modality {manifest.modality.value} not in {[m.value for m in capability.supported_modalities]}",
            )
        )

    present_roles = {c.role for c in manifest.columns}
    for role in capability.required_roles:
        if role not in present_roles:
            issues.append(
                ValidationIssue(code="MISSING_ROLE", message=f"no column with role {role.value}", field=role.value)
            )

    if capability.min_metric_columns:
        n_metric = len(manifest.columns_with_role(ColumnRole.metric))
        if n_metric < capability.min_metric_columns:
            issues.append(
                ValidationIssue(
                    code="INSUFFICIENT_METRICS",
                    message=f"needs >= {capability.min_metric_columns} metric columns, found {n_metric}",
                )
            )

    if capability.requires_temporal:
        has_time = manifest.time_index_column() is not None or manifest.temporal_coverage is not None
        if not has_time:
            issues.append(ValidationIssue(code="NO_TEMPORAL", message="dataset has no time index / temporal coverage"))

    if capability.requires_entity_id and manifest.entity_id_column() is None:
        issues.append(ValidationIssue(code="NO_ENTITY_ID", message="dataset has no entity_id column"))

    # Row count is known only when data was materialized (row_count set).
    if manifest.row_count is not None and manifest.row_count < capability.min_rows:
        issues.append(
            ValidationIssue(
                code="TOO_FEW_ROWS",
                message=f"needs >= {capability.min_rows} rows, found {manifest.row_count}",
            )
        )

    return issues
