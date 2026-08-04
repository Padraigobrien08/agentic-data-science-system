"""Shared execution service for persisted supported evaluation runs."""

from __future__ import annotations

import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, EvaluationRunStatus
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
from backend.repositories.evaluation_case_result_repository import (
    EvaluationCaseResultRepository,
)
from backend.repositories.evaluation_run_repository import EvaluationRunRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.run_queue_service import RunQueueService
from edgar_project.evaluation.catalog import (
    SupportedEvaluationSuite,
    get_supported_evaluation_suite,
)
from edgar_project.evaluation.runner import (
    EvaluationRunner,
    classify_degradation_class_for_case,
)
from edgar_project.evaluation.schemas import (
    BenchmarkCase,
    BenchmarkSuite,
    CaseFailureBrief,
    EvaluationResult,
    EvaluationStatus,
    EvaluationSummary,
    InputMode,
    ValidationDegradationClass,
    ValidationObservation,
    ValidationPolicy,
)
from edgar_project.evaluation.summary_report import failure_reason_short, summary_json_blob

_MAX_CASE_RUN_HISTORY = 5
_UPSTREAM_SEC_ERROR_CODES = frozenset(
    {"sec_rate_limited", "sec_access_denied", "sec_unavailable", "upstream_unavailable"}
)
_STORAGE_ERROR_CODES = frozenset({"artifact_storage_unavailable"})

# Free-text keys that legitimately carry error prose. The heuristics below read these
# rather than the whole serialized payload: a run's own data (figures, CIKs, ISO
# timestamps) must never be mistaken for an upstream failure signal.
_ERROR_TEXT_KEYS = frozenset({"error", "error_message", "message", "detail", "reason"})

# Ordered most-specific first. HTTP status codes are matched on word boundaries so a
# revenue of 4291000 or a microsecond field of .429183 cannot read as a 429.
_UPSTREAM_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"rate limit|\b429\b"), "sec_rate_limited"),
    (re.compile(r"access denied|forbidden|\b403\b"), "sec_access_denied"),
    (re.compile(r"sec unavailable|upstream unavailable"), "sec_unavailable"),
)
_STORAGE_TEXT_PATTERN = re.compile(
    r"artifact content not found in storage"
    r"|could not read artifact from storage"
    r"|storage_reconciliation"
    r"|artifact storage"
)


class EvaluationControlPlaneService:
    def __init__(
        self,
        session: Session,
        *,
        runs: EvaluationRunRepository | None = None,
        case_results: EvaluationCaseResultRepository | None = None,
        analysis_runs: AnalysisRunService | None = None,
        run_queue: RunQueueService | None = None,
        suite_lookup=get_supported_evaluation_suite,
    ) -> None:
        self._session = session
        self._runs = runs if runs is not None else EvaluationRunRepository(session)
        self._case_results = (
            case_results
            if case_results is not None
            else EvaluationCaseResultRepository(session)
        )
        self._analysis_runs = (
            analysis_runs if analysis_runs is not None else AnalysisRunService(session)
        )
        self._run_queue = run_queue if run_queue is not None else RunQueueService(session)
        self._suite_lookup = suite_lookup

    def count_case_results(self, evaluation_run_id: UUID) -> int:
        return self._case_results.count_for_run(evaluation_run_id)

    def start_evaluation_run(
        self,
        evaluation_run_id: UUID,
        *,
        allow_live: bool = False,
    ) -> EvaluationRun:
        row = self._runs.get_for_update(evaluation_run_id)
        if row is None:
            raise KeyError(f"Evaluation run not found: {evaluation_run_id}")

        suite_ref = self._suite_lookup(row.suite_id)
        suite = self._load_suite(row.id, suite_ref)
        live_or_hybrid_cases = [
            case
            for case in suite.cases
            if case.input.mode in {InputMode.live, InputMode.hybrid}
        ]

        if not live_or_hybrid_cases:
            return self._start_synchronous_suite_run(
                row,
                suite=suite,
                allow_live=allow_live,
            )

        row.status = EvaluationRunStatus.running
        row.started_at = datetime.now(timezone.utc)
        row.finished_at = None
        self._runs.flush()

        try:
            sync_cases = [
                case
                for case in suite.cases
                if case.input.mode not in {InputMode.live, InputMode.hybrid}
            ]
            sync_results = self._run_synchronous_case_subset(
                suite=suite,
                cases=sync_cases,
                allow_live=allow_live,
            )
            sync_rows = self._build_case_rows(row.id, suite=suite, results=sync_results)
            pending_rows = [
                self._build_pending_case_row(row.id, case)
                for case in live_or_hybrid_cases
            ]
            all_rows = [*sync_rows, *pending_rows]
            self._case_results.replace_for_run(row.id, all_rows)

            pending_rows_by_case_id = {
                case_row.case_id: case_row
                for case_row in pending_rows
            }
            for case in live_or_hybrid_cases:
                self._enqueue_live_or_hybrid_case_run(
                    row,
                    pending_rows_by_case_id[case.case_id],
                    case,
                )

            self._persist_run_snapshot(
                row,
                suite=suite,
                results=self._case_rows_to_results(
                    suite=suite,
                    case_rows=all_rows,
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive wrapper
            row.status = EvaluationRunStatus.error
            row.summary_json = {
                "suite_id": row.suite_id,
                "error": f"{type(exc).__name__}: {exc}",
            }
            row.results_json = {
                "suite_id": row.suite_id,
                "case_count": 0,
                "results": [],
            }
            row.finished_at = datetime.now(timezone.utc)
            self._case_results.replace_for_run(row.id, [])
        self._runs.flush()
        return row

    def refresh_linked_case_results(self, evaluation_run_id: UUID) -> EvaluationRun:
        row = self._runs.get_for_update(evaluation_run_id)
        if row is None:
            raise KeyError(f"Evaluation run not found: {evaluation_run_id}")

        suite_ref = self._suite_lookup(row.suite_id)
        suite = self._load_suite(row.id, suite_ref)
        cases_by_id = {case.case_id: case for case in suite.cases}
        case_rows = self._case_results.list_for_run(row.id)

        for case_row in case_rows:
            case = cases_by_id.get(case_row.case_id)
            if case is None or case_row.latest_analysis_run_id is None:
                continue
            child_run = self._analysis_runs.get(case_row.latest_analysis_run_id)
            if child_run is None:
                continue
            self._reconcile_case_row_from_analysis_run(
                case_row,
                case=case,
                child_run=child_run,
            )

        if case_rows:
            self._persist_run_snapshot(
                row,
                suite=suite,
                results=self._case_rows_to_results(suite=suite, case_rows=case_rows),
            )
        self._runs.flush()
        return row

    @staticmethod
    def _terminal_status(results: list[EvaluationResult]) -> EvaluationRunStatus:
        if any(result.status == EvaluationStatus.pending for result in results):
            return EvaluationRunStatus.running
        if any(result.status == EvaluationStatus.error for result in results):
            return EvaluationRunStatus.error
        if any(result.status == EvaluationStatus.failed for result in results):
            return EvaluationRunStatus.failed
        if results and all(result.status == EvaluationStatus.skipped for result in results):
            return EvaluationRunStatus.skipped
        return EvaluationRunStatus.passed

    def _load_suite(
        self,
        evaluation_run_id: UUID,
        suite_ref: SupportedEvaluationSuite,
    ) -> BenchmarkSuite:
        suite = BenchmarkSuite.model_validate_json(
            suite_ref.manifest_path.read_text(encoding="utf-8")
        )
        output_root = Path(tempfile.gettempdir()) / "edgar-evaluation-control-plane"
        output_root.mkdir(parents=True, exist_ok=True)
        output_dir = Path(
            tempfile.mkdtemp(
                prefix=f"{suite_ref.suite_id}-{str(evaluation_run_id)[:8]}-",
                dir=output_root,
            )
        )
        return suite.model_copy(
            update={"output_dir": str(output_dir.resolve())},
            deep=True,
        )

    def _start_synchronous_suite_run(
        self,
        row: EvaluationRun,
        *,
        suite: BenchmarkSuite,
        allow_live: bool,
    ) -> EvaluationRun:
        row.status = EvaluationRunStatus.running
        row.started_at = datetime.now(timezone.utc)
        row.finished_at = None
        self._runs.flush()

        try:
            runner = EvaluationRunner(suite=suite, allow_live_cases=allow_live)
            results = runner.run_suite()
            self._case_results.replace_for_run(
                row.id,
                self._build_case_rows(row.id, suite=suite, results=results),
            )
            self._persist_run_snapshot(row, suite=suite, results=results)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            row.status = EvaluationRunStatus.error
            row.summary_json = {
                "suite_id": row.suite_id,
                "error": f"{type(exc).__name__}: {exc}",
            }
            row.results_json = {
                "suite_id": row.suite_id,
                "case_count": 0,
                "results": [],
            }
            row.finished_at = datetime.now(timezone.utc)
            self._case_results.replace_for_run(row.id, [])
        self._runs.flush()
        return row

    def _run_synchronous_case_subset(
        self,
        *,
        suite: BenchmarkSuite,
        cases: list[BenchmarkCase],
        allow_live: bool,
    ) -> list[EvaluationResult]:
        if not cases:
            return []
        subset = suite.model_copy(update={"cases": cases}, deep=True)
        return EvaluationRunner(
            suite=subset,
            allow_live_cases=allow_live,
        ).run_suite()

    @staticmethod
    def _build_case_rows(
        evaluation_run_id: UUID,
        *,
        suite: BenchmarkSuite,
        results: list[EvaluationResult],
    ) -> list[EvaluationCaseResult]:
        case_modes = {case.case_id: case.input.mode.value for case in suite.cases}
        rows: list[EvaluationCaseResult] = []
        for result in results:
            input_mode = str(
                result.metadata.get("input_mode")
                or case_modes.get(result.case_id, InputMode.fixture.value)
            )
            rows.append(
                EvaluationCaseResult(
                    evaluation_run_id=evaluation_run_id,
                    case_id=result.case_id,
                    input_mode=input_mode,
                    status=result.status.value,
                    degradation_class=result.degradation_class.value,
                    run_goal=result.run_goal,
                    message=result.message,
                    policy_json=(
                        result.policy.model_dump(mode="json")
                        if result.policy is not None
                        else None
                    ),
                    observation_json=(
                        result.observation.model_dump(mode="json")
                        if result.observation is not None
                        else None
                    ),
                    checks_json=result.checks,
                    metadata_json=result.metadata,
                    artifacts_json=result.artifacts,
                )
            )
        return rows

    @staticmethod
    def _build_pending_case_row(
        evaluation_run_id: UUID,
        case: BenchmarkCase,
    ) -> EvaluationCaseResult:
        observation_json = None
        if case.input.policy is not None:
            observation_json = ValidationObservation(
                freshness_window_seconds=case.input.policy.freshness_window_seconds,
            ).model_dump(mode="json")
        return EvaluationCaseResult(
            evaluation_run_id=evaluation_run_id,
            case_id=case.case_id,
            input_mode=case.input.mode.value,
            status=EvaluationStatus.pending.value,
            degradation_class=ValidationDegradationClass.none.value,
            run_goal=case.input.goal,
            message="queued canonical child analysis run",
            policy_json=(
                case.input.policy.model_dump(mode="json")
                if case.input.policy is not None
                else None
            ),
            observation_json=observation_json,
            checks_json={},
            metadata_json={
                "input_mode": case.input.mode.value,
                "tickers": list(case.input.tickers),
                "refresh": case.input.refresh,
                "fixture_id": case.input.fixture_id,
                "tags": list(case.tags),
            },
            artifacts_json={},
        )

    def _enqueue_live_or_hybrid_case_run(
        self,
        evaluation_run: EvaluationRun,
        case_row: EvaluationCaseResult,
        case: BenchmarkCase,
        *,
        trace_carrier: dict[str, str] | None = None,
    ) -> UUID:
        if evaluation_run.project_id is None:
            raise ValueError("Evaluation run must be project-scoped before child runs can be enqueued")

        input_payload_json = {
            "tickers": list(case.input.tickers),
            "analysis_goal": case.input.goal,
            "refresh": case.input.refresh,
        }
        meta_json = {
            "evaluation_case_link": {
                "evaluation_run_id": str(evaluation_run.id),
                "case_id": case.case_id,
                "suite_id": evaluation_run.suite_id,
                "input_mode": case.input.mode.value,
            }
        }
        child_run = self._analysis_runs.create(
            evaluation_run.project_id,
            initiated_by_user_id=evaluation_run.initiated_by_user_id,
            orchestration_goal_text=case.input.goal,
            input_payload_json=input_payload_json,
            meta_json=meta_json,
        )
        self._run_queue.enqueue_after_create(
            child_run.id,
            input_payload_json,
            trace_carrier=trace_carrier,
        )
        self._case_results.update_linked_analysis_run(
            case_row,
            latest_analysis_run_id=child_run.id,
            latest_analysis_run_status="queued",
            history_item={
                "analysis_run_id": str(child_run.id),
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            max_history_entries=_MAX_CASE_RUN_HISTORY,
        )
        return child_run.id

    def _persist_run_snapshot(
        self,
        row: EvaluationRun,
        *,
        suite: BenchmarkSuite,
        results: list[EvaluationResult],
    ) -> None:
        summary = self._build_summary(results=results, suite_id=suite.suite_id)
        summary_payload = summary_json_blob(summary, results)
        summary_payload["pending_cases"] = sum(
            1 for result in results if result.status == EvaluationStatus.pending
        )
        row.summary_json = summary_payload
        row.results_json = {
            "suite_id": suite.suite_id,
            "case_count": len(results),
            "results": [result.model_dump(mode="json") for result in results],
        }
        row.status = self._terminal_status(results)
        if row.status == EvaluationRunStatus.running:
            row.finished_at = None
        else:
            row.finished_at = datetime.now(timezone.utc)

    @staticmethod
    def _build_summary(
        *,
        results: list[EvaluationResult],
        suite_id: str,
    ) -> EvaluationSummary:
        total_elapsed = round(sum((result.elapsed_seconds or 0.0) for result in results), 6)
        return EvaluationSummary(
            suite_id=suite_id,
            total_cases=len(results),
            passed_cases=sum(1 for result in results if result.status == EvaluationStatus.passed),
            failed_cases=sum(1 for result in results if result.status == EvaluationStatus.failed),
            skipped_cases=sum(1 for result in results if result.status == EvaluationStatus.skipped),
            error_cases=sum(1 for result in results if result.status == EvaluationStatus.error),
            total_elapsed_seconds=total_elapsed,
            failed_case_briefs=[
                CaseFailureBrief(
                    case_id=result.case_id,
                    status=result.status.value,
                    reason_short=failure_reason_short(result.message),
                )
                for result in results
                if result.status in {EvaluationStatus.failed, EvaluationStatus.error}
            ],
            generated_at=datetime.now(timezone.utc).isoformat(),
            notes="supported evaluation control-plane run",
        )

    def _case_rows_to_results(
        self,
        *,
        suite: BenchmarkSuite,
        case_rows: list[EvaluationCaseResult],
    ) -> list[EvaluationResult]:
        rows_by_case_id = {row.case_id: row for row in case_rows}
        results: list[EvaluationResult] = []
        for case in suite.cases:
            case_row = rows_by_case_id.get(case.case_id)
            if case_row is None:
                continue
            results.append(self._case_row_to_result(case_row, case=case))
        return results

    def _case_row_to_result(
        self,
        case_row: EvaluationCaseResult,
        *,
        case: BenchmarkCase,
    ) -> EvaluationResult:
        return EvaluationResult(
            case_id=case_row.case_id,
            status=EvaluationStatus(case_row.status),
            degradation_class=ValidationDegradationClass(case_row.degradation_class),
            message=case_row.message,
            run_goal=case_row.run_goal,
            artifacts=(
                dict(case_row.artifacts_json)
                if isinstance(case_row.artifacts_json, dict)
                else {}
            ),
            checks=(
                {
                    str(key): bool(value)
                    for key, value in case_row.checks_json.items()
                }
                if isinstance(case_row.checks_json, dict)
                else {}
            ),
            policy=(
                ValidationPolicy.model_validate(case_row.policy_json)
                if isinstance(case_row.policy_json, dict)
                else case.input.policy
            ),
            observation=(
                ValidationObservation.model_validate(case_row.observation_json)
                if isinstance(case_row.observation_json, dict)
                else None
            ),
            metadata=(
                dict(case_row.metadata_json)
                if isinstance(case_row.metadata_json, dict)
                else {}
            ),
        )

    def _reconcile_case_row_from_analysis_run(
        self,
        case_row: EvaluationCaseResult,
        *,
        case: BenchmarkCase,
        child_run: AnalysisRun,
    ) -> None:
        result = self._build_result_from_analysis_run(
            case_row,
            case=case,
            child_run=child_run,
        )
        case_row.status = result.status.value
        case_row.degradation_class = result.degradation_class.value
        case_row.message = result.message
        case_row.observation_json = (
            result.observation.model_dump(mode="json")
            if result.observation is not None
            else None
        )
        case_row.metadata_json = result.metadata
        case_row.latest_analysis_run_status = child_run.status.value
        self._sync_analysis_run_history(case_row, child_run)

    def _build_result_from_analysis_run(
        self,
        case_row: EvaluationCaseResult,
        *,
        case: BenchmarkCase,
        child_run: AnalysisRun,
    ) -> EvaluationResult:
        metadata = self._build_metadata_from_analysis_run(
            case_row,
            child_run=child_run,
            case=case,
        )
        observation = self._build_observation_from_analysis_run(
            child_run=child_run,
            case=case,
            case_row=case_row,
        )
        result = EvaluationResult(
            case_id=case.case_id,
            status=self._case_status_for_analysis_run(child_run.status),
            message=self._message_for_analysis_run(child_run),
            run_goal=case_row.run_goal,
            artifacts=(
                dict(case_row.artifacts_json)
                if isinstance(case_row.artifacts_json, dict)
                else {}
            ),
            checks=(
                {
                    str(key): bool(value)
                    for key, value in case_row.checks_json.items()
                }
                if isinstance(case_row.checks_json, dict)
                else {}
            ),
            policy=case.input.policy,
            observation=observation,
            metadata=metadata,
        )
        if child_run.started_at is not None and child_run.finished_at is not None:
            result.elapsed_seconds = round(
                (child_run.finished_at - child_run.started_at).total_seconds(),
                6,
            )
        result.degradation_class = classify_degradation_class_for_case(
            case,
            result,
            allow_live_cases=True,
        )
        return result

    @staticmethod
    def _case_status_for_analysis_run(
        analysis_run_status: AnalysisRunStatus,
    ) -> EvaluationStatus:
        if analysis_run_status in {
            AnalysisRunStatus.pending,
            AnalysisRunStatus.queued,
            AnalysisRunStatus.running,
        }:
            return EvaluationStatus.pending
        if analysis_run_status == AnalysisRunStatus.success:
            return EvaluationStatus.passed
        if analysis_run_status in {
            AnalysisRunStatus.partial_success,
            AnalysisRunStatus.no_data,
        }:
            return EvaluationStatus.failed
        return EvaluationStatus.error

    @staticmethod
    def _message_for_analysis_run(child_run: AnalysisRun) -> str:
        if child_run.status in {
            AnalysisRunStatus.pending,
            AnalysisRunStatus.queued,
            AnalysisRunStatus.running,
        }:
            return f"awaiting linked analysis run ({child_run.status.value})"
        if child_run.error_summary:
            return child_run.error_summary
        if child_run.status == AnalysisRunStatus.success:
            return "passed via linked analysis run"
        return f"linked analysis run ended with status {child_run.status.value}"

    def _build_metadata_from_analysis_run(
        self,
        case_row: EvaluationCaseResult,
        *,
        child_run: AnalysisRun,
        case: BenchmarkCase,
    ) -> dict[str, object]:
        metadata = (
            dict(case_row.metadata_json)
            if isinstance(case_row.metadata_json, dict)
            else {}
        )
        metadata["input_mode"] = case.input.mode.value
        metadata["tickers"] = list(case.input.tickers)
        metadata["refresh"] = case.input.refresh
        metadata["analysis_run_id"] = str(child_run.id)
        metadata["analysis_run_status"] = child_run.status.value
        if child_run.error_summary:
            metadata["analysis_run_error_summary"] = child_run.error_summary

        upstream_error_code = self._extract_upstream_error_code(child_run)
        if upstream_error_code is not None:
            metadata["upstream_error_code"] = upstream_error_code
        else:
            metadata.pop("upstream_error_code", None)

        storage_error_code = self._extract_storage_error_code(child_run)
        if storage_error_code is not None:
            metadata["storage_error_code"] = storage_error_code
        else:
            metadata.pop("storage_error_code", None)

        return metadata

    def _build_observation_from_analysis_run(
        self,
        *,
        child_run: AnalysisRun,
        case: BenchmarkCase,
        case_row: EvaluationCaseResult,
    ) -> ValidationObservation | None:
        observation_payload = (
            dict(case_row.observation_json)
            if isinstance(case_row.observation_json, dict)
            else {}
        )
        if (
            case.input.policy is not None
            and case.input.policy.freshness_window_seconds is not None
        ):
            observation_payload["freshness_window_seconds"] = (
                case.input.policy.freshness_window_seconds
            )

        observed_at = child_run.finished_at or child_run.updated_at
        if observed_at is not None:
            observation_payload["observed_at"] = observed_at

        source_observed_at = self._coerce_datetime(
            self._find_first_nested_value(
                child_run.output_payload_json,
                keys={"source_observed_at"},
            )
            or self._find_first_nested_value(
                child_run.meta_json,
                keys={"source_observed_at"},
            )
        )
        if source_observed_at is not None:
            observation_payload["source_observed_at"] = source_observed_at

        source_age_seconds = self._coerce_float(
            self._find_first_nested_value(
                child_run.output_payload_json,
                keys={"source_age_seconds"},
            )
            or self._find_first_nested_value(
                child_run.meta_json,
                keys={"source_age_seconds"},
            )
        )
        if source_age_seconds is None and observed_at is not None and source_observed_at is not None:
            source_age_seconds = max(
                0.0,
                (observed_at - source_observed_at).total_seconds(),
            )
        if source_age_seconds is not None:
            observation_payload["source_age_seconds"] = source_age_seconds

        if not observation_payload:
            return None
        return ValidationObservation.model_validate(observation_payload)

    @staticmethod
    def _find_first_nested_value(
        payload: object,
        *,
        keys: set[str],
    ) -> object | None:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in keys and value not in {None, ""}:
                    return value
                nested = EvaluationControlPlaneService._find_first_nested_value(
                    value,
                    keys=keys,
                )
                if nested is not None:
                    return nested
        if isinstance(payload, list):
            for item in payload:
                nested = EvaluationControlPlaneService._find_first_nested_value(
                    item,
                    keys=keys,
                )
                if nested is not None:
                    return nested
        return None

    @staticmethod
    def _coerce_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        candidate = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _extract_upstream_error_code(self, child_run: AnalysisRun) -> str | None:
        explicit = self._find_first_nested_value(
            child_run.output_payload_json,
            keys={"upstream_error_code"},
        ) or self._find_first_nested_value(
            child_run.meta_json,
            keys={"upstream_error_code"},
        )
        if isinstance(explicit, str) and explicit in _UPSTREAM_SEC_ERROR_CODES:
            return explicit

        error_text = self._error_prose(child_run)
        for pattern, code in _UPSTREAM_TEXT_PATTERNS:
            if pattern.search(error_text):
                return code
        return None

    def _extract_storage_error_code(self, child_run: AnalysisRun) -> str | None:
        explicit = self._find_first_nested_value(
            child_run.output_payload_json,
            keys={"storage_error_code"},
        ) or self._find_first_nested_value(
            child_run.meta_json,
            keys={"storage_error_code"},
        )
        if isinstance(explicit, str) and explicit in _STORAGE_ERROR_CODES:
            return explicit

        if _STORAGE_TEXT_PATTERN.search(self._error_prose(child_run)):
            return "artifact_storage_unavailable"
        return None

    def _error_prose(self, child_run: AnalysisRun) -> str:
        """Lower-cased error prose for a run: the summary plus any nested error message.

        Deliberately excludes the raw ``meta_json`` / ``output_payload_json`` blobs.
        Scanning those meant a successful run's own values could trip a failure
        heuristic — a figure like 4291000, a CIK, or an ISO timestamp whose
        microseconds happened to contain 429 all read as an HTTP 429, which
        misclassified healthy runs as upstream-degraded (and made the evaluation
        tests fail depending on the wall-clock time they ran at).
        """
        parts = [child_run.error_summary or ""]
        for source in (child_run.meta_json, child_run.output_payload_json):
            value = self._find_first_nested_value(source, keys=_ERROR_TEXT_KEYS)
            if isinstance(value, str):
                parts.append(value)
        return " ".join(parts).lower()

    @staticmethod
    def _sync_analysis_run_history(
        case_row: EvaluationCaseResult,
        child_run: AnalysisRun,
    ) -> None:
        history = (
            [item for item in case_row.analysis_run_history_json if isinstance(item, dict)]
            if isinstance(case_row.analysis_run_history_json, list)
            else []
        )
        now = datetime.now(timezone.utc).isoformat()
        for index in range(len(history) - 1, -1, -1):
            item = history[index]
            if item.get("analysis_run_id") != str(child_run.id):
                continue
            updated = dict(item)
            updated["status"] = child_run.status.value
            updated["updated_at"] = now
            if child_run.finished_at is not None:
                updated["finished_at"] = child_run.finished_at.isoformat()
            history[index] = updated
            case_row.analysis_run_history_json = history[-_MAX_CASE_RUN_HISTORY:]
            return
        history.append(
            {
                "analysis_run_id": str(child_run.id),
                "status": child_run.status.value,
                "updated_at": now,
                "finished_at": (
                    child_run.finished_at.isoformat()
                    if child_run.finished_at is not None
                    else None
                ),
            }
        )
        case_row.analysis_run_history_json = history[-_MAX_CASE_RUN_HISTORY:]
