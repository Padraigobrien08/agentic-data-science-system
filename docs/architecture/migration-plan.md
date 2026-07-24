# Staged Migration Plan

Status: **plan only — no target architecture implemented beyond the additive
`agentic/` domain + adapter seam already present.** This sequences the
EDGAR→input-agnostic-agentic migration to minimize regressions, following the
project's working method: inspect → document → minimal change → tests → targeted
+ regression tests → summarize.

References: [`current-system.md`](./current-system.md),
[`target-system.md`](./target-system.md),
[`domain-boundaries.md`](./domain-boundaries.md).

---

## Non-negotiable preservation guarantees

Every stage MUST keep all of the following working, verified by existing tests
before the stage is considered done:

1. **EDGAR CLI fixture demo** — `python3 -m edgar_project.cli demo --fixtures`
   and `evaluate` (offline `suite_fixtures_v1`, `tests/test_evaluation_cli_compat.py`,
   `test_evaluate_cli_guardrails.py`).
2. **Docker Compose startup** — `db → migrate → api → worker → web`
   (`docker-compose.yml`, `.github/workflows/compose-smoke.yml`,
   `scripts/smoke-compose.sh`). No service, command, or env-contract changes
   without a smoke pass.
3. **Authentication** — JWT issue/verify, ownership 404 semantics
   (`test_auth_api.py`, `test_secure_defaults_*`, `access_checks`).
4. **Persisted run history** — existing `analysis_runs` rows remain readable;
   API run list/detail/trace unchanged (`test_run_lifecycle_api.py`,
   `test_api_phase_a.py`, `test_sprint3_transparency_api.py`).
5. **Artifact delivery** — opaque IDs, streamed bytes, previews, retention
   (`test_artifact_content_*`, `test_artifact_storage*`, `test_retention_maintenance.py`).
6. **Numerical regression tests** — `test_anomaly`, `test_peer_signals`,
   `test_findings`, `test_trend_breaks`, `test_metric_*`, `test_data_quality`,
   `tests/mcp/test_tools`, and the fixture goldens. **Frozen behavior.**

Global rules: additive migrations only (reversible Alembic), no test deletions to
make new behavior pass, no numerical logic moved into prompts, keep enums explicit,
keep domain entities out of persistence models.

---

## Stage 0 — Foundational domain + adapter seam ✅ (landed, additive)

- `agentic/domain/*` (manifest, investigation, hypothesis, experiment, evidence,
  enums) and `agentic/adapters/*` (`InputAdapter`, `AdapterRegistry`, EDGAR adapter).
- `tests/agentic/*` (16 offline tests). Nothing wired into the run path.
- **Risk:** none (no existing surface touched). **Rollback:** delete `agentic/`.

## Stage 1 — Documentation & boundary ratification (this change)

- The four `docs/architecture/*` docs. No code.
- **Exit:** team agrees on boundaries in `domain-boundaries.md`.

## Stage 2 — Deterministic tool registry (extraction, no behavior change)

- Introduce a role-aware tool registry that wraps the existing
  `edgar_project/mcp/tools.py` functions (reusing `ToolResponseEnvelope`). Tools
  declare typed inputs/outputs and the `ColumnRole`s they need.
- The EDGAR MCP tools are the first registrations; `_dispatch_mcp` stays the
  runtime path unchanged.
- **Tests:** new registry unit tests; **all** `tests/mcp/*` and orchestration
  contract tests stay green.
- **Risk:** low (adapter over existing functions). **Rollback:** drop the registry
  module; nothing else imports it yet.

## Stage 3 — Manifest-backed scope (adapter seam wired, EDGAR default)

- Add an optional `dataset_manifest` / `adapter_id` path into run creation and the
  execution service, defaulting to the EDGAR adapter built from `tickers` so
  existing requests are unchanged. `Project.tickers` and the `tickers` field remain
  supported (compat) but become one adapter's parameters.
- Persist the manifest in `AnalysisRun.meta_json` (no schema change yet).
- **Tests:** existing run-creation/lifecycle tests unchanged; new tests assert the
  EDGAR-default manifest matches today's scope. Route-preview still works.
- **Risk:** medium (touches run creation). **Mitigation:** default path is byte-for-
  byte the current one; manifest is additive metadata.

## Stage 4 — Investigation loop behind a feature flag (agency, opt-in)

- Generalize `traceable_analysis_pipeline` into an investigation engine that, when
  the flag is **off**, executes exactly today's fixed chain (single "run the whole
  pipeline" experiment → critic → report). When **on**, it runs the iterative
  planner → experiment → evidence-updater → critic → termination loop over
  `InvestigationState`.
- Rename `EdgarPipelineExecutionService` → generic run driver with a thin
  `EdgarPipelineExecutionService` alias kept for import compatibility.
- **Tests:** `test_traceable_pipeline.py` and transparency tests pass with flag
  off; new tests cover the loop with flag on using mocked tools (offline).
- **Risk:** high (core execution). **Mitigation:** flag-gated; default off; the
  off-path is the current code path.

## Stage 5 — Persistence mapping + reversible migration

- Add an `investigation_states` table (or a typed JSON column with an index) that
  stores the serialized `InvestigationState`, linked 1:1 to `analysis_runs`.
  Keep `output_payload_json` / `meta_json.ai_agents` populated for backward-compat
  UI parsing.
- Consider generic aliases for EDGAR-shaped `ToolCall` counters
  (`panel_row_count` …) without dropping columns (additive).
- **Tests:** Alembic upgrade/downgrade tested; `test_backend_foundation.py` and
  repository/service tests extended. Existing rows load unchanged.
- **Risk:** medium (schema). **Mitigation:** additive + reversible; no column drops.

## Stage 6 — Evidence-linked report + termination surfacing

- Require the report synthesizer to cite `Evidence` refs; termination decision
  (sufficient/insufficient) surfaced in `output_payload_json` and the UI.
- **Tests:** report credibility tests extended to assert evidence linkage; UI
  parser tests for the new typed fields.
- **Risk:** medium. **Mitigation:** additive fields; legacy narrative retained.

## Stage 7 — Investigation UI + second adapter + evaluation cases

- New frontend surfaces render `InvestigationState` (hypotheses, experiments,
  evidence, termination). Add one non-EDGAR adapter (e.g. generic CSV) to prove
  input-agnosticism, plus evaluation cases for agency (does the loop stop on
  sufficient vs insufficient evidence?).
- **Tests:** Vitest for the new surfaces; new offline evaluation cases; EDGAR
  demo + regression suite still green.
- **Risk:** medium (breadth). **Mitigation:** EDGAR remains the default; new
  adapter is opt-in.

---

## Regression strategy per stage

1. Run the **numerical regression subset** (`test_anomaly`, `test_peer_signals`,
   `test_findings`, `test_trend_breaks`, `test_metric_*`, `test_data_quality`,
   `tests/mcp`) — must be identical.
2. Run the **orchestration contract** + **run lifecycle/worker** subsets.
3. Run the **auth/storage/delivery** subsets.
4. Run the **offline evaluation suite** (`suite_fixtures_v1`) and the CLI demo.
5. Compose smoke for any stage that touches services, env, or migrations.

## Highest-risk migrations (ranked)

1. **Stage 4 — investigation loop over the core execution service.** Touches the
   single code path shared by API and worker; failure = broken runs. Flag-gate,
   keep the off-path identical, land behind mocked-tool tests first.
2. **Stage 5 — persistence migration.** Risk of breaking existing run history /
   Alembic. Additive + reversible only; test downgrade.
3. **Stage 3 — manifest-backed scope in run creation.** Risk of changing request
   semantics / route-preview. Default to EDGAR-from-`tickers`.
4. **Stage 6 — report/UI contract changes.** Risk of blanking the defensively
   parsed UI. Additive fields only.

## Recommended first extraction seam

**Stage 2: the deterministic tool registry over `edgar_project/mcp/tools.py`.**
It is the lowest-risk, highest-leverage seam because:

- it is a pure adapter over already-tested functions (no numerical change);
- it is exercisable entirely offline (fixtures), so it cannot regress the trust
  core;
- it unlocks Stages 3–4 (experiments need a registry of role-aware tools to select
  from) without touching run creation, persistence, auth, or the UI;
- it composes with the already-landed `agentic/adapters` manifest seam (tools bind
  to `ColumnRole`, adapters emit those roles).

Everything after it (manifest wiring, the investigation loop, persistence) builds
on this seam with progressively gated, reversible changes.
