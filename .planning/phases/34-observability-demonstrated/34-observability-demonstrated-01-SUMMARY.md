---
phase: 34-observability-demonstrated
plan: 01
status: completed
completed: 2026-08-07
requirements:
  - OBS-01
---

# Summary 34-01: The seeding workload

## What shipped

- **`scripts/seed-agent-activity.py`** — drives varied investigations against a running stack
  via `POST /v1/investigations`, using in-memory CSVs rendered from the agency fixtures.
  Configurable duration and pace; survives a stack restart mid-seed rather than dying.
- **`tests/test_seed_agent_activity.py`** — 37 tests over the pure parts.
- **`docs/observability.md`** — a "Populating the dashboard" section.

## The catalogue is the design

15 goals spanning 5+ intents, each annotated with which panel it exists to exercise. The spread
is the whole point: `docs/observability.md` says a flat single-tool profile means the loop is not
adapting, so a workload of one repeated question would reproduce that signature and make working
instrumentation look broken.

Five entries use fixtures whose data cannot support the goal (`flat`, `too_short`,
`noisy_no_trend`, `response_latency_flat`, `api_latency_rising`), so the termination breakdown
shows more than `sufficient_evidence` and the error panels are exercised. Three are drawn from
the agency hard tier, so the harder reasoning paths appear too.

## Free and offline, asserted

The workload costs nothing because `build_agent_policy` falls back to `FixtureAgentPolicy` with
no provider configured, and that policy still drives every `edgar_agent_*` metric. A test pins
that fallback, so a change to it cannot silently make this script expensive. Another asserts the
script references no external host and defaults to a local base URL.

Documented caveat: on a machine that *does* have a provider configured the backend uses the model
policy and the runs cost money. That is the operator's standing configuration, not something the
script turns on, and it says so in the module docstring.

## Mutation checks

| Mutation | Guard that fired |
|---|---|
| Point a catalogue entry at a nonexistent fixture | *"catalogue references unregistered fixtures: ['no_such_fixture']"* |
| Collapse the catalogue to one repeated trend question | *"catalogue only reaches ['trend']; the tool mix will be flat"* and *"every seeded goal converges; terminations will not vary"* |

The second is the one that matters — it is the failure that would make the whole phase produce a
misleading screenshot, and it is caught by two independent assertions.

## Deviations from plan

**The intent-spread test uses the policy's own keyword table** rather than a hand-maintained
list. Measuring the spread the loop will actually see beats asserting a spread we believe exists,
and it stays correct if the table changes.

**Test loader needed `sys.modules` registration.** The seeder is a script, not a module, and
`@dataclass` resolves its own module during class creation — importing by path without
registering first fails with an opaque `AttributeError`. Noted in the loader's docstring.

## Verification

- `1022 passed, 10 skipped` (was 985; 37 new)
- `ruff check .` clean
- `python3 -m agentic.evaluation` — core green, exit 0
- Not yet run against a live stack — that is 34-02 Task 1

## Next

34-02: bring the stack up, seed it, verify the dashboard passes its own three health checks
before capturing, then place it in the README with the agreed explicit framing (option A).
