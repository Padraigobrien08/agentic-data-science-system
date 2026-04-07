# Orchestration (Phase 3)

## In-process structure

Three roles, all in one process today:

| Role | Code | Responsibility |
|------|------|------------------|
| **Coordinator** | `agent.py` (`AnalysisAgent`, `run_analysis_agent`) | Validate `OrchestrationInput`, allocate `run_id`, call `Planner`, handle planning failure (no MCP), build `ExecutionRequest`, call `Executor`, set `final_summary`, run-level logging. |
| **Planner** | `planner.py` (`Planner`) | Map input → `PlanningOutcome` (`OrchestrationPlan` + `InterpretedGoal` or errors). Rule-based, deterministic. No MCP, no SEC/network. |
| **Executor** | `executor.py` (`Executor`) | Accept `ExecutionRequest` → run MCP tools via `edgar_project.mcp.tools` only, accumulate step state, classify terminal status, produce `OrchestrationOutput`. |

`ExecutionRequest` / `ExecutionResult` (`execution_contract.py`) define the planner↔executor handoff. `OrchestrationRunState` is built inside the executor from that request for step history.

## Why not remote workers yet

Remote processes add transport, versioning, and failure modes without a current need: throughput is modest, credentials and MCP already sit behind one Python boundary, and the team is still evolving plans and tool behavior. The code is shaped so that boundary could move later without redesigning semantics.

## Future split boundary

The stable wire is: **`ExecutionRequest` in → `OrchestrationOutput` out** (JSON-serializable via Pydantic). A remote executor would deserialize `ExecutionRequest`, run the same `Executor` logic (or equivalent), and return `OrchestrationOutput`. The coordinator would stay the entrypoint that validates input and sequences planner → executor; only the executor call might become RPC.

## What stays centralized

- **Contracts:** `schemas.py` (inputs, outputs, errors, statuses), `constants.py` (tool names, status strings, default tickers when input is empty).
- **Handoff:** `execution_contract.py` (`ExecutionRequest`, `ExecutionResult` alias).
- **Logging helpers:** `run_logging.py` (shared `run_id` correlation style).

## Contract versioning and serialization

- **`ORCH_RUN_STATE_CONTRACT_VERSION`** (`constants.py`): bump when `OrchestrationRunState` or `ExecutionRequest` public fields change; keep `ExecutionRequest.contract_version` and `OrchestrationRunState.contract_version` in lockstep (same integer source).
- **JSON:** `ExecutionRequest`, `OrchestrationRunState`, `PlanningOutcome`, and `OrchestrationOutput` are intended to round-trip with `model_dump(mode="json")` / `model_validate(_json)` for logging, tests, and a future remote executor.

## Permissions (who may do what)

- **Coordinator:** Must not call MCP or Phase 1 pipeline code. It does not reinterpret `analysis_goal` for routing; that is the planner’s job.
- **Planner:** Must not call MCP, mutate artifacts, or import Phase 1 execution paths. It only emits plan steps and structured goals/errors.
- **Executor:** Only orchestration component that invokes MCP tools (`mcp.tools`). It must not call `Planner` or run intent rules. It uses `interpreted_goal` from the request/state as-is (with a narrow fallback only if that field is missing). Skipping a planned MCP step when earlier steps make it pointless (e.g. all fetches `no_data` before `build_panel`) is still executor-side execution policy, not Phase 1 bypass.
