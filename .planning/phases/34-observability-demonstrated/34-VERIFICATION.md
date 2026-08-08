---
phase: 34-observability-demonstrated
verified: 2026-08-08T18:30:00Z
status: passed
---

# Phase 34 Verification

## Goal

Make this project's observability visible to a reader who will never clone the repo.

## What it actually found

The documented observability stack **could not produce a dashboard at all**. Four independent
defects, each fatal on its own, each failing in the way `docs/observability.md` warns is
indistinguishable from broken instrumentation:

1. `EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED` was never forwarded by compose — runs executed on the
   deterministic EDGAR chain and emitted no `edgar_agent_*` metrics at all.
2. `EDGAR_BACKEND_LLM_MODEL_PRICES` was never forwarded — cost read zero while calls were billed.
3. The Prometheus credential file was written `0400` root-owned against an image running as
   `nobody`; the API scrape had never succeeded.
4. All four stat panels declared colour mode `"text"`, which Grafana rejects — it throws in
   `applyFieldConfig` and blanks the entire dashboard.

## Verified Truths

1. The engine flag reaches the containers (`/health` reports `agentic_engine_enabled: true`).
2. All three Prometheus targets scrape successfully.
3. The dashboard renders, with 13 populated panels.
4. Cost is tracked per model-backed component (4 series, $0.80 over the run).
5. The seeding workload is offline-capable and free by construction, asserted by test.
6. The workload is varied: 5+ intents, 7 tools exercised, 2 termination reasons.
7. The three dashboard health checks pass: median iterations 1.4, 7 tools, transitions beyond
   `→ supported`.
8. The README's three pre-existing screenshots and every unrelated section are unchanged.
9. The core agency tier is green and `python3 -m agentic.evaluation` exits 0.

## Evidence

- `docker-compose.yml` — engine flag and price table forwarded
- `docker-compose.observability.yml` — credential file chowned to Prometheus's uid
- `ops/grafana/dashboards/agent-loop.json` — valid colour modes
- `scripts/seed-agent-activity.py` — the varied workload
- `tests/test_compose_env_forwarding.py` — forwarding guard + debt list
- `tests/test_grafana_dashboard_valid.py` — static dashboard validation
- `tests/test_seed_agent_activity.py` — catalogue variety, offline guarantee, standalone entry
- `docs/screenshots/agent-loop-dashboard.png` — the capture
- `README.md`, `docs/observability.md`

## Validation

- `python3 -m pytest -q` — 1066 passed, 10 skipped
- `python3 -m ruff check .` — clean
- `python3 -m agentic.evaluation` — core 13/13, exit 0

## Mutation Checks

Every new guard was shown to fail for the right reason:

| Mutation | Guard |
|---|---|
| Remove the engine flag from compose | forwarding guard, twice over |
| Restore colour mode `"text"` | dashboard validity guard |
| Point a catalogue entry at a missing fixture | fixture registration guard |
| Collapse the catalogue to one question | intent-spread and non-convergence guards |
| Remove the seeder's `sys.path` bootstrap | standalone-invocation guard |

The last one exists because the seeder's first test suite passed 37/37 while
`python3 scripts/seed-agent-activity.py` died on import — the tests loaded the module by path
from the repo root and never exercised the real entry point.

## Carried Forward

- **26 documented settings are still not forwarded by compose**, including `CORS_ALLOW_ORIGINS`,
  `AUTH_RATE_LIMIT_ENABLED`, `SECURITY_CONTENT_SECURITY_POLICY` and `ALLOW_SQLITE`. An operator
  setting a security control gets no effect and no warning. Locked by the debt list in
  `tests/test_compose_env_forwarding.py`; paying it down changes deployed behaviour and needs
  its own phase.
- `Component errors` / `Experiment failure rate by tool` are empty because nothing failed.
  Provoking real failures would need a catalogue change, not a display tweak.
