# Testing Patterns

**Analysis Date:** 2026-04-15

## Test Framework

**Runner:**
- Backend: `pytest >=8.0` from `requirements-dev.txt`, configured by `pytest.ini`.
- Frontend: `vitest ^2.1.9` from `frontend/package.json`, configured by `frontend/vitest.config.ts` with `jsdom` and `frontend/vitest.setup.ts`.
- CI: `.github/workflows/ci.yml` runs backend `pytest` on Python 3.12 and frontend `npm run lint` + `npm run build` on Node 20. It does not run `frontend` Vitest yet.

**Assertion Library:**
- Backend uses plain `assert` with pytest assertion rewriting plus `pytest.raises(...)`.
- Frontend uses Vitest `expect(...)` with DOM queries from `@testing-library/react`.

**Run Commands:**
```bash
python -m pytest tests/ -q --tb=short                                   # Backend suite (same command CI uses)
python -m pytest tests/mcp -v                                           # MCP-focused backend slice
MCP_LIVE_SEC=1 python -m pytest tests/mcp/test_integration_optional.py -v  # Opt-in live SEC resolver check
cd frontend && npm run test                                             # Frontend Vitest once
cd frontend && npm run test:watch                                       # Frontend Vitest watch mode
```

## Test File Organization

**Location:**
- Backend tests live under top-level `tests/`, grouped by concern: broad API/service tests at `tests/test_*.py`, orchestration-focused suites under `tests/orchestration/`, and MCP-specific suites under `tests/mcp/`.
- Shared backend fixtures live in `tests/conftest.py`, `tests/mcp/conftest.py`, and helper modules such as `tests/api_auth.py`.
- Frozen regression payloads live under `tests/fixtures/llm_regression/`.
- Frontend tests live under `frontend/src/` and must satisfy the Vitest include glob `src/**/*.test.{ts,tsx}` from `frontend/vitest.config.ts`. Both sibling tests (`frontend/src/components/trace/planning-transparency-panel.test.tsx`) and `__tests__` directories (`frontend/src/lib/__tests__/run-pipeline-phases.test.ts`) are valid.

**Naming:**
- Python: `test_*.py`
- Frontend: `*.test.ts` or `*.test.tsx`

**Structure:**
```text
tests/
├── conftest.py
├── api_auth.py
├── test_backend_foundation.py
├── test_run_lifecycle_api.py
├── test_llm_output_quality_regression.py
├── fixtures/
│   └── llm_regression/
├── mcp/
│   ├── conftest.py
│   ├── test_tools.py
│   └── test_integration_optional.py
└── orchestration/
    ├── test_phase3_orchestration.py
    └── test_planner_alignment_regression.py

frontend/src/
├── __tests__/sprint3-transparency.lib.test.ts
├── lib/__tests__/run-pipeline-phases.test.ts
├── components/transparency/__tests__/report-evidence-panel.test.tsx
└── components/trace/planning-transparency-panel.test.tsx
```

## Test Structure

**Suite Organization:**
```python
@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, str, dict[str, str]]]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        project_id, headers = register_project_and_headers(client)
        yield client, project_id, headers
    app.dependency_overrides.clear()
```

**Patterns:**
- Backend API/integration tests typically create an in-memory SQLite database, call `Base.metadata.create_all(...)`, override `get_db`, and drive the real FastAPI app through `TestClient` (`tests/test_backend_foundation.py`, `tests/test_run_lifecycle_api.py`, `tests/test_artifact_content_api.py`, `tests/test_async_run_queue.py`).
- `tests/conftest.py` sets a stable JWT secret before `backend.config.settings` is imported so auth-dependent tests do not depend on a developer environment.
- Shared setup logic is extracted into helpers instead of repeated inline payloads, for example `tests/api_auth.py:register_project_and_headers` and `_create_run(...)` helpers inside API suites.
- Frontend tests favor semantic DOM or typed return-value assertions over snapshots. No `toMatchSnapshot` or `toMatchInlineSnapshot` usage is detected in `frontend/src/`.
- Frontend cleanup is centralized in `frontend/vitest.setup.ts`, which runs Testing Library `cleanup()` in `afterEach`.

## Mocking

**Framework:** Python `unittest.mock` (`patch`, `patch.multiple`, `MagicMock`); frontend `vitest` `vi.mock`.

**Patterns:**
```python
@patch.multiple(_MCP, **_granular_mocks_two_tickers())
def test_successful_full_granular_pipeline() -> None:
    out = AnalysisAgent().run(
        OrchestrationInput(tickers=["AAPL", "MSFT"], analysis_goal="find unusual financial changes", refresh=False)
    )
    assert out.status == OrchestrationRunStatus.success
```

```tsx
vi.mock("next/link", () => ({
  default({ children, href }: { children: ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));
```

**What to Mock:**
- External or slow boundaries: MCP tool dispatch in `tests/orchestration/test_phase3_orchestration.py`, traceable pipeline entrypoints in `tests/test_backend_foundation.py`, `tests/test_artifact_content_api.py`, and worker-path tests such as `tests/test_async_run_queue.py`.
- Optional live integrations behind env flags: `tests/mcp/test_integration_optional.py` and the live smoke in `tests/test_llm_provider.py`.
- Next.js-only UI wrappers that interfere with DOM assertions, such as `next/link` in `frontend/src/components/transparency/__tests__/report-evidence-panel.test.tsx`.

**What NOT to Mock:**
- Pure deterministic helpers and serializers are tested directly: `tests/test_run_progress_domain.py`, `tests/test_execution_handoff.py`, `tests/test_llm_output_quality_regression.py`, `frontend/src/lib/__tests__/run-pipeline-phases.test.ts`, and `frontend/src/__tests__/sprint3-transparency.lib.test.ts`.
- FastAPI routing/auth behavior is usually exercised through a real `TestClient` plus dependency overrides rather than mocked route functions.
- UI tests assert rendered text, links, and state derived from real props instead of snapshotting or mocking the component under test.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def tmp_artifact_paths(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "panel": tmp_path / "panel.csv",
        "features": tmp_path / "features.csv",
        "report": tmp_path / "report.md",
    }
    for p in paths.values():
        p.write_text("x", encoding="utf-8")
    return paths
```

**Location:**
- `tests/conftest.py` seeds environment prerequisites for the whole backend suite.
- `tests/api_auth.py` acts as the reusable auth/project factory for API suites.
- `tests/mcp/conftest.py` provides DataFrame fixtures and temp artifact path factories for MCP contract tests.
- `tests/fixtures/llm_regression/*.json` stores frozen LLM-like payloads used by `tests/test_llm_output_quality_regression.py`.
- Backend suites commonly use `tmp_path`, `monkeypatch`, and inline helper builders instead of a large global factory library.

## Coverage

**Requirements:** None enforced. No `pytest-cov`, Coverage.py config, Vitest coverage provider, or coverage upload step is detected in `requirements-dev.txt`, `frontend/package.json`, `frontend/vitest.config.ts`, or `.github/workflows/ci.yml`.

**View Coverage:**
```bash
# Not configured in-repo
```

## Test Types

**Unit Tests:**
- Pure backend/domain logic: `tests/test_run_progress_domain.py`, `tests/test_metric_coverage.py`, `tests/test_execution_handoff.py`, `tests/test_metric_caveats.py`, `tests/test_plan_alignment_review.py`.
- Frozen contract/regression tests: `tests/test_llm_output_quality_regression.py`, `tests/orchestration/test_plan_templates.py`, `tests/orchestration/test_contract_stability.py`.
- Frontend pure helpers and view-model builders: `frontend/src/lib/__tests__/run-pipeline-phases.test.ts`, `frontend/src/lib/__tests__/run-primary-view.test.ts`, `frontend/src/lib/__tests__/context-transparency.test.ts`, `frontend/src/__tests__/sprint3-transparency.lib.test.ts`.

**Integration Tests:**
- FastAPI + SQLAlchemy + filesystem integration through in-memory SQLite, dependency overrides, and `tmp_path`: `tests/test_backend_foundation.py`, `tests/test_run_lifecycle_api.py`, `tests/test_artifact_content_api.py`, `tests/test_async_run_queue.py`, `tests/test_worker_job_lifecycle.py`.
- Orchestration boundary integration with patched MCP tools: `tests/orchestration/test_phase3_orchestration.py`.
- Optional dependency/integration checks use `pytest.importorskip(...)` and `@pytest.mark.integration` (`tests/test_api_phase_a.py`, `tests/test_auth_api.py`, `tests/test_run_lifecycle_production.py`, `tests/mcp/test_integration_optional.py`, `tests/test_llm_provider.py`).

**E2E Tests:**
- Not used. No Playwright, Cypress, or browser E2E config is detected.

## Common Patterns

**Async Testing:**
```python
with patch(
    "backend.services.edgar_pipeline_execution_service.run_traceable_edgar_pipeline",
    _fake_traceable,
):
    assert process_next_job(factory) is True
```
- Async backend behavior is usually exercised synchronously through `TestClient` or worker helper calls such as `process_next_job(...)` in `tests/test_async_run_queue.py`; dedicated `async def` test coroutines are not common in the current suite.

**Error Testing:**
```python
with pytest.raises(InvalidStatusTransition):
    svc.transition_status(run.id, AnalysisRunStatus.running)
```
- Error-path tests typically assert both exception type and message/status code (`tests/test_execution_handoff.py`, `tests/test_llm_provider.py`, `tests/test_settings_database_posture.py`).
- Frontend error-path coverage focuses on rendered failure states and missing-data fallbacks rather than thrown exceptions, for example `frontend/src/components/trace/planning-transparency-panel.test.tsx` and `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx`.

---

*Testing analysis: 2026-04-15*
