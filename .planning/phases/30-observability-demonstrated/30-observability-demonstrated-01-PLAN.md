---
phase: 30-observability-demonstrated
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/seed-agent-activity.py
  - docs/observability.md
  - tests/test_seed_agent_activity.py
autonomous: true
requirements:
  - OBS-01
must_haves:
  truths:
    - "The workload runs offline and free — no API key, no SEC calls, no spend."
    - "Goals span intents, so the tool-mix and hypothesis-transition panels show variation rather than a flat profile."
    - "Some runs terminate unusually, so the error and termination-reason panels are exercised rather than empty."
    - "The procedure is documented well enough that a reader can reproduce the dashboard themselves."
  artifacts:
    - path: scripts/seed-agent-activity.py
      provides: "Repeatable varied agent workload against a running local stack"
    - path: docs/observability.md
      provides: "How to populate the dashboard, and what a healthy one looks like"
  key_links:
    - from: scripts/seed-agent-activity.py
      to: backend/api/routes/investigations.py
      via: "the seeder drives POST /v1/investigations with in-memory CSV datasets"
      pattern: "/v1/investigations|csv|records"
---

<objective>
Build a workload that makes the agent-loop dashboard show something worth looking at.

Purpose: the dashboard's panels are `rate()` over a 15s scrape. Without sustained, varied
activity a screenshot proves only that Grafana renders.
Output: a seeding script, its documentation, and a test that it stays offline.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/30-observability-demonstrated/30-CONTEXT.md
@.planning/phases/30-observability-demonstrated/30-VALIDATION.md
@backend/api/routes/investigations.py
@backend/services/investigation_create_service.py
@backend/agents/agentic_model_policy.py
@agentic/evaluation/cases.py
@agentic/evaluation/fixtures.py
@scripts/smoke-compose.sh
@docs/observability.md
@docs/local-stack.md

<interfaces>
The seeding surface — `POST /v1/investigations`, no SEC involved:
```python
# backend/services/investigation_create_service.py
def create_and_run(..., goal: str, dataset_format: str, csv_text: str | None,
                   records: list[dict] | None, name: str | None) -> ...
# dataset_format is "csv" or "records"; the adapter is in_memory
```

The offline guarantee — `backend/agents/agentic_model_policy.py`:
```python
except LLMProviderConfigurationError:
    log.info("agentic.policy.fixture", reason="llm_provider_unavailable")
    return FixtureAgentPolicy()
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: The seeding script</name>
  <files>scripts/seed-agent-activity.py
tests/test_seed_agent_activity.py</files>
  <read_first>backend/api/routes/investigations.py
backend/services/investigation_create_service.py
agentic/evaluation/cases.py
agentic/evaluation/fixtures.py
scripts/smoke-compose.sh</read_first>
  <behavior>
    - Registers or logs in a user, ensures a project, then submits investigations in a loop
      against a running stack, pacing them so timeseries panels have shape rather than one spike.
    - Goals span intents — trend, comparison, ranking, correlation, anomaly, distribution — so
      the tool-mix piechart is not degenerate.
    - Includes goals whose data cannot support them, so terminations vary beyond
      `sufficient_evidence` and the termination breakdown is populated.
    - Datasets are small in-memory CSVs derived from the agency fixtures; nothing reaches SEC.
    - Configurable duration and concurrency; safe to interrupt.
  </behavior>
  <action>Create `scripts/seed-agent-activity.py` with argparse flags for base URL, duration,
pacing, and credentials. Build a goal catalogue spanning every `AnalysisIntent`, each paired
with a small CSV rendered from `agentic.evaluation.fixtures` — reuse the fixtures rather than
inventing data, so the workload is deterministic and already known to exercise different tools.
Include at least one goal per run cycle whose premise the data cannot support, so terminations
vary. Authenticate, ensure a project exists, then submit investigations at the configured pace
until the duration elapses, logging progress and a final tally by termination reason. Handle
connection errors without dying — a stack that restarts mid-seed should not lose the run.
Create `tests/test_seed_agent_activity.py` covering the pure parts: the goal catalogue spans
more than one intent, every entry renders to valid CSV, and the catalogue includes at least one
goal expected to fail to converge. Do not test against a live stack.</action>
  <acceptance_criteria>`scripts/seed-agent-activity.py` exists and is executable.
It submits to `/v1/investigations`.
Its goal catalogue covers at least five distinct intents.
It includes at least one goal whose data cannot support it.
`tests/test_seed_agent_activity.py` exists and asserts intent spread and CSV validity.
`python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short` passes without a running stack.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short</automated>
  </verify>
  <done>There is a repeatable way to make the dashboard show real, varied agent behaviour.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Prove it stays offline and free</name>
  <files>tests/test_seed_agent_activity.py</files>
  <read_first>backend/agents/agentic_model_policy.py
agentic/agent/fixture_policy.py</read_first>
  <behavior>
    - The seeder cannot cause spend: with no provider configured the policy is the deterministic
      fixture, and the workload makes no outbound calls other than to the local API.
    - This is asserted, not assumed, because the standing goal forbids spending and a seeder that
      quietly used a configured key would violate it on someone else's machine.
  </behavior>
  <action>Add a test asserting `build_agent_policy` returns `FixtureAgentPolicy` when the
provider is unconfigured, and that the seeding module imports nothing that would reach an
external service. Mutation-check it: point the goal catalogue at a nonexistent fixture and
confirm the CSV-validity test fails; restore. Document in the script's module docstring that it
is free and offline by construction, and that a machine with a configured key will use the model
policy instead — which costs money and is the operator's explicit choice, not the script's.</action>
  <acceptance_criteria>A test asserts the offline fixture fallback.
The script's docstring states the free/offline guarantee and its one caveat.
`python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short</automated>
    <manual>Mutation-check: break a fixture reference, confirm the test fails, restore.</manual>
  </verify>
  <done>The workload cannot cost anyone money by accident.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Document the procedure</name>
  <files>docs/observability.md</files>
  <read_first>docs/observability.md
docs/local-stack.md</read_first>
  <behavior>
    - A reader can bring up the stack, seed it, and see the dashboard populated, without guessing.
    - The doc says what a *healthy* dashboard looks like, tied to the failure signatures the page
      already names.
    - It states that seeded runs use the deterministic policy and therefore show zero spend.
  </behavior>
  <action>Add a "Populating the dashboard" section to `docs/observability.md`: bringing up the
stack with the observability overlay, enabling `EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED` on both
api and worker, running the seeder, and how long to wait before the timeseries panels are
legible. Cross-reference the existing failure signatures — median iterations pinned at 1, a flat
single-tool profile, only `→ supported` transitions — as the checks a reader should apply to
their own populated dashboard. Note that seeded runs use the fixture policy, so
`edgar_agent_cost_usd_total` stays at zero and that is expected rather than a broken metric.</action>
  <acceptance_criteria>`docs/observability.md` contains a "Populating the dashboard" section.
It names the agentic engine flag requirement for api and worker.
It states the zero-cost expectation for seeded runs.
It cross-references the existing failure signatures.</acceptance_criteria>
  <verify>
    <manual>Follow the section from a clean shell and confirm it is sufficient without prior knowledge.</manual>
  </verify>
  <done>Anyone can reproduce the dashboard, which is what makes a screenshot of it credible.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short` after each task.
Full suite and lint before commit, per the standing goal.
</verification>

<success_criteria>
A documented, tested, offline, free workload that drives varied agent activity through the
backend, so the agent-loop dashboard shows adaptation rather than a flat line.
</success_criteria>

<output>
After completion, create `.planning/phases/30-observability-demonstrated/30-observability-demonstrated-01-SUMMARY.md`
</output>
