# Investigation Storage

Persistence for the generalized investigation model
(`agentic/domain`). Additive to the existing schema — no run, artifact, step,
critic, report, or model-call table is altered, and no existing run record is
removed. Migration: `alembic/versions/014_investigation_persistence.py`
(down-revision `013_live_hybrid_evaluation_case_run_links`).

## Tables

| Domain concept | Table | Notes |
|---|---|---|
| Investigation (root) | `investigations` | `state_version` = optimistic-concurrency version; links (nullable) to `projects`, `users`, `analysis_runs`. |
| Investigation dataset | `investigation_datasets` | DatasetReference + serialized manifest. |
| Hypothesis | `hypotheses` | self-FK `parent_hypothesis_id`; status/confidence queryable. |
| Evidence | `evidence` | direction + bounded strength/reliability/coverage; `statistics_json`. |
| Experiment request | `experiment_requests` | unique `(investigation_id, domain_id)`. |
| Experiment result | `experiment_results` | **unique `(investigation_id, idempotency_key)`** for retry dedup. |
| Observation | `observations` | FK to `experiment_results`. |
| Agent decision | `agent_decisions` | ordered by `sequence`. |
| Critique | `critiques` | typed target (`target_kind`, `target_id`). |
| Open question | `open_questions` | status + answer. |
| Conclusion | `conclusions` | `investigations.current_conclusion_id` points at the current one. |
| Reproducibility manifest | `reproducibility_manifests` | tool versions, prompt versions, model config, seed, env. |
| Orchestration checkpoint | `orchestration_checkpoints` | durable **full serialized state**; per-investigation `sequence`. |
| State event log | `investigation_state_events` | **append-only** history; per-investigation `sequence`. |
| Artifact linkage | `evidence_artifacts`, `experiment_result_artifacts` | FK to the existing `artifacts` table. |
| Evidence↔hypothesis | `evidence_hypothesis_links` | rebuildable supporting/contradicting arrays with FK integrity. |

## Reuse of existing concepts (non-destructive)

- **Artifacts** — evidence and experiment results link to the existing
  `artifacts` table via link tables; no new artifact storage.
- **Runs** — an investigation may reference an existing `analysis_runs` row
  (`analysis_run_id`, unique). See
  [`legacy-run-compatibility.md`](./legacy-run-compatibility.md).
- **Prompt / model / tool versions** — `reproducibility_manifests` persists
  `prompt_versions_json`, `model_config_json`, and `tool_versions_json`; agent
  provenance on each entity mirrors the `model_calls` audit fields.
- **Projects / users** — nullable FKs reuse existing ownership.

## Requirements → mechanism

| Requirement | How it is met |
|---|---|
| Append-oriented history | `investigation_state_events` is insert-only with a monotonic per-investigation `sequence`; every create/save/record appends an event. |
| Explicit state version | `investigations.state_version` (SQLAlchemy `version_id_col`), also stamped on every event and checkpoint. |
| Optimistic concurrency | `version_id_col` raises `StaleDataError` on a conflicting concurrent update; `save_state(expected_state_version=…)` adds an explicit app-level guard (`InvestigationConcurrencyError`). |
| Idempotent experiment recording | unique `(investigation_id, idempotency_key)`; `record_experiment_result` returns the existing row on a repeat. |
| Durable orchestration checkpoints | `orchestration_checkpoints.state_json` stores the full serialized `Investigation`, written on create and every save. |
| Foreign-key integrity | every child FK's to `investigations` (`ON DELETE CASCADE`); cross-entity FKs (`experiment_results`→`experiment_requests`, `evidence`→`experiment_results`, self-FK on `hypotheses`). |
| Artifact linkage | `evidence_artifacts` / `experiment_result_artifacts` FK the existing `artifacts.id`. |
| Prompt & model config persistence | `reproducibility_manifests.prompt_versions_json` + `model_config_json`. |
| Tool version persistence | `reproducibility_manifests.tool_versions_json` (+ `experiment_results.tool_version`). |
| Migration compatibility | additive `create_table` only; existing tables and rows untouched; downgrade drops only the new tables. |

## Repository

`backend/repositories/investigation_repository.py` — `InvestigationRepository`
(Protocol) + `SqlAlchemyInvestigationRepository`:

- `create(investigation, …)` — persists root + normalized children + repro
  manifest, appends a `created` event, writes checkpoint `#0`.
- `save_state(id, investigation, expected_state_version=…, event_type=…)` —
  upserts children by `domain_id`, appends an event, writes a checkpoint, bumps
  `state_version` (touching a real column so every save conflicts detectably).
- `load_domain(id)` — reconstructs the exact domain aggregate from the latest
  checkpoint.
- `record_experiment_result(id, result=…, idempotency_key=…)` — idempotent insert.
- `link_evidence_artifact` / `link_experiment_result_artifact` — artifact linkage.
- `import_legacy_run(analysis_run)` — compatibility import.

## What becomes source of truth

- **Native investigations** (`origin = native`): the normalized rows **plus the
  latest checkpoint** are the source of truth. The checkpoint is authoritative for
  exact-state reconstruction; the normalized rows are the durable, FK-integrous,
  queryable projection and history.
- **Legacy-import investigations** (`origin = legacy_import`): the linked
  `analysis_runs` row remains the source of truth for the numeric run; the
  investigation is a representation (see the companion doc).

## How resumed investigations restore exact state

`load_domain` reads the **latest `orchestration_checkpoints.state_json`** — the
full serialized `Investigation` — and returns
`Investigation.model_validate(state_json)`. Because the whole aggregate
(hypotheses, evidence, experiments, observations, decisions, critiques, questions,
conclusion, budget, termination, ids, timestamps) is serialized, the restored
object is byte-identical to the saved one (`test_resume_restores_exact_state`,
`test_latest_checkpoint_used_for_resume`). Every `save_state` writes a new
checkpoint, so resume always reflects the most recent durable state at the
recorded `state_version`.

## How retries avoid duplicate experiment results

`experiment_results` has a unique `(investigation_id, idempotency_key)`
constraint. Callers set the idempotency key to the experiment's deterministic
`output_fingerprint` (or `input_fingerprint`). A retried computation produces the
same key, so `record_experiment_result` finds the existing row and returns
`(row, created=False)` without inserting — exactly one result row per distinct
computation, regardless of how many times a retry re-runs it
(`test_experiment_result_recording_is_idempotent`, and the Postgres equivalent).

## Testing

- `tests/test_investigation_persistence.py` — 13 unit tests (SQLite).
- `tests/test_investigation_migration.py` — isolated 014 upgrade/downgrade DDL
  (SQLite; the full chain isn't SQLite-compatible due to an earlier migration).
- `tests/test_investigation_persistence_postgres.py` — repository behavior +
  full-chain `upgrade → downgrade(013) → upgrade` on Postgres, asserting
  `analysis_runs` survives the downgrade. Skipped without `EDGAR_TEST_POSTGRES_URL`.
