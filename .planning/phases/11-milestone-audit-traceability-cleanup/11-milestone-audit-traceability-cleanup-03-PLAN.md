---
phase: 11-milestone-audit-traceability-cleanup
plan: 03
type: execute
wave: 2
depends_on:
  - "11-01"
  - "11-02"
files_modified:
  - .planning/v1.1-MILESTONE-AUDIT.md
  - .planning/STATE.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "The refreshed `v1.1` audit reports `passed` instead of `tech_debt` once summary and Nyquist bookkeeping drift is removed."
    - "The refreshed audit shows no remaining `tech_debt` entries tied to Phase 09, Phase 10, or Phase 06 through Phase 10 validation metadata."
    - "Phase 11 leaves the project state ready for milestone completion rather than leaving archival readiness ambiguous."
  artifacts:
    - path: .planning/v1.1-MILESTONE-AUDIT.md
      provides: "Refreshed milestone audit with clean passed status after traceability fixes"
    - path: .planning/STATE.md
      provides: "Project state aligned with the rerun audit outcome"
  key_links:
    - from: .planning/v1.1-MILESTONE-AUDIT.md
      to: .planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
      via: "audit no longer depends on manual interpretation once summary requirement metadata is repaired"
      pattern: "status: passed|tech_debt: []"
    - from: .planning/v1.1-MILESTONE-AUDIT.md
      to: .planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
      via: "audit no longer reports Nyquist partial phases once validation bookkeeping is repaired"
      pattern: "compliant_phases|overall: compliant"
---

<objective>
Refresh the `v1.1` milestone audit after the metadata cleanup and leave project state aligned with clean archival readiness.

Purpose: close the loop on Phase 11 by proving the milestone audit is now free of traceability debt.
Output: passed audit report, preserved cross-phase regression evidence, and project state ready for milestone completion.
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
@.planning/phases/11-milestone-audit-traceability-cleanup/11-milestone-audit-traceability-cleanup-01-PLAN.md
@.planning/phases/11-milestone-audit-traceability-cleanup/11-milestone-audit-traceability-cleanup-02-PLAN.md
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
  <name>Task 1: Re-run and rewrite the milestone audit so `v1.1` passes cleanly</name>
  <files>.planning/v1.1-MILESTONE-AUDIT.md
.planning/STATE.md</files>
  <read_first>.planning/v1.1-MILESTONE-AUDIT.md
.planning/STATE.md
.planning/ROADMAP.md
.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md
.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md</read_first>
  <behavior>
    - The milestone audit must refresh from the cleaned planning metadata and report `passed`.
    - The rerun audit must preserve the already-established requirement, integration, and flow coverage rather than weakening the result.
    - Project state should end this task clearly ready to complete the milestone.
  </behavior>
  <action>Rewrite `.planning/v1.1-MILESTONE-AUDIT.md` from the updated planning artifacts so its frontmatter contains the exact values `status: passed`, `gaps.requirements: []`, `gaps.integration: []`, `gaps.flows: []`, `tech_debt: []`, `nyquist.compliant_phases: [06, 07, 08, 09, 10]`, `nyquist.partial_phases: []`, `nyquist.missing_phases: []`, and `nyquist.overall: compliant`. Update the markdown body so the Outcome, Scorecard, Requirement Coverage, Phase Verification Summary, Cross-Phase Integration, Flow Audit, and Conclusion sections reflect a clean pass with no residual metadata-drift debt. Preserve the audit-time regression evidence by re-running the exact backend slice `python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_live_hybrid_execution.py tests/test_trace_summary_api.py tests/test_artifact_content_delivery.py tests/test_backend_health.py -q --tb=short` and the exact frontend slice `cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx`, then record their passing results in the audit body. Update `.planning/STATE.md` so the current focus returns to milestone completion rather than Phase 11 planning once the refreshed audit passes.</action>
  <acceptance_criteria>`.planning/v1.1-MILESTONE-AUDIT.md` contains `status: passed`.
`.planning/v1.1-MILESTONE-AUDIT.md` contains `tech_debt: []`.
`.planning/v1.1-MILESTONE-AUDIT.md` contains `compliant_phases: [06, 07, 08, 09, 10]`.
`.planning/v1.1-MILESTONE-AUDIT.md` contains `partial_phases: []`.
`.planning/v1.1-MILESTONE-AUDIT.md` contains `overall: compliant`.
`.planning/v1.1-MILESTONE-AUDIT.md` does not contain `status: tech_debt`.
`.planning/STATE.md` contains `Ready to Complete Milestone` or another explicit milestone-closeout status.
`python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_live_hybrid_execution.py tests/test_trace_summary_api.py tests/test_artifact_content_delivery.py tests/test_backend_health.py -q --tb=short` passes.
`cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_policy_contract.py tests/test_evaluation_runner_policy.py tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_live_hybrid_execution.py tests/test_trace_summary_api.py tests/test_artifact_content_delivery.py tests/test_backend_health.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx</automated>
  </verify>
  <done>The milestone audit is refreshed to `passed`, and project state is ready for final milestone completion.</done>
</task>

</tasks>

<verification>
Run the full audit regression slice after refreshing the audit so Phase 11 proves the milestone is clean on both planning metadata and preserved cross-phase behavior.
</verification>

<success_criteria>
Phase 11 closes cleanly once the refreshed `v1.1` audit passes, no traceability debt remains in the audit report, and the project state points back to milestone completion.
</success_criteria>

<output>
After completion, create `.planning/phases/11-milestone-audit-traceability-cleanup/11-milestone-audit-traceability-cleanup-03-SUMMARY.md`
</output>
