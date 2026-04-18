"""Shared execution service for persisted supported evaluation runs."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import EvaluationRunStatus
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
from edgar_project.evaluation.runner import EvaluationRunner
from edgar_project.evaluation.schemas import (
    BenchmarkSuite,
    EvaluationResult,
    EvaluationStatus,
    InputMode,
)
from edgar_project.evaluation.summary_report import summary_json_blob

_MAX_CASE_RUN_HISTORY = 5


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

        row.status = EvaluationRunStatus.running
        row.started_at = datetime.now(timezone.utc)
        row.finished_at = None
        self._runs.flush()

        try:
            runner = EvaluationRunner(suite=suite, allow_live_cases=allow_live)
            results = runner.run_suite()
            summary = runner.latest_summary
            if summary is None:  # pragma: no cover - defensive guard
                raise RuntimeError("evaluation runner did not populate latest_summary")

            row.summary_json = summary_json_blob(summary, results)
            row.results_json = {
                "suite_id": suite.suite_id,
                "case_count": len(results),
                "results": [result.model_dump(mode="json") for result in results],
            }
            self._case_results.replace_for_run(
                row.id,
                self._build_case_rows(row.id, suite=suite, results=results),
            )
            row.status = self._terminal_status(results)
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
            self._case_results.replace_for_run(row.id, [])
        row.finished_at = datetime.now(timezone.utc)
        self._runs.flush()
        return row

    @staticmethod
    def _terminal_status(results: list[EvaluationResult]) -> EvaluationRunStatus:
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

    @staticmethod
    def _build_case_rows(
        evaluation_run_id: UUID,
        *,
        suite: BenchmarkSuite,
        results: list[EvaluationResult],
    ) -> list[EvaluationCaseResult]:
        case_modes = {
            case.case_id: case.input.mode.value
            for case in suite.cases
        }
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

    def _enqueue_live_or_hybrid_case_run(
        self,
        evaluation_run: EvaluationRun,
        case_row: EvaluationCaseResult,
        case,
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
