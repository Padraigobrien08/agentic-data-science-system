---
phase: 13-analyst-prompt-routing
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - edgar_project/orchestration/intent.py
  - edgar_project/orchestration/planner.py
  - edgar_project/orchestration/prompt_scope.py
  - tests/orchestration/test_intent.py
  - tests/orchestration/test_planner.py
  - tests/orchestration/test_planner_alignment_regression.py
  - tests/orchestration/test_prompt_scope.py
autonomous: true
requirements:
  - PROMPT-01
  - PROMPT-02
must_haves:
  truths:
    - "Normal analyst thesis prompts such as `Analyze MSFT over the last 8 quarters and tell me whether margin pressure is temporary or structural` no longer fail the deterministic intent gate."
    - "Peer routing accepts explicit relative language such as `vs`, `versus`, `relative to`, `weaker`, `stronger`, and `underperform`, but does not infer peer mode from multiple tickers alone."
    - "If the prompt names a ticker subset already in the workspace, the effective run scope narrows to that subset; if it names out-of-scope symbols, the planner records that fact for later guidance instead of silently expanding."
  artifacts:
    - path: edgar_project/orchestration/intent.py
      provides: "Broadened deterministic eligibility rules for analyst-language routing"
    - path: edgar_project/orchestration/prompt_scope.py
      provides: "Deterministic prompt-scope extraction for in-workspace ticker narrowing and out-of-scope detection"
    - path: tests/orchestration/test_prompt_scope.py
      provides: "Regression coverage for prompt-named subset behavior"
  key_links:
    - from: edgar_project/orchestration/prompt_scope.py
      to: edgar_project/orchestration/planner.py
      via: "Planner uses extracted in-scope tickers as the effective orchestration scope before plan-template selection"
      pattern: "matched_workspace_tickers|out_of_scope_tickers|effective_tickers"
    - from: edgar_project/orchestration/intent.py
      to: tests/orchestration/test_intent.py
      via: "User-facing phrases are locked as deterministic supported-intent examples"
      pattern: "temporary or structural|versus|weaker|underperform"
    - from: tests/orchestration/test_planner_alignment_regression.py
      to: edgar_project/orchestration/planner.py
      via: "Live prompt phrasing still lands on the correct plan template and preference interpretation"
      pattern: "trend_deterioration|peer_comparison"
---

<objective>
Expand the deterministic routing foundation so ordinary analyst language and prompt-named ticker subsets map cleanly into the existing supported orchestration templates.

Purpose: satisfy `PROMPT-01` and `PROMPT-02` at the orchestration core before adding preview/guidance or chat integration.
Output: broadened deterministic intent eligibility, prompt-scoped ticker narrowing, and regression coverage tied to live user phrasing.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
@.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
@.planning/phases/13-analyst-prompt-routing/13-VALIDATION.md
@edgar_project/orchestration/intent.py
@edgar_project/orchestration/goal_preferences.py
@edgar_project/orchestration/planner.py
@edgar_project/orchestration/plan_templates.py
@tests/orchestration/test_intent.py
@tests/orchestration/test_planner.py
@tests/orchestration/test_planner_alignment_regression.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add deterministic prompt-scope narrowing for in-workspace ticker subsets</name>
  <files>edgar_project/orchestration/prompt_scope.py
edgar_project/orchestration/planner.py
tests/orchestration/test_prompt_scope.py
tests/orchestration/test_planner.py</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
.planning/phases/13-analyst-prompt-routing/13-VALIDATION.md
edgar_project/orchestration/planner.py
edgar_project/orchestration/goal_preferences.py
tests/orchestration/test_planner.py</read_first>
  <behavior>
    - Prompt text that explicitly names one or more ticker symbols already present in `OrchestrationInput.tickers` must narrow the effective run scope to only those named symbols.
    - Prompt text that names ticker symbols outside `OrchestrationInput.tickers` must not silently expand scope.
    - Scope extraction must remain deterministic and ticker-symbol-based; Phase 13 must not introduce fuzzy company-name lookup.
  </behavior>
  <action>Create a new module `edgar_project/orchestration/prompt_scope.py` with a pure helper that takes `analysis_goal` plus `workspace_tickers` and returns three explicit fields: `matched_workspace_tickers`, `out_of_scope_tickers`, and `effective_tickers`. Use uppercase ticker-token extraction only: split `analysis_goal` on non-alphanumeric boundaries, keep tokens that match `workspace_tickers`, and separately collect uppercase ticker-like tokens that were named in the goal but are not present in `workspace_tickers`. In `edgar_project/orchestration/planner.py`, call that helper before plan-template selection. If `matched_workspace_tickers` is non-empty, build the plan with only those tickers. If `out_of_scope_tickers` is non-empty, keep that information available for the later guidance layer instead of silently adding those symbols to the run. Add `tests/orchestration/test_prompt_scope.py` that covers an in-scope narrowing example such as workspace `['AAPL', 'MSFT', 'NVDA']` with goal `Analyze MSFT over the last 8 quarters`, and an out-of-scope example such as the same workspace with goal `Analyze TSLA margin pressure`. Extend `tests/orchestration/test_planner.py` so the planner’s run-pipeline or granular steps use the narrowed ticker list when a prompt names an in-scope subset.</action>
  <acceptance_criteria>`edgar_project/orchestration/prompt_scope.py` exists.
`edgar_project/orchestration/prompt_scope.py` contains `matched_workspace_tickers`.
`edgar_project/orchestration/prompt_scope.py` contains `out_of_scope_tickers`.
`edgar_project/orchestration/prompt_scope.py` contains `effective_tickers`.
`edgar_project/orchestration/planner.py` contains `prompt_scope`.
`tests/orchestration/test_prompt_scope.py` exists.
`tests/orchestration/test_prompt_scope.py` contains `Analyze MSFT over the last 8 quarters`.
`tests/orchestration/test_prompt_scope.py` contains `Analyze TSLA margin pressure`.
`tests/orchestration/test_planner.py` contains `effective_tickers` or `MSFT`.
`python3 -m pytest tests/orchestration/test_prompt_scope.py tests/orchestration/test_planner.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/orchestration/test_prompt_scope.py tests/orchestration/test_planner.py -q --tb=short</automated>
  </verify>
  <done>The planner can now deterministically narrow to prompt-named in-workspace tickers and record out-of-scope symbols for later guidance.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Broaden deterministic analyst-language and peer-language routing without changing the intent enum</name>
  <files>edgar_project/orchestration/intent.py
edgar_project/orchestration/planner.py
tests/orchestration/test_intent.py
tests/orchestration/test_planner.py
tests/orchestration/test_planner_alignment_regression.py</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
edgar_project/orchestration/intent.py
edgar_project/orchestration/goal_preferences.py
edgar_project/orchestration/plan_templates.py
tests/orchestration/test_intent.py
tests/orchestration/test_planner_alignment_regression.py</read_first>
  <behavior>
    - Thesis-style business prompts should enter the existing supported routing surface without requiring anomaly keywords.
    - Peer routing should recognize explicit comparison words like `vs`, `versus`, `relative to`, `weaker`, `stronger`, and `underperform`.
    - Multiple tickers with no comparison language must not route as `peer_report`.
  </behavior>
  <action>Extend `edgar_project/orchestration/intent.py` so `interpret_goal_intent(...)` admits analyst-language business cues into the existing `OrchestrationIntent.anomaly_analysis` bucket when the goal contains deterministic deterioration/trend evidence such as `margin pressure`, `temporary or structural`, `cash flow quality`, `slipping`, `persistent`, `sustained`, `last eight quarters`, or named metric/time cues already represented in `goal_preferences.py`. Extend peer detection so prompts containing `vs`, `versus`, `relative to`, `weaker`, `stronger`, `underperform`, `outperform`, or `which company` can resolve to `OrchestrationIntent.peer_report` when paired with comparison framing, but do not let multiple tickers alone trigger peer routing. Keep `OrchestrationIntent` unchanged. Add and update tests for these exact phrases in `tests/orchestration/test_intent.py`, and extend `tests/orchestration/test_planner_alignment_regression.py` with at least two new product-facing regression anchors: `Analyze MSFT over the last 8 quarters and tell me whether margin pressure is temporary or structural` and `Which company is weaker, AAPL or MSFT, on free cash flow quality?`. Ensure those planner regressions still land on the existing `trend_deterioration` and `peer_comparison` templates respectively.</action>
  <acceptance_criteria>`edgar_project/orchestration/intent.py` contains `temporary or structural`.
`edgar_project/orchestration/intent.py` contains `cash flow quality`.
`edgar_project/orchestration/intent.py` contains `versus` or `vs`.
`edgar_project/orchestration/intent.py` contains `weaker`.
`tests/orchestration/test_intent.py` contains `temporary or structural`.
`tests/orchestration/test_intent.py` contains `Which company is weaker`.
`tests/orchestration/test_planner_alignment_regression.py` contains `Analyze MSFT over the last 8 quarters and tell me whether margin pressure is temporary or structural`.
`tests/orchestration/test_planner_alignment_regression.py` contains `Which company is weaker, AAPL or MSFT`.
`tests/orchestration/test_planner.py` contains a case proving multiple tickers alone do not force `peer_report`.
`python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py -q --tb=short</automated>
  </verify>
  <done>Ordinary analyst phrasing and peer-relative language route into the correct existing templates without changing the trust boundary or the intent enum.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/orchestration/test_prompt_scope.py tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py -q --tb=short` after completing both tasks.
</verification>

<success_criteria>
Phase 13 has a sound routing core once the deterministic planner accepts normal analyst phrasing, narrows prompt-named ticker subsets correctly, and preserves the explicit peer-language boundary.
</success_criteria>

<output>
After completion, create `.planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-01-SUMMARY.md`
</output>
