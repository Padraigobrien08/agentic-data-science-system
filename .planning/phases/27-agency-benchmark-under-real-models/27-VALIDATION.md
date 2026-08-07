# Phase 27 Validation

## Commands

- `python3 -m pytest tests/agentic -q --tb=short`
- `python3 -m pytest tests/test_agentic_model_policy_prompts.py tests/test_agency_bench.py tests/test_agent_observability.py -q --tb=short`
- `python3 -m agentic.evaluation`
- `python3 -m backend.dev.agency_bench --policy fixture --trials 2 --format md`
- `python3 -m ruff check .`
- `python3 -m mypy backend`

## Must Hold True

- `python3 -m agentic.evaluation` runs offline, free, and deterministic with no flags, no provider,
  and no prompt files present.
- No module under `agentic/` imports `backend` — at module level or inside a function — and an AST
  test enforces it.
- Imports of `edgar_project` or `src` from `agentic/` occur only in `agentic/adapters/edgar.py` and
  `agentic/experiments/tools/edgar_tools.py`, enforced by the same test as an explicit allowlist.
- The four agentic policy prompts are versioned files under `backend/agents/prompts/`, and their
  `prompt_id` + `prompt_version` land on the `ModelCall` rows the policy produces.
- A missing or unreadable prompt file degrades to the domain defaults rather than making the loop
  unrunnable, preserving `build_agent_policy`'s existing never-raise contract.
- The bench harness reports variance across trials; a case whose verdict is not unanimous is listed
  as unstable rather than averaged away.
- Cost and latency in the scoreboard come from captured `InvestigationEnded` events, not a second
  measurement path.
- The suite-level cost ceiling truncates a run before it exceeds the stated budget.
- Every `AgencyProperty` member has a committed floor, and the offline suite asserts all of them on
  every PR.
- No pull request can trigger a paid model run.
- The README's remaining stated limits — MCP rate limiting and handshake auth, no CD, no
  backup/restore runbook, single-host Compose — are unchanged.

## Out of Scope

Changes to `agentic/evaluation/agency.py` scoring logic, the `AGENCY_CASES` set, the loop, the
components, or the experiment registry. This phase measures the instrument's subject, not the
instrument.
