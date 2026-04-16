---
phase: 04-ci-coverage
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/ci-postgres-regressions.sh
  - .github/workflows/postgres-regressions.yml
autonomous: false
requirements:
  - QUAL-03
must_haves:
  truths:
    - "Artifact-collision, heartbeat, and Postgres claim/reclaim regressions run as a dedicated PR-required check instead of being buried in the slower full-stack gate."
    - "The Postgres regression workflow uses a real Postgres service container and the exact `EDGAR_TEST_POSTGRES_URL` contract already supported by the test suite."
    - "The regression command is reusable locally and in CI through a checked-in script."
  artifacts:
    - path: scripts/ci-postgres-regressions.sh
      provides: "Single source of truth for the required Postgres regression slice"
    - path: .github/workflows/postgres-regressions.yml
      provides: "Dedicated PR workflow for collision and lease regressions"
  key_links:
    - from: scripts/ci-postgres-regressions.sh
      to: tests/test_worker_job_lifecycle_postgres.py
      via: "script runs the exact Postgres claim/reclaim regression file"
      pattern: "test_worker_job_lifecycle_postgres.py"
    - from: scripts/ci-postgres-regressions.sh
      to: tests/test_worker_lease_heartbeat.py
      via: "script includes the heartbeat and lease-loss regression slice"
      pattern: "test_worker_lease_heartbeat.py"
    - from: .github/workflows/postgres-regressions.yml
      to: scripts/ci-postgres-regressions.sh
      via: "workflow exports `EDGAR_TEST_POSTGRES_URL` and invokes the shared regression script"
      pattern: "EDGAR_TEST_POSTGRES_URL|ci-postgres-regressions.sh"
---

<objective>
Promote the highest-risk collision and lease regressions into a separate required Postgres-backed CI workflow.

Purpose: satisfy QUAL-03 with faster failure isolation than the full-stack Compose gate, so concurrency and stale-lease bugs fail in a focused regression job before they reach users.
Output: one checked-in regression script and one PR-triggered Postgres workflow that runs the exact collision/heartbeat/claim tests.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-ci-coverage/04-CONTEXT.md
@.planning/phases/04-ci-coverage/04-RESEARCH.md
@.planning/phases/04-ci-coverage/04-VALIDATION.md
@tests/test_run_isolation_overlap.py
@tests/test_worker_lease_heartbeat.py
@tests/test_worker_job_lifecycle_postgres.py
@tests/postgres_queue_test_utils.py
@.github/workflows/ci.yml

<interfaces>
From `tests/test_worker_job_lifecycle_postgres.py`:
```python
postgres_session_factory: sessionmaker[Session]
```

From `tests/postgres_queue_test_utils.py`:
```python
EDGAR_TEST_POSTGRES_URL
```

From `.github/workflows/ci.yml`:
```yaml
jobs:
  backend:
  frontend:
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create a reusable Postgres regression command for collision and lease tests</name>
  <files>scripts/ci-postgres-regressions.sh</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
tests/test_run_isolation_overlap.py
tests/test_worker_lease_heartbeat.py
tests/test_worker_job_lifecycle_postgres.py
tests/postgres_queue_test_utils.py</read_first>
  <behavior>
    - One checked-in script runs the exact Phase 4 concurrency regression slice.
    - The script requires `EDGAR_TEST_POSTGRES_URL` and fails fast when it is missing.
    - The script runs overlap, heartbeat, and Postgres claim/reclaim tests in one command.
  </behavior>
  <action>Create `scripts/ci-postgres-regressions.sh` as a POSIX shell script with `#!/usr/bin/env bash` and `set -euo pipefail`. Require `EDGAR_TEST_POSTGRES_URL` to be non-empty and print a clear error if it is missing. Run the exact command `python3 -m pytest tests/test_run_isolation_overlap.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle_postgres.py -q --tb=short` with `EDGAR_TEST_POSTGRES_URL` exported to the current environment. Keep the script reusable both locally and in CI; do not hard-code GitHub-only paths or behavior.</action>
  <acceptance_criteria>`scripts/ci-postgres-regressions.sh` exists.
`scripts/ci-postgres-regressions.sh` starts with `#!/usr/bin/env bash`.
`scripts/ci-postgres-regressions.sh` contains `set -euo pipefail`.
`scripts/ci-postgres-regressions.sh` checks for `EDGAR_TEST_POSTGRES_URL`.
`scripts/ci-postgres-regressions.sh` contains `tests/test_run_isolation_overlap.py`.
`scripts/ci-postgres-regressions.sh` contains `tests/test_worker_lease_heartbeat.py`.
`scripts/ci-postgres-regressions.sh` contains `tests/test_worker_job_lifecycle_postgres.py`.
`bash -n scripts/ci-postgres-regressions.sh` exits 0.</acceptance_criteria>
  <verify>
    <automated>bash -n scripts/ci-postgres-regressions.sh</automated>
  </verify>
  <done>The regression slice is encoded once in a checked-in script instead of being duplicated across local and CI commands.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Run the Postgres regression slice as a dedicated PR workflow</name>
  <files>.github/workflows/postgres-regressions.yml</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
.github/workflows/ci.yml
scripts/ci-postgres-regressions.sh
tests/test_worker_job_lifecycle_postgres.py
tests/postgres_queue_test_utils.py</read_first>
  <behavior>
    - Pull requests trigger a dedicated `Postgres Regressions` workflow.
    - The workflow uses a real PostgreSQL service container.
    - The workflow exports the exact `EDGAR_TEST_POSTGRES_URL` expected by the test helpers.
    - The workflow invokes the shared regression script and preserves failure output.
  </behavior>
  <action>Create `.github/workflows/postgres-regressions.yml` with workflow name `Postgres Regressions`, `pull_request` plus `push` to `main`/`master`, and a single job named `postgres-regressions`. In that job, use `ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5` with Python `3.12`, and `pip install -r requirements-dev.txt`. Add a `postgres:16` service container with `POSTGRES_USER=edgar`, `POSTGRES_PASSWORD=edgar`, `POSTGRES_DB=edgar`, and health options based on `pg_isready -U edgar -d edgar`. Export `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar` in the regression step and invoke the script through an exact shell block `set -o pipefail; bash scripts/ci-postgres-regressions.sh 2>&1 | tee .tmp/postgres-regressions.log` so the workflow preserves the regression exit status while still writing a log file. Upload `.tmp/postgres-regressions.log` as a workflow artifact on failure so lease/collision failures remain diagnosable.</action>
  <acceptance_criteria>`.github/workflows/postgres-regressions.yml` exists.
`.github/workflows/postgres-regressions.yml` contains `name: Postgres Regressions`.
`.github/workflows/postgres-regressions.yml` contains `pull_request:`.
`.github/workflows/postgres-regressions.yml` defines a `postgres` service.
`.github/workflows/postgres-regressions.yml` sets `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar`.
`.github/workflows/postgres-regressions.yml` runs `bash scripts/ci-postgres-regressions.sh`.
`.github/workflows/postgres-regressions.yml` contains `set -o pipefail`.
`.github/workflows/postgres-regressions.yml` uploads `.tmp/postgres-regressions.log` on failure.</acceptance_criteria>
  <verify>
    <automated>EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar bash scripts/ci-postgres-regressions.sh</automated>
  </verify>
  <done>Collision and lease regressions now fail in a fast, focused Postgres workflow instead of being buried inside the slower full-stack gate.</done>
</task>

<task type="checkpoint:human-action">
  <name>Task 3: Mark the new CI jobs as required checks in GitHub branch protection or rulesets</name>
  <files>.github/workflows/compose-smoke.yml, .github/workflows/postgres-regressions.yml</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
.github/workflows/compose-smoke.yml
.github/workflows/postgres-regressions.yml</read_first>
  <action>Stop execution with a human-action checkpoint after the `Full Stack / full-stack` and `Postgres Regressions / postgres-regressions` workflows exist and have run at least once on a branch. Ask the user to open the repository branch protection or ruleset settings and mark those exact checks as required for merge. Resume only after the user confirms the settings change.</action>
  <acceptance_criteria>The task names the exact required checks `Full Stack / full-stack` and `Postgres Regressions / postgres-regressions`.
The task instructs the executor to stop for a human-action checkpoint instead of silently assuming workflow YAML makes checks required.
Execution does not proceed past this checkpoint until the user confirms the branch protection or ruleset update.</acceptance_criteria>
  <verify>
    <manual>Confirm in GitHub settings or a protected-branch test PR that `Full Stack / full-stack` and `Postgres Regressions / postgres-regressions` are required checks for merge.</manual>
  </verify>
  <done>The repository-level settings now enforce the new CI jobs as actual merge gates instead of merely running them on pull requests.</done>
</task>

</tasks>

<verification>
Lint the script as soon as it exists, then run the full Postgres regression command once the workflow wiring is in place so the CI slice proves the exact tests it advertises, and finally stop for the required-check checkpoint before declaring the plan complete.
</verification>

<success_criteria>
Phase 4 gains a focused required regression boundary when pull requests run the exact overlap, heartbeat, and Postgres claim/reclaim tests through a dedicated workflow backed by a real Postgres service and GitHub settings mark that workflow plus the full-stack gate as required checks for merge.
</success_criteria>

<output>
After completion, create `.planning/phases/04-ci-coverage/04-ci-coverage-03-SUMMARY.md`
</output>
