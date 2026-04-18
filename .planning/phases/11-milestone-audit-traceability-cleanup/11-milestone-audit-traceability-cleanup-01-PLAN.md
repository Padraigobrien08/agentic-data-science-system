---
phase: 11-milestone-audit-traceability-cleanup
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
  - .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
  - .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md
  - .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md
  - .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
  - .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Phase 09 summary frontmatter exposes `VALID-01` and `EVAL-01` through truthful `requirements-completed` entries."
    - "Phase 10 summary frontmatter exposes `EVAL-02` and `OPS-01` through truthful `requirements-completed` entries."
    - "Summary frontmatter and summary body text stay aligned with the already-passed verification reports instead of inventing new scope."
  artifacts:
    - path: .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
      provides: "Phase 09 summary metadata now records the supported evaluation requirements it already satisfied"
    - path: .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md
      provides: "Phase 10 summary metadata now records both canonical child-run and ops-truthfulness requirements"
  key_links:
    - from: .planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
      to: .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
      via: "summary frontmatter must mirror the requirement IDs already satisfied in verification"
      pattern: "VALID-01|EVAL-01|requirements-completed"
    - from: .planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
      to: .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md
      via: "summary frontmatter must mirror the requirement IDs already satisfied in verification"
      pattern: "EVAL-02|OPS-01|requirements-completed"
---

<objective>
Repair the Phase 09 and Phase 10 summary frontmatter so milestone requirement cross-checks no longer depend on manual audit interpretation.

Purpose: restore automated traceability between executed summaries and already-passed verification reports.
Output: updated `requirements-completed` metadata across the touched summary files with no product-scope changes.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/v1.1-MILESTONE-AUDIT.md
@.planning/phases/11-milestone-audit-traceability-cleanup/11-CONTEXT.md
@.planning/phases/11-milestone-audit-traceability-cleanup/11-VALIDATION.md
@.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
@.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
@.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
@.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
@.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md
@.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md
@.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
@.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Reconcile Phase 09 and Phase 10 summary requirement metadata</name>
  <files>.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md</files>
  <read_first>.planning/v1.1-MILESTONE-AUDIT.md
.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md</read_first>
  <behavior>
    - Phase 09 summary frontmatter must expose the requirement IDs already satisfied by the supported evaluation control-plane work.
    - Phase 10 summary frontmatter must expose the requirement IDs already satisfied by the live or hybrid hardening work.
    - Summary bodies stay semantically unchanged except where a small wording adjustment is required to keep frontmatter and prose truthful together.
  </behavior>
  <action>Update the exact `requirements-completed` lines in the touched summary frontmatter to these values: `09-evaluation-control-plane-01-SUMMARY.md` -> `requirements-completed: [EVAL-01]`; `09-evaluation-control-plane-02-SUMMARY.md` -> `requirements-completed: [VALID-01, EVAL-01]`; `09-evaluation-control-plane-03-SUMMARY.md` -> `requirements-completed: [VALID-01, EVAL-01]`; `10-live-hybrid-execution-hardening-01-SUMMARY.md` -> `requirements-completed: [EVAL-02]`; `10-live-hybrid-execution-hardening-02-SUMMARY.md` -> `requirements-completed: [EVAL-02]`; `10-live-hybrid-execution-hardening-03-SUMMARY.md` -> `requirements-completed: [EVAL-02, OPS-01]`. Do not add or remove other requirement IDs. Do not widen the accomplishment or decision sections beyond what the existing verification reports already proved.</action>
  <acceptance_criteria>`.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md` contains `requirements-completed: [EVAL-01]`.
`.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md` contains `requirements-completed: [VALID-01, EVAL-01]`.
`.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md` contains `requirements-completed: [VALID-01, EVAL-01]`.
`.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md` contains `requirements-completed: [EVAL-02]`.
`.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md` contains `requirements-completed: [EVAL-02]`.
`.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md` contains `requirements-completed: [EVAL-02, OPS-01]`.
`python3 - <<'PY'
from pathlib import Path
import re
def collect(phase_dir):
    reqs=set()
    for path in Path(phase_dir).glob('*-SUMMARY.md'):
        text=path.read_text()
        match=re.search(r'^requirements-completed:\\s*\\[([^\\]]*)\\]', text, re.M)
        if match:
            reqs.update(item.strip() for item in match.group(1).split(',') if item.strip())
    return reqs
assert {'VALID-01', 'EVAL-01'} <= collect('.planning/phases/09-evaluation-control-plane')
assert {'EVAL-02', 'OPS-01'} <= collect('.planning/phases/10-live-hybrid-execution-hardening')
print('summary-frontmatter ok')
PY` prints `summary-frontmatter ok`.</acceptance_criteria>
  <verify>
    <automated>python3 - <<'PY'
from pathlib import Path
import re
def collect(phase_dir):
    reqs=set()
    for path in Path(phase_dir).glob('*-SUMMARY.md'):
        text=path.read_text()
        match=re.search(r'^requirements-completed:\\s*\\[([^\\]]*)\\]', text, re.M)
        if match:
            reqs.update(item.strip() for item in match.group(1).split(',') if item.strip())
    return reqs
assert {'VALID-01', 'EVAL-01'} <= collect('.planning/phases/09-evaluation-control-plane')
assert {'EVAL-02', 'OPS-01'} <= collect('.planning/phases/10-live-hybrid-execution-hardening')
print('summary-frontmatter ok')
PY</automated>
  </verify>
  <done>Phase 09 and Phase 10 summary metadata now matches the requirement coverage their verification reports already proved.</done>
</task>

</tasks>

<verification>
Run the summary-frontmatter union check after the task so Phase 09 and Phase 10 no longer depend on manual audit interpretation for requirement coverage.
</verification>

<success_criteria>
Phase 11 can trust the summary-side requirement cross-check once the touched Phase 09 and Phase 10 summaries expose the exact requirement IDs already satisfied in verification.
</success_criteria>

<output>
After completion, create `.planning/phases/11-milestone-audit-traceability-cleanup/11-milestone-audit-traceability-cleanup-01-SUMMARY.md`
</output>
