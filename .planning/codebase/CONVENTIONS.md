# Coding Conventions

**Analysis Date:** 2026-04-15

## Naming Patterns

**Files:**
- Use `snake_case.py` for Python modules in `backend/`, `edgar_project/`, and `tests/` (examples: `backend/services/run_lifecycle_service.py`, `backend/models/analysis_run.py`, `tests/test_run_lifecycle_api.py`).
- Use lowercase `kebab-case.ts` / `kebab-case.tsx` for frontend utilities and components under `frontend/src/` (examples: `frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/transparency/report-evidence-panel.tsx`).
- Use framework-reserved filenames only where Next.js expects them: `frontend/src/app/**/page.tsx`, `frontend/src/app/**/layout.tsx`, and `frontend/src/app/api/**/route.ts`.
- Use `index.ts` barrels only inside established frontend subpackages such as `frontend/src/components/structured-answer/index.ts` and `frontend/src/lib/api/index.ts`; Python package surfaces use thin `__init__.py` re-exports such as `backend/services/__init__.py`.

**Functions:**
- Use `snake_case` for Python functions and methods (`backend/main.py:create_app`, `backend/services/run_lifecycle_service.py:cancel_analysis_run`, `backend/services/analysis_run_service.py:transition_status`).
- Use `camelCase` for TypeScript helpers and `PascalCase` for React components (`frontend/src/lib/api/client.ts:apiGet`, `frontend/src/lib/run-pipeline-phases.ts:derivePipelinePhaseView`, `frontend/src/components/runs/run-primary-answer.tsx:RunPrimaryAnswer`).
- Prefer verb-led names for mutations (`merge_output_payload`, `retry_analysis_run`, `parseArtifactRefs`) and derivation-style names for pure view builders (`deriveCurrentPhaseIndex`, `build_status_view`, `buildPrimaryAnswerView`).

**Variables:**
- Use `snake_case` locals and parameters in Python, `camelCase` in TypeScript, and preserve domain acronyms inline (`analysis_run_id`, `runId`, `llmProvider`, `apiClient`).
- Reserve module constants for uppercase or underscore-prefixed uppercase tables (`backend/domain/status_transitions.py:_ANALYSIS_RUN_ALLOWED`, `frontend/src/lib/run-pipeline-phases.ts:PIPELINE_PHASES`, `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx:EXECUTABLE_HINT`).
- Keep JSON-like blobs explicitly named with `_json` or descriptive suffixes when they cross API/storage boundaries (`meta_json`, `input_payload_json`, `trace_context_json`).

**Types:**
- Use `PascalCase` for Python classes, ORM models, and Pydantic schemas (`Settings`, `AnalysisRun`, `RunEnqueueOverrides`, `AnalysisRunRead`).
- Use `PascalCase` for TypeScript interfaces, type aliases, and component prop models (`ArtifactMetadata`, `RunStepDetail`, `PipelinePhaseView`, `Props` blocks in `frontend/src/components/*`).
- Prefer explicit string-literal unions and typed wire mirrors over loose strings in frontend API code (`frontend/src/lib/api/types.ts`).

## Code Style

**Formatting:**
- Python source follows Black-like layout even though no repo formatter config is detected. `pyproject.toml`, `ruff.toml`, `.flake8`, `.isort.cfg`, `.editorconfig`, and `.prettierrc*` are not present at repo root, so match the existing 4-space indentation, trailing commas in multiline literals, and typed signatures seen in `backend/main.py`, `backend/services/analysis_run_service.py`, and `backend/repositories/run_execution_job_repository.py`.
- Frontend TypeScript/TSX uses 2-space indentation, semicolons, and wrapped JSX props/children as seen in `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/trace/planning-transparency-panel.tsx`, and `frontend/src/components/transparency/report-evidence-panel.tsx`.
- Keep Python module docstrings at the top of files and use short JSDoc blocks only where the contract is subtle (`frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/lib/api/types.ts`).

**Linting:**
- Frontend linting is enforced by `frontend/.eslintrc.json` extending `next/core-web-vitals` and by `frontend/package.json` scripts such as `npm run lint`.
- Backend lint is enforced by `ruff.toml` and runs as a blocking `python -m ruff check .` step in `.github/workflows/ci.yml`. Rules are narrow on purpose: `E4`/`E7`/`E9`/`F`/`W` plus `I`, with `E501` omitted and `E402` ignored.
- Backend type checking is configured in `mypy.ini` and runs as a report-only (`continue-on-error`) `python -m mypy backend` step; the backend is not yet mypy-clean, so it surfaces regressions without blocking.
- Keep suppressions narrow and justified. Existing examples are side-effect imports for ORM metadata (`import backend.models  # noqa: F401` in `tests/test_backend_foundation.py`), defensive boundary catches (`# noqa: BLE001` in `backend/api/routes/health.py`), and environment-only branches (`# pragma: no cover` in `backend/llm/openai_provider.py`).

## Import Organization

**Order:**
1. Python: `from __future__ import annotations`, then standard library, then third-party packages, then local `backend` / `edgar_project` / `tests` imports.
2. Frontend: framework or external packages first (`react`, `next/*`, Testing Library), then `@/` alias imports, then relative imports.
3. Type-only imports are separated with `TYPE_CHECKING` in Python and `import type` in TypeScript.

**Path Aliases:**
- Use the `@/*` alias defined in `frontend/tsconfig.json` for frontend app imports (`@/components/...`, `@/lib/...`).
- Backend code uses package-root imports (`backend.*`, `edgar_project.*`) instead of deep relative imports across layers.
- In tests that need SQLAlchemy metadata registered, import `backend.models` once near the top before creating tables (`tests/test_backend_foundation.py`, `tests/test_run_lifecycle_api.py`, `tests/test_async_run_queue.py`).

## Error Handling

**Patterns:**
- Raise domain/service exceptions inside backend services, not HTTP exceptions. `backend/services/exceptions.py` defines `InvalidStatusTransition` and `RunLifecycleError`; callers convert them at the API boundary.
- Translate service errors with rollback before re-raising. `backend/api/routes/runs.py` catches `RunLifecycleError` / `InvalidStatusTransition`, calls `db.rollback()`, and maps them to `HTTPException`.
- Use safe parsers and guard helpers for unknown JSON-like frontend payloads. `frontend/src/lib/run-pipeline-phases.ts:metaRecord`, `frontend/src/components/transparency/report-evidence-panel.tsx:isRecord`, and `frontend/src/components/trace/planning-transparency-panel.tsx:stringList` all return fallbacks instead of throwing on malformed shapes.
- Wrap failed backend HTTP calls in `ApiError` from `frontend/src/lib/api/errors.ts`; `frontend/src/lib/api/client.ts` reads the response body once and throws `new ApiError(status, body)` on non-2xx.
- In tests, prefer `with pytest.raises(...)` and message matching over manual try/except (`tests/test_execution_handoff.py`, `tests/test_llm_provider.py`, `tests/test_run_repositories_services.py`).

## Logging

**Framework:** `structlog` on the backend; no dedicated frontend logging framework is detected.

**Patterns:**
- Configure logging once through `backend/observability/logging.py:setup_observability_logging`; JSON logs are the default from `backend/config/settings.py`.
- Acquire loggers with `structlog.get_logger(__name__)` or a scoped name (`backend/services/edgar_pipeline_execution_service.py`, `backend/worker/loop.py`, `backend/worker/__main__.py`).
- Emit event-style messages with structured fields instead of interpolated prose:
```python
log.info(
    "pipeline_completed",
    analysis_run_id=str(analysis_run_id),
    orchestration_run_id=str(out.run_id) if out.run_id else None,
    duration_s=round(duration_s, 4),
    orchestration_status=out.status.value,
    db_terminal_status=db_terminal.value,
)
```
- Bind request/run trace context before long-running work via `bind_current_trace_for_logs()` and the middleware helpers in `backend/observability/middleware.py` and `backend/observability/tracing.py`.

## Comments

**When to Comment:**
- Keep module-level Python docstrings that explain the boundary or purpose of the file (`backend/main.py`, `backend/services/run_lifecycle_service.py`, `tests/test_backend_foundation.py`).
- Use short explanatory comments for invariants, environment quirks, or boundary behavior, not line-by-line narration (`backend/config/settings.py`, `tests/test_api_phase_a.py`, `frontend/src/lib/run-pipeline-phases.ts`).
- Avoid adding new TODO/FIXME comments to product code unless there is a concrete follow-up artifact. Existing TODOs are limited to evaluation scaffolding such as `edgar_project/evaluation/runner.py`.

**JSDoc/TSDoc:**
- Use concise JSDoc on exported frontend constants/components whose contract is not obvious (`frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/components/trace/planning-transparency-panel.tsx`, `frontend/src/lib/api/types.ts`).
- Do not add heavyweight docblocks to every helper; most small local guard functions stay undocumented.

## Function Design

**Size:** Keep pure transformations small and local in `backend/domain/*.py`, `backend/agents/*` helpers, and `frontend/src/lib/*.ts`. Larger orchestration and route modules still decompose logic into helpers (`RunLifecycleService`, `derivePipelinePhaseView`, `parseArtifactRefs`) instead of nesting deep inline branches everywhere.

**Parameters:**
- Backend constructors and mutating methods prefer explicit type hints and keyword-only optional dependencies (`backend/services/run_lifecycle_service.py`, `backend/services/analysis_run_service.py`, `backend/repositories/run_execution_job_repository.py`).
- Frontend components declare a typed `Props` object and pass structured values rather than loose dictionaries (`frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/transparency/report-evidence-panel.tsx`).
- Unknown JSON from API/meta payloads is narrowed locally with guard helpers before use rather than cast globally.

**Return Values:**
- Backend services usually return ORM rows or typed tuples after flushing (`AnalysisRunService.transition_status`, `RunLifecycleService.build_status_view`, `RunExecutionJobRepository.queue_observability_snapshot`).
- Frontend helpers return explicit typed view models (`PipelinePhaseView`, `RunTransparencySummary`, `PrimaryAnswerView`) instead of mutating arguments in place.
- Use `None` / `null` sentinel returns only for expected absence (`get`, `metaRecord`, `parseArtifactRefs`), not for control-flow errors.

## Module Design

**Exports:**
- Python packages expose thin curated re-exports from `__init__.py` only where the package is used as a public surface (`backend/services/__init__.py`).
- Frontend modules overwhelmingly use named exports; keep default exports for Next.js route modules like `frontend/src/app/**/page.tsx`.
- Keep backend data contracts split by responsibility: persistence models under `backend/models/`, wire schemas under `backend/schemas/`, repositories under `backend/repositories/`, and business workflows under `backend/services/`.

**Barrel Files:**
- Use barrels selectively in frontend feature folders that already present a stable surface (`frontend/src/components/structured-answer/index.ts`, `frontend/src/lib/api/index.ts`).
- Do not introduce broad repo-wide barrels for Python code; explicit imports are the norm.

---

*Convention analysis: 2026-04-15*
