---
phase: 27-agency-benchmark-under-real-models
plan: 01
status: completed
completed: 2026-08-07
requirements:
  - AGCY-01
  - AGCY-02 (partial — see Deviations)
---

# Summary 27-01: Versioned prompts for the policy surface

## What shipped

- **`PolicyPrompts` injection seam** (`agentic/agent/policy.py`). A frozen dataclass whose four
  fields default to the exact strings that were previously inline, so a no-argument
  `ModelAgentPolicy` is behaviourally identical to the pre-change version. `DEFAULT_POLICY_PROMPTS`
  is the shared default instance. All four `_call` sites now read from `self._prompts`.
- **Four versioned prompt bodies** under `backend/agents/prompts/agentic_*/1.0.0.md`, each ~2.3-2.5k
  chars, carrying the exact input payload shape, the output JSON schema, the closed enum values,
  and a role-appropriate calibration section.
- **Registry entries** — four ids namespaced `edgar.agentic.*` plus `AGENTIC_POLICY_ROLES`, ordered
  to match `AgentPolicy`'s four methods.
- **Loading and injection** in `build_agent_policy`, via `_load_policy_prompts()`, which degrades to
  the domain defaults on any file error rather than raising.
- **`CostAwareModelPolicy.prompt_identity`** — a `prompt_id -> version` map the 27-03 scoreboard
  reads to name the prompts that produced a result.

## Verification

- `891 passed, 10 skipped` (was 877 + 10 before this plan; 14 new tests)
- `ruff check .` — clean
- `mypy backend` — 53 errors before, 53 after; none in the files touched. The one pre-existing
  error in `agentic_model_policy.py:63` (`response_format`) is on an untouched line.
- `python3 -m agentic.evaluation` — still runs offline with no provider, 12/12, 100% on all
  eight properties.

## Deviations from plan

**`ModelCall` persistence was carved out of AGCY-02.** The plan's Task 3 said to make
`prompt_id`/`prompt_version` "reach the `ModelCall` persistence path used by the recorded-completion
service." That assumed such a path existed for the agentic policy. It does not:
`CostTrackingResponder` calls `provider.complete()` directly, and `ModelCall` rows are written only
by `RecordedChatCompletionService`, which requires a `Session` and an `analysis_run_id` — neither of
which `build_agent_policy(settings)` has or should have.

Wiring it would mean threading a session and run id through `build_agent_policy`, changing its
signature and both call sites (`agentic_investigation_execution_service`,
`investigation_replay_service`). That is a distinct piece of work and was not done here.

Prompt identity is instead exposed on the policy object and emitted on the
`agentic.policy.model_backed` log event. This fully satisfies the benchmark's traceability need —
27-03 records prompt versions in the scoreboard, and the bench harness runs with no DB session at
all. It leaves a genuine gap for *product* runs: a user's investigation does not currently produce
`ModelCall` rows for its four policy decisions, so agentic runs are invisible to LLM cost/usage
analytics that read that table.

## Correction to phase scoping

The CONTEXT's original D-01 claim — "`agentic/` imports nothing from `backend/` or
`edgar_project/`" — was wrong, and was derived from a line-anchored grep that could not see
function-local imports. An AST scan gives the accurate picture:

| Root | Imports | Where |
|---|---|---|
| `backend` | 0 | — |
| `edgar_project` | 3 | `agentic/experiments/tools/edgar_tools.py` (all function-local) |
| `src` | 3 | `agentic/adapters/edgar.py`, `agentic/experiments/tools/edgar_tools.py` |

The `backend` invariant is absolute and holds. The `edgar_project`/`src` imports are the adapter
pattern working as designed, confined to two EDGAR bridge modules and lazy so the generic path
never pays for them. D-01, 27-VALIDATION, and 27-02 Task 1 were all corrected: the boundary test
now forbids `backend` outright and allowlists the two bridge modules for `edgar_project`/`src`.

Had this not been caught, 27-02 Task 1 would have failed on first run against existing code.

## Follow-ups

- **`ModelCall` persistence for agentic policy calls** — needs a decision on whether
  `build_agent_policy` grows session-aware construction, or whether the recording moves into
  `agentic_investigation_execution_service` where the session already lives. Not blocking 27-02.
- `_agentic_model` still defaults to `"gpt-5.4-mini"`. Confirm it resolves before 27-03 runs a
  paid benchmark — an unresolvable model id fails every case as `reason=error`, which scores as a
  confident-looking zero rather than an obvious misconfiguration.

## Next

27-02: observer passthrough, pure multi-trial aggregation, the bench harness, and the corrected
boundary test.
