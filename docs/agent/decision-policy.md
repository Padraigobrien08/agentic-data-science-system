# Decision Policy (AgentPolicy)

`AgentPolicy` (`agentic/agent/policy.py`) is the model-backed decision surface of
the loop. It cleanly separates the two responsibilities: **the policy interprets
and chooses; the deterministic experiment registry computes.** No numeric result
is ever produced by a policy.

## What the policy decides (and what it never does)

The policy is consulted for exactly four kinds of decision — each one model call
with a defined input and a typed, validated output:

| Method | Input | Typed output |
|---|---|---|
| `interpret_goal(goal_text, capability_summary)` | goal + dataset capabilities | `GoalInterpretation` (intent, metric/group hints, direction) |
| `generate_hypotheses(interpretation, metric_names, dimension_names)` | interpretation + schema | `HypothesisProposals` (hypotheses + questions) |
| `select_experiment(goal_summary, candidates)` | goal + **already-validated** candidate experiments | `ExperimentChoice` (index into candidates) |
| `critique(strongest_claim, available_tools)` | strongest claim + unused tools | `CritiqueProposal` (challenge + falsification tool) |

The policy **never**: runs a tool, computes a statistic, sets an evidence
strength, or decides a hypothesis status — those are deterministic
(`EvidenceUpdater`, `HypothesisUpdater`, the experiment registry). The planner
only ever offers the policy candidates that already passed capability + parameter
validation, so the policy cannot select an invalid experiment.

## Typed I/O and safe failure

Every policy output is a Pydantic model (`GoalInterpretation`,
`HypothesisProposals`, `ExperimentChoice`, `CritiqueProposal`). This makes every
model call a defined-input/typed-output contract.

`ModelAgentPolicy` wraps a JSON responder `(system, user) -> str`:

1. parse the response as JSON — bad JSON → `MalformedPolicyResponse`;
2. `model_validate` into the expected type — schema violation → `MalformedPolicyResponse`.

`MalformedPolicyResponse` (a subclass of `AgentPolicyError`) is caught by the
loop, which terminates safely with reason `error`, still synthesizes an
(insufficient) conclusion, and sets status `failed` — never a crash or a partial,
untyped result (`test_malformed_model_response_fails_safely`).

## Two interchangeable implementations

Because `AgentPolicy` is a `Protocol`, model-backed and deterministic policies are
drop-in interchangeable:

- **`FixtureAgentPolicy`** (`fixture_policy.py`) — deterministic, rule-based, no
  LLM. Intent is keyword-derived from the goal; hypotheses follow from intent;
  selection prefers falsification candidates then highest expected information
  gain (deterministic tie-break by index); critique challenges a supported,
  not-yet-challenged claim with an unused tool. Used by every integration test so
  they are fully deterministic and offline.
- **`ModelAgentPolicy`** — backed by any JSON responder (e.g. an LLM), with the
  validation/safe-failure behavior above.

`InvestigationLoop(policy=...)` accepts either; the default is `FixtureAgentPolicy`.

## How intent drives divergent execution

`interpret_goal` returns an `AnalysisIntent` (trend / comparison / correlation /
anomaly / distribution / ranking / association / profile / general). The
deterministic `InvestigationPlanner` maps intent to an ordered candidate tool set
(`INTENT_TOOLS`, plus `EDGAR_INTENT_TOOLS` for EDGAR panels). That mapping is why
a trend goal and a comparison goal run different experiments — the divergence is
in deterministic planning keyed on the policy's typed interpretation, not in
free-form model behavior.

## Selection and adaptivity

`select_experiment` receives candidate **summaries** (`index`, `tool_name`,
`purpose`, `expected_information_gain`, `falsification`). The fixture policy
returns the falsification candidate if present, else the highest information-gain
candidate. Because the planner rebuilds candidates each iteration from current
state (excluding executed tools, adding falsification candidates from open
critiques), the policy's choices depend on intermediate results — the loop adapts.

## Provenance

Every entity a component produces carries `Provenance(source=agent_llm,
agent_id=<component>)` for policy-driven decisions, or
`source=deterministic_tool` for experiment results — so the audit trail records
which model call or deterministic tool produced each hypothesis, evidence item,
decision, critique, and conclusion.
