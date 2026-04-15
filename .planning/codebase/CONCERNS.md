# Codebase Concerns

**Analysis Date:** 2026-04-15

## Tech Debt

**Shared Phase 1 artifact namespace across CLI, MCP, and backend runs:**
- Issue: Phase 1 writers use fixed filenames under `data/processed/` and `data/artifacts/`, MCP adapters delegate directly to those writers, and report generation can read the default paths back in.
- Files: `src/pipeline_runner.py`, `edgar_project/mcp/adapters.py`, `edgar_project/mcp/tools.py`, `backend/services/edgar_pipeline_execution_service.py`, `data/processed/panel.csv`, `data/artifacts/report.md`
- Impact: Overlapping runs can overwrite one another, ingest stale files, or attach the wrong artifacts to a persisted run.
- Fix approach: Create per-run working directories keyed by run/orchestration id, pass explicit paths through MCP envelopes, and remove dependence on global Phase 1 filenames.

**Execution is split across three layers with process-global state:**
- Issue: The numerical pipeline in `src/`, orchestration in `edgar_project/`, and API/worker persistence in `backend/` are coupled through repo-root imports, filesystem side effects, and `os.chdir`.
- Files: `main.py`, `src/pipeline_runner.py`, `edgar_project/cli.py`, `edgar_project/repo_layout.py`, `backend/services/edgar_pipeline_execution_service.py`
- Impact: Refactors are high-risk because behavior depends on cwd, shared checkout state, and implicit path conventions rather than explicit contracts.
- Fix approach: Extract a single pure execution service with explicit input/output paths and remove process-wide cwd mutation.

**Core behavior is concentrated in large multi-responsibility modules:**
- Issue: Several central files mix orchestration, I/O, summarization, persistence, and error translation in 500-1000 line modules.
- Files: `edgar_project/mcp/tools.py` (1044 lines), `edgar_project/orchestration/executor.py` (804 lines), `src/report.py` (726 lines), `src/anomaly.py` (670 lines), `edgar_project/evaluation/runner.py` (667 lines), `frontend/src/components/trace/run-trace-experience.tsx` (638 lines), `backend/agents/traceable_analysis_pipeline.py` (515 lines), `backend/agents/artifact_summaries.py` (511 lines), `backend/agents/llm_context.py` (480 lines)
- Impact: Small changes have a wide blast radius, and repeated `except Exception` fallbacks make local failures hard to reason about.
- Fix approach: Split by responsibility first: pure transforms, artifact/path helpers, envelope shaping, and persistence should live in separate modules with narrower tests.

**Mutable runtime outputs and SEC caches are committed to git:**
- Issue: The repository tracks live-style SEC caches, processed CSVs, generated artifacts, and evaluation outputs instead of keeping only curated fixtures/examples.
- Files: `data/raw/company_tickers.json`, `data/raw/AAPL/CIK0000320193_companyfacts.json`, `data/processed/panel.csv`, `data/artifacts/unified_findings.csv`, `data/evaluation/suite_fixtures_v1_results.json`
- Impact: Repo history accumulates stale operational state, diffs become noisy, and developers can accidentally code against old outputs.
- Fix approach: Keep only intentional fixtures/goldens in git, move live outputs to ignored directories, and regenerate example artifacts from scripts when needed.

**Operational health reporting masks some backend failures:**
- Issue: Worker health falls back to zeroed queue values on `SQLAlchemyError`, and metrics refresh also zeros gauges when DB reads fail.
- Files: `backend/api/routes/health.py`, `backend/observability/metrics.py`
- Impact: Monitoring can interpret a database problem as an empty queue or idle worker instead of a degraded dependency.
- Fix approach: Emit an explicit degraded/error state, preserve the last successful readings separately, and add failure counters for scrape-time DB errors.

## Known Bugs

**SEC ticker resolution can stay stale indefinitely:**
- Symptoms: `resolve_company` / `resolve_ticker_to_cik` can reject valid tickers or return outdated mappings even when the rest of the fetch path is refreshed.
- Files: `src/data_fetch.py`, `data/raw/company_tickers.json`
- Trigger: `data/raw/company_tickers.json` already exists and SEC ticker metadata has changed since that file was written.
- Workaround: Delete `data/raw/company_tickers.json` before running live resolution.

**Successful runs can finish without persisted artifacts:**
- Symptoms: A run reaches a terminal success-like DB status, but some expected artifact rows never appear in the API.
- Files: `backend/services/edgar_pipeline_execution_service.py`
- Trigger: Any unreadable path, `OSError`, or `ValueError` during the artifact ingest loop.
- Workaround: Inspect the filesystem paths in `out.artifact_paths` directly and rerun; the ingest loop currently suppresses these failures.

**Default-path report generation can summarize the wrong run:**
- Symptoms: `generate_report_tool` can produce a report from the most recently written global `features.csv` / `anomalies.csv` rather than the caller's logical run.
- Files: `edgar_project/mcp/tools.py`, `src/pipeline_runner.py`
- Trigger: Calling `generate_report_tool` with `use_default_artifact_paths=True` after another run has already rewritten `data/processed/features.csv` or `data/artifacts/anomalies.csv`.
- Workaround: Pass explicit artifact paths instead of relying on default Phase 1 paths.

## Security Considerations

**JWT signing can fall back to a predictable built-in secret:**
- Risk: `backend/config/settings.py` ships a hard-coded default `jwt_secret`, and `_production_sanity` only checks length, not whether the default value is still active.
- Files: `backend/config/settings.py`
- Current mitigation: The secret must be at least 32 characters when `debug` is false.
- Recommendations: Fail startup when the default secret is still present and require an env-provided value outside tests.

**Open self-service registration is enabled by default:**
- Risk: Any reachable deployment accepts new accounts unless registration is explicitly disabled.
- Files: `backend/config/settings.py`, `backend/api/routes/auth.py`, `docs/auth-api.md`
- Current mitigation: `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` can turn registration off.
- Recommendations: Default to closed registration outside local development, or gate on an environment profile.

**Operational metrics are exposed without application auth:**
- Risk: `/metrics` is mounted outside the authenticated API router and exposes request, queue, worker, and model-call telemetry to any network client that can reach the service.
- Files: `backend/main.py`, `backend/api/routes/metrics.py`
- Current mitigation: None in-app; protection depends on deployment networking.
- Recommendations: Put `/metrics` behind ingress/network policy or add explicit authentication.

**LLM payloads and local host paths are persisted and re-exposable:**
- Risk: Full LLM request/response payloads and absolute artifact `source_path` values are stored and can be retrieved by owners via `include_payloads=true` or `include_meta=true`.
- Files: `backend/services/recorded_chat_completion_service.py`, `backend/models/model_call.py`, `backend/api/routes/runs.py`, `backend/services/artifact_service.py`
- Current mitigation: Owner-based access checks in `backend/api/access_checks.py`.
- Recommendations: Redact sensitive fields by default, store summaries instead of raw payloads where possible, and avoid persisting absolute filesystem paths.

## Performance Bottlenecks

**Artifact ingest loads and rewrites every file in full:**
- Problem: `ingest_pipeline_file` reads the entire source file into memory and writes a second copy into the local object store for every pipeline artifact.
- Files: `backend/services/artifact_service.py`, `backend/services/edgar_pipeline_execution_service.py`
- Cause: The pipeline writes local files first, then the backend copies them wholesale into managed storage.
- Improvement path: Write directly to object storage or stream-copy with hashing instead of `Path.read_bytes()`.

**Metrics and worker-health scrapes issue multiple live DB aggregations:**
- Problem: Queue depth and terminal activity metrics are recomputed with several `COUNT(*)` / `MAX(...)` queries on each scrape.
- Files: `backend/observability/metrics.py`, `backend/repositories/run_execution_job_repository.py`, `backend/api/routes/health.py`
- Cause: Observability derives queue state from transactional tables rather than from cached counters.
- Improvement path: Maintain counters on enqueue/finalize, cache snapshots, or reduce scrape frequency.

**Synchronous run execution ties up HTTP workers for long jobs:**
- Problem: `POST /v1/runs/{run_id}/execute` performs SEC fetches, artifact generation, persistence, and optional LLM phases inline.
- Files: `backend/api/routes/runs.py`, `backend/services/edgar_pipeline_execution_service.py`
- Cause: The API exposes both background and fully synchronous execution paths.
- Improvement path: Route non-trivial work through the queue by default and surface progress via status/streaming endpoints instead of long-held requests.

## Fragile Areas

**Background job leasing has no heartbeat/renewal path:**
- Files: `backend/config/settings.py`, `backend/repositories/run_execution_job_repository.py`, `backend/worker/loop.py`
- Why fragile: `lease_expires_at` is set when a job is claimed, but no code refreshes the lease during execution. A long-running job becomes reclaimable while it is still active.
- Safe modification: Add periodic lease renewal inside the worker and treat reclaim/retry logic as a transaction contract, not just a polling detail.
- Test coverage: Queue lifecycle is covered by `tests/test_worker_job_lifecycle.py`, `tests/test_async_run_queue.py`, and `tests/test_run_lifecycle_production.py`, but there is no checked-in long-running heartbeat scenario.

**Run isolation depends on cwd and repo-local default paths:**
- Files: `edgar_project/repo_layout.py`, `backend/services/edgar_pipeline_execution_service.py`, `edgar_project/mcp/tools.py`, `src/report.py`
- Why fragile: Backend execution changes process cwd, and several report/artifact paths are discovered implicitly from repo-local defaults instead of being passed through explicitly.
- Safe modification: Thread explicit path/workdir objects through the pipeline and remove `chdir_repo_root`.
- Test coverage: Orchestration and API tests cover the happy path, but not concurrent multi-run path isolation in one checkout.

**MCP/report artifact enrichment suppresses parse/read failures locally:**
- Files: `edgar_project/mcp/tools.py`
- Why fragile: Many `try/except Exception` branches fall back silently when reading optional CSVs and trustworthiness artifacts.
- Safe modification: Centralize artifact inspection, log partial failures consistently, and return explicit warning codes rather than silently degrading.
- Test coverage: `tests/mcp/test_tools.py` and orchestration tests cover typical success/error cases, not every fallback branch.

**Transparency behavior spans large, tightly coupled backend and frontend files:**
- Files: `backend/agents/traceable_analysis_pipeline.py`, `backend/agents/artifact_summaries.py`, `backend/agents/llm_context.py`, `frontend/src/components/trace/run-trace-experience.tsx`, `backend/schemas/run_transparency.py`, `frontend/src/lib/api/types.ts`
- Why fragile: Prompt versions, artifact summaries, model-call payloads, and trace UI rendering are coupled across large modules and a shared wire schema.
- Safe modification: Treat the schema layer as the boundary, then split context construction, persistence, and rendering into smaller units behind that contract.
- Test coverage: `tests/test_traceable_pipeline.py`, `tests/test_sprint3_transparency_api.py`, and a handful of frontend unit tests cover slices, not full-browser navigation with large real payloads.

## Scaling Limits

**Phase 1 writer concurrency is effectively one safe writer per repo checkout:**
- Current capacity: One run can safely own `data/processed/*.csv` and `data/artifacts/*.csv` at a time.
- Limit: Concurrent runs overwrite shared filenames before ingestion/persistence finishes.
- Scaling path: Give every run a unique output directory and make artifact paths first-class throughout orchestration and persistence.

**Worker throughput is one blocking run per worker process:**
- Current capacity: `backend/worker/__main__.py` runs a single polling loop that claims one job and blocks until pipeline completion.
- Limit: Throughput only scales by adding more worker processes, while missing lease heartbeats make long-running parallel work unsafe.
- Scaling path: Add lease renewal, idempotent per-run workspaces, and then parallel worker capacity or a dedicated queue backend.

**Artifact storage assumes a shared local filesystem:**
- Current capacity: Only `local:` URIs are implemented, with shared visibility expected between API and worker processes.
- Limit: Multi-host deployment requires a shared volume; `backend/storage/resolver.py` has no remote object-store path in use.
- Scaling path: Add S3/object-store support and remove assumptions that API and worker see the same local disk.

**Run history grows without retention bounds:**
- Current capacity: `analysis_runs`, `artifacts`, and `model_calls` store payload JSON, raw model responses, and copied artifact blobs indefinitely.
- Limit: Database size, local object storage, and payload-heavy API responses get larger with each run.
- Scaling path: Add retention/archival, truncate or redact raw payloads, and separate audit-grade storage from hot query paths.

## Dependencies at Risk

**Python runtime dependencies are only minimum-version ranges:**
- Risk: Reinstalls can pull newer transitive dependency trees without any code change.
- Files: `requirements.txt`, `requirements-backend.txt`, `requirements-dev.txt`
- Impact: CI, local dev, and production are harder to reproduce across `fastapi`, `sqlalchemy`, `pydantic`, and `openai`.
- Migration plan: Adopt a compiled lockfile (`pip-tools`, `uv`, Poetry, or equivalent) and pin runtime vs dev dependencies explicitly.

**Frontend dependency resolution is split across npm and pnpm:**
- Risk: The repo keeps both `package-lock.json` and `pnpm-lock.yaml` without a declared `packageManager` in `frontend/package.json`.
- Files: `frontend/package-lock.json`, `frontend/pnpm-lock.yaml`, `frontend/package.json`
- Impact: CI uses `npm ci`, while local contributors can resolve a different tree with pnpm.
- Migration plan: Standardize on one package manager, delete the extra lockfile, and declare the package manager/version in `frontend/package.json`.

## Missing Critical Features

**Live and hybrid evaluation modes are not implemented in the benchmark runner:**
- Problem: `edgar_project/evaluation/runner.py` skips `InputMode.live` and `hybrid`, and `edgar_project/evaluation/README.md` documents that real SEC/MCP end-to-end execution is not exercised.
- Blocks: Confidence in live SEC fetches, network failure handling, cache refresh behavior, and orchestration behavior outside mocked fixtures.

**Rubric data is loaded but does not affect benchmark pass/fail:**
- Problem: `EvaluationRunner` accepts a `Rubric`, but `edgar_project/evaluation/README.md` states rubric scoring is not applied to case outcomes.
- Blocks: Score-based acceptance criteria, richer benchmark prioritization, and non-binary quality gates.

**SEC access is not productionized:**
- Problem: `config.py` hard-codes `SEC_USER_AGENT` with a placeholder contact, and `src/data_fetch.py` uses fixed sleeps with no retry/backoff or cache invalidation for the ticker map.
- Blocks: Reliable live SEC access, operational compliance, and accurate ticker resolution under real usage.

## Test Coverage Gaps

**Live SEC behavior is opt-in only and absent from default CI:**
- What's not tested: real resolver/fetch behavior against current SEC responses is skipped unless `MCP_LIVE_SEC=1`.
- Files: `tests/mcp/test_integration_optional.py`, `pytest.ini`, `.github/workflows/ci.yml`
- Risk: SEC contract changes, rate limits, or cache-format drift can break production paths without failing pull requests.
- Priority: High

**Frontend tests are unit/component level and are not run in CI:**
- What's not tested: authenticated page flows, cookie-backed session behavior, artifact proxy routes, and end-to-end trace navigation in the running app.
- Files: `frontend/vitest.config.ts`, `frontend/src/__tests__/sprint3-transparency.lib.test.ts`, `frontend/src/components/trace/planning-transparency-panel.test.tsx`, `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx`, `.github/workflows/ci.yml`
- Risk: SSR/auth regressions can ship even when lint and build pass.
- Priority: High

**PR CI does not cover the documented Postgres + worker + web stack:**
- What's not tested: the documented Compose topology, Postgres-specific queue semantics, background worker execution, and frontend integration are not part of pull request gating.
- Files: `.github/workflows/ci.yml`, `.github/workflows/compose-smoke.yml`, `docs/local-stack.md`, `backend/config/settings.py`
- Risk: behavior can differ between SQLite-backed CI and the documented production posture.
- Priority: High

**Concurrent artifact-path collisions and long-running lease expiry are untested:**
- What's not tested: overlapping runs that write the same `data/processed/` and `data/artifacts/` paths, plus jobs that run longer than `run_job_lease_seconds`.
- Files: `src/pipeline_runner.py`, `edgar_project/mcp/tools.py`, `backend/repositories/run_execution_job_repository.py`, `backend/worker/loop.py`
- Risk: duplicate execution, stale artifacts, and race conditions can reach users without a regression test catching them.
- Priority: High

---

*Concerns audit: 2026-04-15*
