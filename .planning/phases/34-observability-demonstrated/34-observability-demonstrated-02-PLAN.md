---
phase: 34-observability-demonstrated
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - docs/screenshots/
  - README.md
  - docs/observability.md
autonomous: false
requirements:
  - OBS-02
  - OBS-03
must_haves:
  truths:
    - "The README shows the agent-loop dashboard populated with varied activity."
    - "The dashboard visibly passes its own three health checks — iterating, adapting, being challenged."
    - "The caption states what produced the data, using the framing the user chose."
    - "No existing screenshot or unrelated README claim is disturbed."
  artifacts:
    - path: docs/screenshots/
      provides: "The capture of a populated agent-loop dashboard"
    - path: README.md
      provides: "Observability made visible to a reader who will never clone the repo"
  key_links:
    - from: README.md
      to: docs/observability.md
      via: "the screenshot links to the page explaining how to reproduce it"
      pattern: "observability.md|Populating the dashboard"
---

<objective>
Put the dashboard in front of a reader who will never run the stack.

Purpose: observability is the project's thesis and its best artifact has never been shown. A
reader judges from the README.
Output: a capture of a populated dashboard, placed and captioned.

**Not autonomous.** The caption framing is an open decision in `34-CONTEXT.md`, and the standing
goal requires stopping on README claims about capability.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/34-observability-demonstrated/34-CONTEXT.md
@.planning/phases/34-observability-demonstrated/34-VALIDATION.md
@.planning/phases/34-observability-demonstrated/34-observability-demonstrated-01-PLAN.md
@docs/observability.md
@README.md
@ops/grafana/dashboards/agent-loop.json

<interfaces>
Local stack, from `docs/observability.md`:

| UI | URL |
|---|---|
| Grafana | http://127.0.0.1:3001 — EDGAR ▸ **Agentic Investigation Loop** |
| Prometheus | http://127.0.0.1:9090 — Status ▸ Targets |

Grafana runs with anonymous read access, so capture needs no login.

The dashboard's own health signatures, from `docs/observability.md`:
- median iterations pinned at 1 → the loop is not iterating
- a flat single-tool profile → the loop is not adapting
- only `→ supported` transitions → the loop is not being challenged
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Run the stack, seed it, verify the dashboard is worth capturing</name>
  <files>docs/screenshots/</files>
  <read_first>docs/observability.md
docs/local-stack.md
scripts/seed-agent-activity.py</read_first>
  <behavior>
    - The stack comes up with the observability overlay and Prometheus targets are **up** before
      any conclusion is drawn about the data.
    - The seeder runs long enough for the timeseries panels to have shape.
    - The dashboard is inspected against its own three health signatures before capture. A
      screenshot showing a flat tool profile would advertise the opposite of the claim.
  </behavior>
  <action>Bring up `docker compose -f docker-compose.yml -f docker-compose.observability.yml`
with `EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true` on api and worker. Confirm Prometheus
Status ▸ Targets shows the api and worker scrapes healthy — an unhealthy scrape looks exactly
like missing instrumentation. Run the seeder for long enough that the timeseries panels are
legible. Open Grafana at the agent-loop dashboard and check, explicitly: median iterations is
above 1; the tool mix shows several tools; hypothesis transitions include something other than
`→ supported`; the termination breakdown has more than one reason. If any check fails, extend or
vary the workload rather than capturing it — the screenshot's whole value is that those checks
pass. Then capture, at a width that stays legible in a README.</action>
  <acceptance_criteria>Prometheus targets are healthy before capture.
Median iterations is greater than 1.
The tool-mix panel shows more than one tool.
Hypothesis transitions include a non-`supported` transition.
The termination breakdown shows more than one reason.
A capture exists under `docs/screenshots/`.</acceptance_criteria>
  <verify>
    <manual>Look at the capture as a stranger. If it does not visibly demonstrate an adapting loop, it is not worth publishing — extend the workload instead.</manual>
  </verify>
  <done>There is a capture that demonstrates the claim rather than merely illustrating it.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Place it, with the agreed framing</name>
  <files>README.md
docs/observability.md</files>
  <read_first>README.md
docs/observability.md
.planning/phases/34-observability-demonstrated/34-CONTEXT.md</read_first>
  <behavior>
    - The screenshot sits in Product Screens alongside the existing three, which are untouched.
    - The caption uses the framing the user chose for the open decision, and does not overstate.
    - It links to the reproduction procedure, which is what makes it credible rather than
      decorative.
    - Every unrelated README claim — Stable, Known limits, In progress — is unchanged.
  </behavior>
  <action>Confirm the caption framing decision from `34-CONTEXT.md` has been answered before
writing anything. Add the dashboard to README Product Screens with a caption in the agreed
framing and a link to the "Populating the dashboard" section in `docs/observability.md`. Say
what the dashboard demonstrates — that the loop iterates, adapts its tool choice to the goal,
and is challenged by its own evidence — rather than only naming it. Embed the capture in
`docs/observability.md` too, next to the reading-order section it illustrates. Leave the three
existing screenshots and every unrelated README section exactly as they are.</action>
  <acceptance_criteria>`README.md` embeds the dashboard capture in Product Screens.
The caption matches the framing chosen for the open decision.
`README.md` links to the reproduction procedure.
The three existing screenshots are unchanged.
`README.md` still contains the MCP rate limiting limitation.
`README.md` still contains the CD pipeline limitation.
`docs/observability.md` embeds the capture.</acceptance_criteria>
  <verify>
    <manual>Diff the README and confirm only Product Screens changed.</manual>
  </verify>
  <done>The best artifact in the repository is visible to someone deciding whether to read further.</done>
</task>

</tasks>

<verification>
Full suite, lint, and `python3 -m agentic.evaluation` before commit, per the standing goal.
Confirm no unrelated README section moved.
</verification>

<success_criteria>
A reader who never clones the repository can see that this project's agent loop is instrumented,
that the instrumentation answers real operational questions, and how to reproduce the view
themselves.
</success_criteria>

<output>
After completion, create `.planning/phases/34-observability-demonstrated/34-observability-demonstrated-02-SUMMARY.md`
</output>
