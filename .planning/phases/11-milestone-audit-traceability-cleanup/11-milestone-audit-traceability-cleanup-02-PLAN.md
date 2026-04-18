---
phase: 11-milestone-audit-traceability-cleanup
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
  - .planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
  - .planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
  - .planning/phases/09-evaluation-control-plane/09-VALIDATION.md
  - .planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Phase 06 through Phase 10 validation files reflect completed execution state instead of stale planned or researched bookkeeping."
    - "Nyquist bookkeeping no longer reports pending task rows or unchecked Wave 0 items for already-verified phases."
    - "The updated validation docs remain consistent with the already-passed phase verification reports."
  artifacts:
    - path: .planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
      provides: "Completed validation bookkeeping for Phase 06"
    - path: .planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
      provides: "Completed validation bookkeeping for Phase 10"
  key_links:
    - from: .planning/phases/06-validation-boundaries-and-policy/06-VERIFICATION.md
      to: .planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
      via: "validation bookkeeping must match the already-green execution and verification state"
      pattern: "status: complete|wave_0_complete: true|Approval: complete"
    - from: .planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
      to: .planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
      via: "validation bookkeeping must stop advertising stale pending work after the phase passed"
      pattern: "status: complete|wave_0_complete: true|✅ green"
---

<objective>
Reconcile Phase 06 through Phase 10 validation and Nyquist bookkeeping with the fact that those phases already executed and verified successfully.

Purpose: remove the remaining Nyquist-related metadata debt called out by the milestone audit.
Output: completed validation docs for Phases 06 through 10 with no stale pending or unchecked state.
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
@.planning/phases/01-run-isolation/01-VALIDATION.md
@.planning/phases/02-worker-resilience/02-VALIDATION.md
@.planning/phases/06-validation-boundaries-and-policy/06-VERIFICATION.md
@.planning/phases/07-remote-artifact-storage-contract/07-VERIFICATION.md
@.planning/phases/08-summary-first-large-trace-views/08-VERIFICATION.md
@.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
@.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
@.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
@.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
@.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
@.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
@.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Mark Phase 06 through Phase 10 validation docs as completed and green</name>
  <files>.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md</files>
  <read_first>.planning/v1.1-MILESTONE-AUDIT.md
.planning/phases/01-run-isolation/01-VALIDATION.md
.planning/phases/02-worker-resilience/02-VALIDATION.md
.planning/phases/06-validation-boundaries-and-policy/06-VERIFICATION.md
.planning/phases/07-remote-artifact-storage-contract/07-VERIFICATION.md
.planning/phases/08-summary-first-large-trace-views/08-VERIFICATION.md
.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md</read_first>
  <behavior>
    - All touched validation files must present completed state rather than planned or researched state.
    - Every per-task verification row in the touched files must stop showing `⬜ pending`.
    - Every Wave 0 checklist in the touched files must stop showing unchecked items once the phase is already verified green.
  </behavior>
  <action>Update the five touched validation files so each one contains `status: complete` and `wave_0_complete: true` in frontmatter. Replace every `⬜ pending` status cell in their per-task verification tables with `✅ green`. Replace every unchecked Wave 0 list item (`- [ ]`) in those five files with checked items (`- [x]`). Replace the final sign-off line in each touched file with the exact string `**Approval:** complete`. Do not alter the quick or full command coverage unless a command string is objectively wrong; this plan is bookkeeping cleanup, not validation redesign.</action>
  <acceptance_criteria>`.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md` contains `status: complete`.
`.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md` contains `status: complete`.
`.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md` contains `status: complete`.
`.planning/phases/09-evaluation-control-plane/09-VALIDATION.md` contains `status: complete`.
`.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md` contains `status: complete`.
Each touched validation file contains `wave_0_complete: true`.
Each touched validation file contains `**Approval:** complete`.
No touched validation file contains `⬜ pending`.
No touched validation file contains `- [ ]`.
`python3 - <<'PY'
from pathlib import Path
for phase in ['06', '07', '08', '09', '10']:
    text = next(Path('.planning/phases').glob(f'{phase}-*/*-VALIDATION.md')).read_text()
    assert 'status: complete' in text
    assert 'wave_0_complete: true' in text
    assert '⬜ pending' not in text
    assert '- [ ]' not in text
    assert '**Approval:** complete' in text
print('validation-bookkeeping ok')
PY` prints `validation-bookkeeping ok`.</acceptance_criteria>
  <verify>
    <automated>python3 - <<'PY'
from pathlib import Path
for phase in ['06', '07', '08', '09', '10']:
    text = next(Path('.planning/phases').glob(f'{phase}-*/*-VALIDATION.md')).read_text()
    assert 'status: complete' in text
    assert 'wave_0_complete: true' in text
    assert '⬜ pending' not in text
    assert '- [ ]' not in text
    assert '**Approval:** complete' in text
print('validation-bookkeeping ok')
PY</automated>
  </verify>
  <done>Phase 06 through Phase 10 validation docs now advertise truthful completed Nyquist bookkeeping instead of stale pending state.</done>
</task>

</tasks>

<verification>
Run the validation-bookkeeping check after the task so the milestone audit can stop marking Phase 06 through Phase 10 as partial on Nyquist metadata alone.
</verification>

<success_criteria>
Phase 11 removes the Nyquist bookkeeping debt once all touched Phase 06 through Phase 10 validation docs present completed, green, and checked-off state consistent with their verification reports.
</success_criteria>

<output>
After completion, create `.planning/phases/11-milestone-audit-traceability-cleanup/11-milestone-audit-traceability-cleanup-02-SUMMARY.md`
</output>
