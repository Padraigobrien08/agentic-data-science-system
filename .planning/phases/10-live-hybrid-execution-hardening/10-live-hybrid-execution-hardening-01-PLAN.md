---
phase: 10-live-hybrid-execution-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/013_live_hybrid_evaluation_case_run_links.py
  - backend/models/evaluation_case_result.py
  - backend/schemas/evaluation_case_result.py
  - backend/schemas/evaluation_run.py
  - backend/repositories/evaluation_case_result_repository.py
  - backend/services/evaluation_control_plane_service.py
  - tests/test_evaluation_live_hybrid_execution.py
  - tests/test_evaluation_control_plane_api.py
autonomous: true
requirements:
  - EVAL-02
must_haves:
  truths:
    - "Live and hybrid evaluation cases persist a direct latest child `AnalysisRun` pointer plus bounded prior child-run history instead of one opaque execution-log blob."
    - "The control plane can mint canonical child analysis runs with evaluation linkage metadata and enqueue them through the existing queue service."
    - "Case rows remain the evaluation-side resource, while `AnalysisRun` stays the execution-side source of truth."
  artifacts:
    - path: alembic/versions/013_live_hybrid_evaluation_case_run_links.py
      provides: "Persistence contract for latest child-run pointer and bounded prior history on evaluation case rows"
    - path: backend/services/evaluation_control_plane_service.py
      provides: "Helper that creates and enqueues canonical child runs for live or hybrid cases"
    - path: tests/test_evaluation_live_hybrid_execution.py
      provides: "Regression coverage for case-run linkage and queue-backed child-run creation"
  key_links:
    - from: backend/services/evaluation_control_plane_service.py
      to: backend/services/run_queue_service.py
      via: "live or hybrid evaluation cases are launched through the canonical queue path rather than inline execution"
      pattern: "RunQueueService|enqueue_after_create|evaluation_case_link"
    - from: backend/models/evaluation_case_result.py
      to: backend/models/analysis_run.py
      via: "case rows persist the latest linked child run and a bounded prior run history"
      pattern: "latest_analysis_run_id|latest_analysis_run_status|analysis_run_history_json"
    - from: tests/test_evaluation_live_hybrid_execution.py
      to: backend/services/evaluation_control_plane_service.py
      via: "tests lock the latest-child-run pointer, bounded history, and queued child-run behavior"
      pattern: "latest_analysis_run_id|analysis_run_history_json|RunExecutionJobStatus.pending"
---

<objective>
Add the child-run linkage contract for live and hybrid evaluation cases and the control-plane helper that creates canonical queued child `AnalysisRun` rows.

Purpose: establish the persistence and queue foundation before Phase 10 converts evaluation starts or ops reporting.
Output: case-result linkage fields, queue-backed child-run creation helper, and regression tests for the new contract.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
@.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
@.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
@backend/models/evaluation_case_result.py
@backend/schemas/evaluation_case_result.py
@backend/services/evaluation_control_plane_service.py
@backend/services/run_queue_service.py
@backend/services/analysis_run_service.py
@backend/models/analysis_run.py
@backend/schemas/analysis_run.py

<interfaces>
From `backend/models/evaluation_case_result.py`:
```python
class EvaluationCaseResult(Base):
    evaluation_run_id: Mapped[uuid.UUID]
    case_id: Mapped[str]
    status: Mapped[str]
    degradation_class: Mapped[str]
```

From `backend/services/run_queue_service.py`:
```python
def enqueue_after_create(
    self,
    analysis_run_id: UUID,
    overrides: dict[str, Any] | None,
    *,
    trace_carrier: dict[str, str] | None = None,
) -> None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend evaluation case rows with latest child-run pointers and bounded history</name>
  <files>alembic/versions/013_live_hybrid_evaluation_case_run_links.py
backend/models/evaluation_case_result.py
backend/schemas/evaluation_case_result.py
backend/schemas/evaluation_run.py
backend/repositories/evaluation_case_result_repository.py
tests/test_evaluation_live_hybrid_execution.py
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
backend/models/evaluation_case_result.py
backend/schemas/evaluation_case_result.py
backend/schemas/evaluation_run.py
backend/models/analysis_run.py
backend/repositories/evaluation_case_result_repository.py</read_first>
  <behavior>
    - Each persisted live or hybrid case row exposes a direct latest child-run pointer and bounded prior child-run history.
    - The evaluation API can serialize those run links without inventing a second execution resource.
    - The new linkage fields remain nullable so existing fixture-only evaluation history continues to load cleanly.
  </behavior>
  <action>Create `alembic/versions/013_live_hybrid_evaluation_case_run_links.py` that adds nullable columns `latest_analysis_run_id` (`Uuid`, foreign key to `analysis_runs.id` with `ondelete="SET NULL"`), `latest_analysis_run_status` (`String(64)`), and `analysis_run_history_json` (`JSON`) to `evaluation_case_results`. Update `backend/models/evaluation_case_result.py` with matching mapped columns, keeping the existing case-result fields unchanged. Extend `backend/schemas/evaluation_case_result.py` so `EvaluationCaseResultRead` includes `latest_analysis_run_id: UUID | None = None`, `latest_analysis_run_status: str | None = None`, and `analysis_run_history_json: dict | list | None = None`. Extend `backend/schemas/evaluation_run.py` only as needed to surface linked-run counts or other summary fields without forcing clients to parse `results_json`. Add repository helpers in `backend/repositories/evaluation_case_result_repository.py` that can persist those linkage fields without deleting and recreating the case row. Seed `tests/test_evaluation_live_hybrid_execution.py` and `tests/test_evaluation_control_plane_api.py` with assertions that linked-run fields serialize as nullable on fixture rows and become populated for live or hybrid rows.</action>
  <acceptance_criteria>`alembic/versions/013_live_hybrid_evaluation_case_run_links.py` exists.
`alembic/versions/013_live_hybrid_evaluation_case_run_links.py` contains `latest_analysis_run_id`.
`alembic/versions/013_live_hybrid_evaluation_case_run_links.py` contains `latest_analysis_run_status`.
`alembic/versions/013_live_hybrid_evaluation_case_run_links.py` contains `analysis_run_history_json`.
`backend/models/evaluation_case_result.py` contains `latest_analysis_run_id`.
`backend/models/evaluation_case_result.py` contains `latest_analysis_run_status`.
`backend/models/evaluation_case_result.py` contains `analysis_run_history_json`.
`backend/schemas/evaluation_case_result.py` contains `latest_analysis_run_id`.
`backend/schemas/evaluation_case_result.py` contains `analysis_run_history_json`.
`backend/repositories/evaluation_case_result_repository.py` contains `update_linked_analysis_run` or another helper with `latest_analysis_run_id`.
`tests/test_evaluation_live_hybrid_execution.py` exists.
`tests/test_evaluation_live_hybrid_execution.py` contains `latest_analysis_run_id`.
`tests/test_evaluation_control_plane_api.py` contains `analysis_run_history_json`.
`python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>Evaluation case rows now have a first-class persistence contract for latest child-run navigation and bounded history.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add a queue-backed helper that mints canonical child runs for live or hybrid cases</name>
  <files>backend/services/evaluation_control_plane_service.py
tests/test_evaluation_live_hybrid_execution.py
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
backend/services/evaluation_control_plane_service.py
backend/services/analysis_run_service.py
backend/services/run_queue_service.py
backend/schemas/analysis_run.py
backend/models/analysis_run.py
tests/test_evaluation_live_hybrid_execution.py</read_first>
  <behavior>
    - The control plane can create one canonical child `AnalysisRun` for a live or hybrid case without bypassing the existing queue or worker path.
    - The child run carries explicit evaluation linkage metadata so operators can inspect why it exists from the normal run surfaces.
    - The case row is updated immediately with the queued child-run pointer and a history entry.
  </behavior>
  <action>Update `backend/services/evaluation_control_plane_service.py` to add a helper such as `_enqueue_live_or_hybrid_case_run(evaluation_run: EvaluationRun, case_row: EvaluationCaseResult, case: BenchmarkCase, *, trace_carrier: dict[str, str] | None = None) -> UUID`. The helper must create an `AnalysisRun` through `AnalysisRunService` using the parent evaluation run's `project_id` and `initiated_by_user_id`, set `orchestration_goal_text` to `case.input.goal`, set `input_payload_json` to a JSON object containing the exact keys `tickers`, `analysis_goal`, and `refresh`, and set `meta_json["evaluation_case_link"]` with the exact keys `evaluation_run_id`, `case_id`, `suite_id`, and `input_mode`. Queue the child run with `RunQueueService.enqueue_after_create(...)`, then update the case row so `latest_analysis_run_id` points at the new run, `latest_analysis_run_status` is `queued`, and `analysis_run_history_json` appends an object with at least `analysis_run_id`, `status`, and `created_at`. Extend `tests/test_evaluation_live_hybrid_execution.py` to assert the child run exists in `analysis_runs`, a pending `run_execution_jobs` row exists for it, and the queued run carries the `evaluation_case_link` metadata. Extend `tests/test_evaluation_control_plane_api.py` so the serialized case body exposes the new latest-run pointer after a live or hybrid launch helper is exercised.</action>
  <acceptance_criteria>`backend/services/evaluation_control_plane_service.py` contains `_enqueue_live_or_hybrid_case_run`.
`backend/services/evaluation_control_plane_service.py` contains `AnalysisRunService`.
`backend/services/evaluation_control_plane_service.py` contains `RunQueueService`.
`backend/services/evaluation_control_plane_service.py` contains `"evaluation_case_link"`.
`backend/services/evaluation_control_plane_service.py` contains `"evaluation_run_id"`.
`backend/services/evaluation_control_plane_service.py` contains `"case_id"`.
`backend/services/evaluation_control_plane_service.py` contains `latest_analysis_run_id`.
`backend/services/evaluation_control_plane_service.py` contains `latest_analysis_run_status`.
`backend/services/evaluation_control_plane_service.py` contains `analysis_run_history_json`.
`tests/test_evaluation_live_hybrid_execution.py` contains `evaluation_case_link`.
`tests/test_evaluation_live_hybrid_execution.py` contains `RunExecutionJobStatus.pending`.
`tests/test_evaluation_control_plane_api.py` contains `latest_analysis_run_id`.
`python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>The control plane can now schedule live and hybrid cases into the canonical run queue and persist direct child-run links on the case rows.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` after each task so the linkage fields and queued child-run helper stay aligned.
</verification>

<success_criteria>
Phase 10 has a sound execution foundation once live and hybrid case rows can point to canonical queued child runs and preserve a bounded history of prior child-run ids.
</success_criteria>

<output>
After completion, create `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md`
</output>
