"""DB-backed observability for supported evaluation dependency truth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.evaluation_case_result import EvaluationCaseResult

_UPSTREAM_SEC_ERROR_CODES = frozenset(
    {"sec_rate_limited", "sec_access_denied", "sec_unavailable", "upstream_unavailable"}
)
_STORAGE_ERROR_CODES = frozenset({"artifact_storage_unavailable"})


@dataclass(frozen=True, slots=True)
class EvaluationValidationObservabilityResult:
    """Shared evaluation dependency view for JSON and Prometheus surfaces."""

    state_known: bool
    sec_dependency_ok: bool | None
    storage_dependency_ok: bool | None
    recent_degraded_case_count: int | None
    detail: str | None


def get_evaluation_validation_observability(
    session: Session,
    *,
    lookback_hours: int = 24,
) -> EvaluationValidationObservabilityResult:
    """Inspect recent live or hybrid evaluation cases without masking DB failures."""

    try:
        case_rows = list(
            session.scalars(
                select(EvaluationCaseResult)
                .where(EvaluationCaseResult.input_mode.in_(("live", "hybrid")))
                .order_by(EvaluationCaseResult.updated_at.desc())
            ).all()
        )
    except SQLAlchemyError as exc:
        return EvaluationValidationObservabilityResult(
            state_known=False,
            sec_dependency_ok=None,
            storage_dependency_ok=None,
            recent_degraded_case_count=None,
            detail=str(exc),
        )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)
    recent_rows = [
        row
        for row in case_rows
        if _normalize_datetime(row.updated_at) >= cutoff
    ]
    if not recent_rows:
        return EvaluationValidationObservabilityResult(
            state_known=True,
            sec_dependency_ok=True,
            storage_dependency_ok=True,
            recent_degraded_case_count=0,
            detail="No recent live or hybrid evaluation cases within lookback window.",
        )

    sec_rows = [row for row in recent_rows if _row_indicates_sec_degradation(row)]
    storage_rows = [row for row in recent_rows if _row_indicates_storage_degradation(row)]
    recent_degraded_case_count = len(
        {
            row.id
            for row in [*sec_rows, *storage_rows]
        }
    )

    detail_parts: list[str] = []
    if sec_rows:
        detail_parts.append(
            f"SEC degradation seen in {len(sec_rows)} recent case(s)"
        )
    if storage_rows:
        detail_parts.append(
            f"storage degradation seen in {len(storage_rows)} recent case(s)"
        )
    if not detail_parts:
        detail_parts.append("No recent evaluation dependency degradation detected.")

    return EvaluationValidationObservabilityResult(
        state_known=True,
        sec_dependency_ok=not sec_rows,
        storage_dependency_ok=not storage_rows,
        recent_degraded_case_count=recent_degraded_case_count,
        detail="; ".join(detail_parts),
    )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _row_metadata(row: EvaluationCaseResult) -> dict[str, object]:
    if isinstance(row.metadata_json, dict):
        return row.metadata_json
    return {}


def _row_indicates_sec_degradation(row: EvaluationCaseResult) -> bool:
    metadata = _row_metadata(row)
    upstream_error_code = str(metadata.get("upstream_error_code") or "")
    return (
        row.degradation_class in {"upstream_sec_degraded", "stale_source"}
        or upstream_error_code in _UPSTREAM_SEC_ERROR_CODES
    )


def _row_indicates_storage_degradation(row: EvaluationCaseResult) -> bool:
    metadata = _row_metadata(row)
    storage_error_code = str(metadata.get("storage_error_code") or "")
    return storage_error_code in _STORAGE_ERROR_CODES
