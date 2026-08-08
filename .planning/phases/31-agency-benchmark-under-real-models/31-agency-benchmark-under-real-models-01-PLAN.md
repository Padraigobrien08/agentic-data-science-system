---
phase: 31-agency-benchmark-under-real-models
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - agentic/agent/policy.py
  - agentic/agent/__init__.py
  - backend/agents/prompt_registry.py
  - backend/agents/prompts/agentic_goal_interpreter/1.0.0.md
  - backend/agents/prompts/agentic_hypothesis_generator/1.0.0.md
  - backend/agents/prompts/agentic_experiment_selector/1.0.0.md
  - backend/agents/prompts/agentic_critic/1.0.0.md
  - backend/agents/agentic_model_policy.py
  - tests/agentic/test_policy_prompts.py
  - tests/test_agentic_model_policy_prompts.py
autonomous: true
requirements:
  - AGCY-01
  - AGCY-02
must_haves:
  truths:
    - "The four agentic policy prompts are versioned files on disk under the existing prompt registry, not inline string literals."
    - "`agentic/` still imports nothing from `backend/`: prompts are injected into `ModelAgentPolicy`, never loaded by it."
    - "`python -m agentic.evaluation` still runs offline and deterministic with no provider and no prompt files present."
    - "Policy model calls carry `prompt_id` and `prompt_version` so a benchmark row is traceable to the prompt that produced it."
  artifacts:
    - path: agentic/agent/policy.py
      provides: "`PolicyPrompts` container with standalone defaults, injected into `ModelAgentPolicy`"
    - path: backend/agents/prompts/agentic_experiment_selector/1.0.0.md
      provides: "Versioned selector prompt carrying output schema and candidate-field semantics"
    - path: backend/agents/agentic_model_policy.py
      provides: "Registry-backed prompt loading wired into `build_agent_policy`"
    - path: tests/agentic/test_policy_prompts.py
      provides: "Regression that default prompts keep the domain standalone and injection overrides them"
  key_links:
    - from: backend/agents/agentic_model_policy.py
      to: backend/agents/prompt_registry.py
      via: "build_agent_policy resolves the four policy roles through the registry and injects their bodies"
      pattern: "load_registered_prompt|AGENTIC_POLICY_ROLES|PolicyPrompts"
    - from: agentic/agent/policy.py
      to: agentic/agent/policy.py
      via: "ModelAgentPolicy reads every system prompt from the injected container instead of inline literals"
      pattern: "self._prompts|PolicyPrompts"
---

<objective>
Give the four model-backed policy decisions real, versioned, registry-managed prompts without
breaking the domain purity that makes `agentic/` reusable.

Purpose: the benchmark in 31-02 is only meaningful if the prompts under test are inspectable,
versioned, and traceable. Today they are four one-line string literals.
Output: a `PolicyPrompts` injection seam, four prompt files, registry entries, and wiring.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-agency-benchmark-under-real-models/31-CONTEXT.md
@.planning/phases/31-agency-benchmark-under-real-models/31-VALIDATION.md
@agentic/agent/policy.py
@agentic/agent/fixture_policy.py
@agentic/evaluation/agency.py
@agentic/evaluation/cases.py
@backend/agents/agentic_model_policy.py
@backend/agents/prompt_registry.py
@backend/agents/prompt_loader.py
@backend/agents/prompts/critic/1.2.0.md

<interfaces>
From `agentic/agent/policy.py` (current — four inline prompts to be replaced):
```python
class ModelAgentPolicy:
    def __init__(self, respond: Responder) -> None:
        self._respond = respond

    def _call(self, system: str, user: str, model: type[BaseModel]): ...

    def interpret_goal(self, goal_text, *, capability_summary) -> GoalInterpretation:
        return self._call(
            "Interpret the analytical goal. Reply as GoalInterpretation JSON.", ...)
```

From `backend/agents/prompt_registry.py`:
```python
AGENT_PROMPT_IDS: dict[str, str] = {
    "intent": "edgar.agent.intent",
    ...
}
def load_registered_prompt(role: str, file_version: str) -> RegisteredAgentPrompt: ...
```

From `backend/agents/prompt_loader.py`:
```python
@dataclass(frozen=True)
class AgentPromptTemplate:
    agent: str
    version: str
    template_id: str
    system_body: str
    path: Path
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add the PolicyPrompts injection seam with standalone defaults</name>
  <files>agentic/agent/policy.py
agentic/agent/__init__.py
tests/agentic/test_policy_prompts.py</files>
  <read_first>agentic/agent/policy.py
agentic/agent/__init__.py
.planning/phases/31-agency-benchmark-under-real-models/31-CONTEXT.md</read_first>
  <behavior>
    - `ModelAgentPolicy` reads each system prompt from an injected container, not a literal.
    - Constructed with no prompts, it behaves exactly as it does today, so `agentic/` stays a
      standalone package with no dependency on files that live under `backend/`.
    - Injected prompts fully replace the defaults for all four decisions.
  </behavior>
  <action>In `agentic/agent/policy.py` add a frozen dataclass `PolicyPrompts` with the four
string fields `interpret_goal`, `generate_hypotheses`, `select_experiment`, and `critique`,
each defaulting to the exact literal currently passed at that call site (lines 161-190), so the
no-argument construction is behaviourally identical. Add a module-level
`DEFAULT_POLICY_PROMPTS = PolicyPrompts()`. Change `ModelAgentPolicy.__init__` to
`def __init__(self, respond: Responder, *, prompts: PolicyPrompts | None = None) -> None` and
store `self._prompts = prompts or DEFAULT_POLICY_PROMPTS`. Replace each of the four inline system
strings with the matching `self._prompts.<field>`. Leave `_call`, the typed models, and
`MalformedPolicyResponse` behaviour untouched. Export `PolicyPrompts` and
`DEFAULT_POLICY_PROMPTS` from `agentic/agent/__init__.py`. Create
`tests/agentic/test_policy_prompts.py` asserting that a default-constructed `ModelAgentPolicy`
sends the default system strings, that an injected `PolicyPrompts` replaces all four, and that
`CostAwareModelPolicy`'s superclass call still accepts the keyword.</action>
  <acceptance_criteria>`agentic/agent/policy.py` contains `class PolicyPrompts`.
`agentic/agent/policy.py` contains `DEFAULT_POLICY_PROMPTS`.
`agentic/agent/policy.py` contains `prompts: PolicyPrompts | None = None`.
`agentic/agent/policy.py` contains `self._prompts`.
`agentic/agent/__init__.py` contains `PolicyPrompts`.
`tests/agentic/test_policy_prompts.py` exists.
`python3 -m pytest tests/agentic/test_policy_prompts.py -q --tb=short` passes.
`python3 -m pytest tests/agentic -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/agentic -q --tb=short</automated>
  </verify>
  <done>The policy's prompts are injectable, and the domain still carries working defaults on its own.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Author the four versioned policy prompts and register them</name>
  <files>backend/agents/prompts/agentic_goal_interpreter/1.0.0.md
backend/agents/prompts/agentic_hypothesis_generator/1.0.0.md
backend/agents/prompts/agentic_experiment_selector/1.0.0.md
backend/agents/prompts/agentic_critic/1.0.0.md
backend/agents/prompt_registry.py</files>
  <read_first>backend/agents/prompt_registry.py
backend/agents/prompt_loader.py
backend/agents/prompts/critic/1.2.0.md
agentic/agent/policy.py
agentic/evaluation/agency.py
agentic/evaluation/cases.py
agentic/experiments/tools/general_tools.py</read_first>
  <behavior>
    - Each prompt states its exact output JSON schema and the closed enum values it may use, so a
      model cannot invent an intent or a field name.
    - The selector prompt explains what `falsification` and `expected_information_gain` mean on a
      candidate, because choosing well is the decision the suite scores hardest.
    - Every prompt is explicit that confidence must track evidence strength in *both* directions:
      hedging on an unambiguous signal is as wrong as asserting a trend in noise.
    - Prompts are registered with stable ids that follow the existing `edgar.agent.*` convention.
  </behavior>
  <action>Add four prompt files with `template_id` + `version: 1.0.0` front matter matching the
loader's format. `agentic_goal_interpreter/1.0.0.md`: emit `GoalInterpretation` JSON; enumerate
every `AnalysisIntent` value (`trend`, `comparison`, `correlation`, `anomaly`, `distribution`,
`ranking`, `association`, `profile`, `general`); explain `metric_hint`/`group_hint` must be drawn
from the supplied capability summary, never invented; `direction` is `up`/`down`/null.
`agentic_hypothesis_generator/1.0.0.md`: emit `HypothesisProposals` JSON; hypotheses must be
falsifiable statements over supplied metric and dimension names; `direction` is one of
`up`/`down`/`none`. `agentic_experiment_selector/1.0.0.md`: emit `ExperimentChoice` JSON;
`request_index` must be an index present in the candidate list or null; document that
`falsification: true` marks a candidate that could disconfirm the current strongest claim and
should be preferred, and that `expected_information_gain` is a comparable score; instruct against
re-running a tool already used for the same question. `agentic_critic/1.0.0.md`: emit
`CritiqueProposal` JSON; challenge only a claim that is currently supported and not already
challenged; `falsification_tool` must come from the supplied available-tools list. Every file
carries a calibration paragraph stating both failure modes explicitly. Then in
`backend/agents/prompt_registry.py` add the four entries to `AGENT_PROMPT_IDS` —
`agentic_goal_interpreter: edgar.agentic.goal_interpreter`,
`agentic_hypothesis_generator: edgar.agentic.hypothesis_generator`,
`agentic_experiment_selector: edgar.agentic.experiment_selector`,
`agentic_critic: edgar.agentic.critic` — and add a module constant
`AGENTIC_POLICY_ROLES: tuple[str, ...]` naming those four roles in policy-call order.</action>
  <acceptance_criteria>`backend/agents/prompts/agentic_goal_interpreter/1.0.0.md` exists.
`backend/agents/prompts/agentic_hypothesis_generator/1.0.0.md` exists.
`backend/agents/prompts/agentic_experiment_selector/1.0.0.md` exists.
`backend/agents/prompts/agentic_critic/1.0.0.md` exists.
`backend/agents/prompts/agentic_goal_interpreter/1.0.0.md` contains `version: 1.0.0`.
`backend/agents/prompts/agentic_experiment_selector/1.0.0.md` contains `expected_information_gain`.
`backend/agents/prompts/agentic_experiment_selector/1.0.0.md` contains `falsification`.
`backend/agents/prompt_registry.py` contains `edgar.agentic.goal_interpreter`.
`backend/agents/prompt_registry.py` contains `edgar.agentic.experiment_selector`.
`backend/agents/prompt_registry.py` contains `AGENTIC_POLICY_ROLES`.</acceptance_criteria>
  <verify>
    <automated>python3 -c "from backend.agents.prompt_registry import AGENTIC_POLICY_ROLES, load_registered_prompt; [print(load_registered_prompt(r, '1.0.0').prompt_id) for r in AGENTIC_POLICY_ROLES]"</automated>
  </verify>
  <done>The agentic policy has the same versioned, inspectable prompt surface the EDGAR agents already had.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Load and inject the registered prompts in build_agent_policy</name>
  <files>backend/agents/agentic_model_policy.py
tests/test_agentic_model_policy_prompts.py</files>
  <read_first>backend/agents/agentic_model_policy.py
backend/agents/prompt_registry.py
agentic/agent/policy.py
tests/test_agent_observability.py</read_first>
  <behavior>
    - With a provider configured, the returned policy carries the registry-loaded prompt bodies.
    - The resolved `prompt_id` and `prompt_version` are recorded on the `ModelCall` rows the policy
      produces, matching how the EDGAR agents already persist prompt identity.
    - A missing or unreadable prompt file must not make the loop unrunnable: it falls back to the
      domain defaults and logs, preserving the existing "never raise on misconfiguration" contract.
  </behavior>
  <action>In `backend/agents/agentic_model_policy.py` add
`_load_policy_prompts(version: str = "1.0.0") -> PolicyPrompts` which calls
`load_registered_prompt` for each role in `AGENTIC_POLICY_ROLES`, builds a `PolicyPrompts` from
the four `template.system_body` values, and on `FileNotFoundError`/`ValueError` logs
`agentic.policy.prompts_unavailable` and returns `DEFAULT_POLICY_PROMPTS`. Pass the result into
`CostAwareModelPolicy` via the new `prompts=` keyword in `build_agent_policy`. Extend
`CostTrackingResponder` so the resolved `prompt_id`/`prompt_version` for the active call reach the
`ModelCall` persistence path used by the recorded-completion service, following the pattern the
EDGAR agents already use; keep the mapping explicit rather than positional. Extend the existing
`agentic.policy.model_backed` log event with the loaded prompt versions. Create
`tests/test_agentic_model_policy_prompts.py` covering: a configured provider yields a policy whose
prompts differ from `DEFAULT_POLICY_PROMPTS`; a monkeypatched loader raising `FileNotFoundError`
yields the defaults without raising; and the fixture fallback path when no provider is configured
is unchanged.</action>
  <acceptance_criteria>`backend/agents/agentic_model_policy.py` contains `_load_policy_prompts`.
`backend/agents/agentic_model_policy.py` contains `AGENTIC_POLICY_ROLES`.
`backend/agents/agentic_model_policy.py` contains `prompts=`.
`backend/agents/agentic_model_policy.py` contains `prompts_unavailable`.
`tests/test_agentic_model_policy_prompts.py` exists.
`python3 -m pytest tests/test_agentic_model_policy_prompts.py tests/test_agent_observability.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_agentic_model_policy_prompts.py tests/test_agent_observability.py -q --tb=short</automated>
  </verify>
  <done>A model-backed run now uses versioned prompts whose identity is persisted alongside the call.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/agentic tests/test_agentic_model_policy_prompts.py tests/test_agent_observability.py -q --tb=short` after each task.
Confirm `python3 -m agentic.evaluation` still runs and reports the fixture baseline with no provider configured.
</verification>

<success_criteria>
The four policy decisions are driven by versioned, inspectable, registry-managed prompts whose
identity lands on `ModelCall`, and `agentic/` still runs standalone and offline with no knowledge
that `backend/` exists.
</success_criteria>

<output>
After completion, create `.planning/phases/31-agency-benchmark-under-real-models/31-agency-benchmark-under-real-models-01-SUMMARY.md`
</output>
