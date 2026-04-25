import Link from "next/link";

import { FinalReportWithEvidence } from "@/components/runs/final-report-with-evidence";
import { CriticFindingsCard } from "@/components/transparency/critic-findings-card";
import { ModelCallSummaryCard } from "@/components/transparency/model-call-summary-card";
import { PhaseStatusChip } from "@/components/transparency/phase-status-chip";
import { PlanningOutputCard } from "@/components/transparency/planning-output-card";
import { ReportEvidencePanel } from "@/components/transparency/report-evidence-panel";
import { StepStatusTimeline } from "@/components/transparency/step-status-timeline";
import { MetaRow, Section, StatusBadge } from "@/components/ui/technical";
import { InterpretedGoalPanel } from "@/components/trace/interpreted-goal-panel";
import {
  collectPlanAlignmentFindings,
  PlanAlignmentCallout,
} from "@/components/trace/plan-alignment-callout";
import { PlanningTransparencyPanel } from "@/components/trace/planning-transparency-panel";
import { ContextTransparencyPanel } from "@/components/trace/context-transparency-panel";
import { RunGapOverview } from "@/components/trace/run-gap-overview";
import { LlmPhaseUsageCard } from "@/components/trace/llm-phase-usage-card";
import { indexModelCallsById, stringArrayFromUnknown } from "@/lib/agent-transparency";
import type {
  AnalysisRunStatus,
  ArtifactMetadata,
  ModelCallApiItem,
  RunStepDetail,
  RunTransparencySummary,
} from "@/lib/api/types";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type {
  ParsedOrchestrationOutput,
  UserFacingReport,
} from "@/lib/orchestration-output";
import {
  deriveExecutionPlan,
  toolResultByOrder,
} from "@/lib/run-trace-derive";

/** Jump-nav targets only — avoid stacking scroll-margin on nested panels. */
const scrollAnchor = "scroll-mt-20";
const panelDense = "shadow-sm";
const auditBody = "p-2.5 sm:p-3";
const auditHeader = "py-1.5";

type Props = {
  projectId: string;
  runId: string;
  orch: ParsedOrchestrationOutput | null;
  ai: ParsedAiAgents | null;
  steps: RunStepDetail[];
  artifacts: ArtifactMetadata[];
  userFacingReport: UserFacingReport | null;
  modelCalls: ModelCallApiItem[];
  /** When true, omit link to full trace from timeline footer. */
  compactTraceLink?: boolean;
  runStatus?: AnalysisRunStatus;
  runErrorSummary?: string | null;
  runTransparency?: RunTransparencySummary | null;
};

function runNeedsAttention(
  status: AnalysisRunStatus | undefined,
  errorSummary: string | null | undefined,
): boolean {
  if (errorSummary?.trim()) return true;
  if (!status) return false;
  return (
    status === "error" ||
    status === "cancelled" ||
    status === "partial_success" ||
    status === "no_data"
  );
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function phaseOutput(meta: unknown): Record<string, unknown> | null {
  if (!isRecord(meta)) return null;
  const po = meta.phase_output;
  return isRecord(po) ? po : null;
}

/**
 * Deep-dive audit body: goal → plan → execution → timeline → model calls → artifacts → agents → report → prompts/usage.
 * Jump nav ids are centralized in ``deep-dive-nav-config``.
 */
export function RunTraceExperience({
  projectId,
  runId,
  orch,
  ai,
  steps,
  artifacts,
  userFacingReport,
  modelCalls,
  compactTraceLink,
  runStatus,
  runErrorSummary,
  runTransparency,
}: Props) {
  const tr = ai?.traceability;
  const lps = orch?.llm_phases_summary;
  const planRows = deriveExecutionPlan(orch, ai);
  const resultByOrder = toolResultByOrder(orch?.tool_results_summary);
  const intentPo = phaseOutput(ai?.intent);
  const planPo = phaseOutput(ai?.planning);
  const criticPo = phaseOutput(ai?.critic);
  const reportPo = phaseOutput(ai?.report);
  const blockingForOverview =
    tr?.critic?.blocking_caveats && tr.critic.blocking_caveats.length > 0
      ? tr.critic.blocking_caveats
      : stringArrayFromUnknown(criticPo?.issues, 12);
  const criticConfidenceOverview =
    (typeof criticPo?.overall_confidence === "string" ? criticPo.overall_confidence : null) ??
    (typeof tr?.critic?.overall_confidence === "string" ? tr.critic.overall_confidence : null);
  const mcById = indexModelCallsById(modelCalls);
  const planningMc =
    typeof ai?.planning?.model_call_id === "string"
      ? (mcById.get(ai.planning.model_call_id) ?? null)
      : null;
  const criticMcId = lps?.critic?.model_call_id ?? ai?.critic?.model_call_id;
  const criticMc =
    typeof criticMcId === "string" ? (mcById.get(criticMcId) ?? null) : null;
  const reportMcId = lps?.report?.model_call_id ?? ai?.report?.model_call_id;
  const reportMc =
    typeof reportMcId === "string" ? (mcById.get(reportMcId) ?? null) : null;
  const toolNamesHint = planRows.map((r) => r.tool_name).filter(Boolean);

  const intentGoal = ai?.intent?.interpreted_goal ?? orch?.interpreted_goal;
  const hasStructuredIntent =
    intentPo &&
    (intentPo.goal_code != null ||
      intentPo.description_excerpt ||
      intentPo.user_goal_excerpt);
  const planningTransparency =
    (intentPo && isRecord(intentPo.planning_transparency) && intentPo.planning_transparency) ||
    tr?.intent?.planning_transparency ||
    tr?.planning?.planning_transparency ||
    null;

  const { findings: planAlignmentFindings, codes: planAlignmentCodes } =
    collectPlanAlignmentFindings(criticPo, tr?.critic);

  return (
    <div className="space-y-3 text-[13px] leading-snug">
      {runNeedsAttention(runStatus, runErrorSummary) ? (
        <div
          className={`rounded border p-2.5 ${
            runStatus === "partial_success"
              ? "border-amber-300 bg-amber-50/80 dark:border-amber-800 dark:bg-amber-950/30"
              : "border-red-300 bg-red-50/80 dark:border-red-900 dark:bg-red-950/35"
          }`}
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--foreground)]">
            Run status & errors
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {runStatus ? <StatusBadge status={runStatus} variant="friendly" /> : null}
          </div>
          {runErrorSummary?.trim() ? (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-red-900 dark:text-red-100">
              {runErrorSummary}
            </pre>
          ) : null}
        </div>
      ) : null}

      <section id="run-overview" className={`${scrollAnchor} space-y-2`}>
        <RunGapOverview
          orch={orch}
          traceability={tr}
          blockingCaveats={blockingForOverview}
          overallConfidence={criticConfidenceOverview}
        />
      </section>

      <div id="run-goal-plan" className={`${scrollAnchor} space-y-3`}>
        <Section
          title="Interpreted goal"
          description="Intent phase output and/or orchestration interpreted_goal — what the system understood before planning."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          {tr?.intent?.decision_summary ? (
            <p className="max-w-prose whitespace-pre-wrap border-b border-[var(--border)] pb-2.5 text-[13px]">
              {tr.intent.decision_summary}
            </p>
          ) : null}
          {hasStructuredIntent || intentGoal ? (
            <InterpretedGoalPanel
              orchestrationGoal={intentGoal}
              phaseIntent={hasStructuredIntent && intentPo ? intentPo : null}
            />
          ) : (
            <p className="text-sm text-[var(--muted)]">No interpreted goal recorded.</p>
          )}
          {typeof intentPo?.confidence === "string" ? (
            <MetaRow label="intent_confidence">{intentPo.confidence}</MetaRow>
          ) : null}
          {ai?.intent?.model_call_id ? (
            <p className="font-mono text-[10px] text-[var(--muted)]">
              intent model_call_id: {ai.intent.model_call_id}
            </p>
          ) : null}
        </Section>

        <Section
          title="Selected plan & alignment"
          description="Template choice, rule-derived transparency, and deterministic plan–goal alignment (typed fields)."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          <PlanAlignmentCallout
            findings={planAlignmentFindings}
            codes={planAlignmentCodes}
            variant="prominent"
          />
          <PlanningTransparencyPanel transparency={planningTransparency} />
        </Section>

        <Section
          title="Planning output"
          description="Ordered tool chain and planning phase metadata (meta_json.ai_agents.planning)."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          <PlanningOutputCard ai={ai} planRows={planRows} planningModelCall={planningMc} />
        </Section>

        <Section
          title="Execution plan (ordered tools)"
          description="ordered_plan / step_statuses / tool_call_sequence; MCP status and execution hints by order."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          {tr?.planning?.decision_summary ? (
            <p className="mb-2 max-w-prose whitespace-pre-wrap text-[11px] text-[var(--muted)]">
              {tr.planning.decision_summary}
            </p>
          ) : null}
          {tr?.planning?.rationale_summary ? (
            <p className="mb-2 max-w-prose whitespace-pre-wrap text-[11px] text-[var(--muted)]">
              {tr.planning.rationale_summary}
            </p>
          ) : null}
          {planPo && typeof planPo.step_count === "number" ? (
            <p className="mb-2 font-mono text-[10px] text-[var(--muted)]">
              phase_output.step_count: {planPo.step_count}
              {typeof planPo.source === "string" ? ` · source: ${planPo.source}` : ""}
            </p>
          ) : null}
          {planRows.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">No plan rows available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] border-collapse text-left text-[11px]">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                    <th className="py-1 pr-2 font-medium">Order</th>
                    <th className="py-1 pr-2 font-medium">tool_name</th>
                    <th className="py-1 pr-2 font-medium">label</th>
                    <th className="py-1 pr-2 font-medium">MCP status</th>
                    <th className="py-1 font-medium">Result hint</th>
                  </tr>
                </thead>
                <tbody>
                  {planRows.map((row) => {
                    const r = resultByOrder.get(row.order);
                    const hint = r
                      ? [
                          r.panel_row_count != null ? `panel:${r.panel_row_count}` : null,
                          r.feature_row_count != null ? `feat:${r.feature_row_count}` : null,
                          r.anomaly_count != null ? `anom:${r.anomaly_count}` : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")
                      : "";
                    return (
                      <tr key={`${row.order}-${row.tool_name}`} className="border-b border-[var(--border)]">
                        <td className="py-1 pr-2 font-mono">{row.order}</td>
                        <td className="py-1 pr-2 font-mono">{row.tool_name}</td>
                        <td className="max-w-[12rem] py-1 pr-2 text-[var(--muted)]">{row.label ?? "—"}</td>
                        <td className="py-1 pr-2 font-mono">{row.mcp_status ?? r?.mcp_status ?? "—"}</td>
                        <td className="py-1 font-mono text-[10px] text-[var(--muted)]">{hint || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      </div>

      <div id="run-execution" className={`${scrollAnchor} space-y-3`}>
        <Section
          title="Orchestration outcome"
          description="Top-level status and traceability execution summaries from output_payload_json / meta_json."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          {!orch && !lps && !tr?.execution ? (
            <p className="text-sm text-[var(--muted)]">No orchestration snapshot on this run.</p>
          ) : (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                {orch?.status ? (
                  <span className="font-mono text-[11px]">
                    orchestration: <strong>{orch.status}</strong>
                  </span>
                ) : null}
                {lps?.critic?.phase_status ? (
                  <span className="flex items-center gap-1 font-mono text-[10px] text-[var(--muted)]">
                    critic <PhaseStatusChip status={lps.critic.phase_status} />
                  </span>
                ) : null}
                {lps?.report?.phase_status ? (
                  <span className="flex items-center gap-1 font-mono text-[10px] text-[var(--muted)]">
                    report <PhaseStatusChip status={lps.report.phase_status} />
                  </span>
                ) : null}
              </div>
              {orch?.message ? (
                <MetaRow label="message">
                  <span className="whitespace-pre-wrap">{orch.message}</span>
                </MetaRow>
              ) : null}
              {orch?.final_summary ? (
                <MetaRow label="final_summary">
                  <span className="whitespace-pre-wrap text-[11px]">{orch.final_summary}</span>
                </MetaRow>
              ) : null}
              {tr?.execution?.decision_summary ? (
                <MetaRow label="execution (traceability)">
                  <span className="whitespace-pre-wrap text-[11px]">{tr.execution.decision_summary}</span>
                </MetaRow>
              ) : null}
              {tr?.execution?.orchestration_message ? (
                <MetaRow label="orchestration_message">
                  <span className="whitespace-pre-wrap text-[11px]">{tr.execution.orchestration_message}</span>
                </MetaRow>
              ) : null}
            </div>
          )}
        </Section>

        <Section
          title="Tool call summaries"
          description="Per-order MCP outcomes and row counts (tool_results_summary)."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          {!orch?.tool_results_summary?.length ? (
            <p className="text-sm text-[var(--muted)]">No tool_results_summary in orchestration output.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[32rem] border-collapse text-left text-[10px]">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                    <th className="py-1 pr-2 font-medium">Ord</th>
                    <th className="py-1 pr-2 font-medium">Tool</th>
                    <th className="py-1 pr-2 font-medium">MCP</th>
                    <th className="py-1 pr-2 font-medium">Panel</th>
                    <th className="py-1 pr-2 font-medium">Features</th>
                    <th className="py-1 pr-2 font-medium">Anom</th>
                    <th className="py-1 font-medium">Report chars</th>
                  </tr>
                </thead>
                <tbody>
                  {orch.tool_results_summary.map((r) => (
                    <tr key={`${r.order}-${r.tool_name}`} className="border-b border-[var(--border)]">
                      <td className="py-1 pr-2 font-mono">{r.order}</td>
                      <td className="py-1 pr-2 font-mono">{r.tool_name}</td>
                      <td className="py-1 pr-2 font-mono">{r.mcp_status}</td>
                      <td className="py-1 pr-2 font-mono">{r.panel_row_count ?? "—"}</td>
                      <td className="py-1 pr-2 font-mono">{r.feature_row_count ?? "—"}</td>
                      <td className="py-1 pr-2 font-mono">{r.anomaly_count ?? "—"}</td>
                      <td className="py-1 font-mono">{r.report_character_count ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      </div>

      <Section
        id="run-timeline"
        title="Step timeline"
        description="Persisted RunStep rows; LLM steps join ModelCall rows by id. Phase_output summaries when steps include transparency."
        className={`${scrollAnchor} ${panelDense}`}
        bodyClassName={auditBody}
        headerClassName={auditHeader}
      >
        <StepStatusTimeline
          steps={steps}
          modelCallById={mcById}
          projectId={projectId}
          runId={runId}
          toolNamesHint={toolNamesHint}
          hideTraceLink={compactTraceLink}
        />
      </Section>

      <Section
        id="run-model-calls"
        title="Model call summaries"
        description="Persisted LLM invocations (GET /v1/runs/{id}/model-calls). Expand a card for request/response JSON."
        className={`${scrollAnchor} ${panelDense}`}
        bodyClassName={auditBody}
        headerClassName={auditHeader}
      >
        {modelCalls.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No model call rows. Traceable agents may not have run, or calls are not persisted for this run.
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {modelCalls.map((c) => (
              <ModelCallSummaryCard
                key={c.id}
                call={c}
                inspectHref={`/projects/${projectId}/runs/${runId}/trace?collection=model-calls&focus=${c.id}#trace-collection`}
              />
            ))}
          </div>
        )}
      </Section>

      <Section
        id="run-artifacts"
        title="Evidence & artifact links"
        description="Pipeline evidence refs and registered artifacts; traceability maps roles to IDs when ingest completed."
        className={`${scrollAnchor} ${panelDense}`}
        bodyClassName={auditBody}
        headerClassName={auditHeader}
      >
        <p className="mb-2 text-[10px] leading-snug text-[var(--muted)]">
          Chat routes conclusion and finding chips to this roster and to critic/report sections above.
        </p>
        {tr?.evidence_artifact_refs && tr.evidence_artifact_refs.length > 0 ? (
          <div className="mb-2">
            <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">Pipeline evidence refs</p>
            <ul className="font-mono text-[11px]">
              {tr.evidence_artifact_refs.map((ref, i) => (
                <li key={i}>
                  {ref.role ?? "?"} → {ref.basename ?? "—"}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {artifacts.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No artifacts registered for this run.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-[11px]">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-1 pr-2 font-medium">role_key</th>
                  <th className="py-1 pr-2 font-medium">kind</th>
                  <th className="py-1 font-medium">id</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.id} className="border-b border-[var(--border)]">
                    <td className="py-1 pr-2 font-mono">
                      <Link href={`/artifacts/${a.id}`} className="underline">
                        {a.role_key}
                      </Link>
                    </td>
                    <td className="py-1 pr-2 font-mono">{a.kind}</td>
                    <td className="py-1 font-mono text-[10px] text-[var(--muted)]">{a.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <div id="run-agents" className={`${scrollAnchor} space-y-3`}>
        <Section
          title="Critic & report phases"
          description="Structured critic notes and report evidence (phase_output + traceability). Raw JSON only inside each card’s details."
          className={panelDense}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          <div className="grid gap-3 lg:grid-cols-2">
            <CriticFindingsCard
              lps={lps}
              phaseStatus={
                typeof ai?.critic?.phase_status === "string" ? ai.critic.phase_status : undefined
              }
              trace={tr?.critic}
              phaseOutput={criticPo}
              criticModelCall={criticMc}
            />
            <ReportEvidencePanel
              lps={lps?.report}
              phaseStatus={
                typeof ai?.report?.phase_status === "string" ? ai.report.phase_status : undefined
              }
              trace={tr?.report}
              phaseOutput={reportPo}
              artifacts={artifacts}
              reportModelCall={reportMc}
            />
          </div>
        </Section>
      </div>

      {userFacingReport ? (
        <Section
          id="run-conclusions"
          title="Final report (markdown)"
          description="Merged user_facing_report with artifact and critic cross-links."
          className={`${scrollAnchor} ${panelDense}`}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          <FinalReportWithEvidence
            markdown={userFacingReport.markdown}
            keyTakeaways={userFacingReport.key_takeaways}
            modelCallId={userFacingReport.model_call_id}
            reportPhaseOutput={reportPo}
            criticPhaseOutput={criticPo}
            traceability={tr}
            lpsCritic={lps?.critic}
            lpsReport={lps?.report}
            artifacts={artifacts}
          />
        </Section>
      ) : (
        <Section
          id="run-conclusions"
          title="Final report"
          description="user_facing_report is absent when the report phase did not produce merged markdown."
          className={`${scrollAnchor} ${panelDense}`}
          bodyClassName={auditBody}
          headerClassName={auditHeader}
        >
          <p className="text-sm text-[var(--muted)]">
            No user-facing report on this run. Check model phase summaries and the technical inspector for partial
            outputs.
          </p>
        </Section>
      )}

      <Section
        id="run-audit-meta"
        title="Prompts, versions & LLM usage"
        description="Typed transparency from GET /v1/runs/{id}?include_transparency=true — prompt versions, model-call count, evidence id index, per-phase token/latency/cost rollup."
        className={`${scrollAnchor} ${panelDense}`}
        bodyClassName={auditBody}
        headerClassName={auditHeader}
      >
        <ContextTransparencyPanel ai={ai} />
        {runTransparency ? (
          <div className="space-y-2 text-[11px]">
            <MetaRow label="model_call_count">{runTransparency.model_call_count}</MetaRow>
            <MetaRow label="evidence rows (ids)">{runTransparency.evidence_artifact_ids.length}</MetaRow>
            {runTransparency.prompt_versions && Object.keys(runTransparency.prompt_versions).length > 0 ? (
              <div className="overflow-x-auto border-t border-[var(--border)] pt-2">
                <table className="w-full min-w-[16rem] border-collapse text-left font-mono text-[10px]">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-1 pr-2 font-medium">Agent / role key</th>
                      <th className="py-1 font-medium">prompt_version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(runTransparency.prompt_versions).map(([role, ver]) => (
                      <tr key={role} className="border-b border-[var(--border)]">
                        <td className="py-1 pr-2">{role}</td>
                        <td className="py-1">{ver}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-[var(--muted)]">
                No <code className="text-[var(--foreground)]">meta_json.ai_agents.prompt_versions</code> on this run.
              </p>
            )}
            {runTransparency.evidence_artifact_ids.length > 0 ? (
              <p className="font-mono text-[10px] text-[var(--muted)]">
                Evidence artifact ids:{" "}
                {runTransparency.evidence_artifact_ids.slice(0, 6).map((id, i) => (
                  <span key={id}>
                    {i > 0 ? ", " : null}
                    <Link href={`/artifacts/${id}`} className="underline">
                      {id.slice(0, 8)}…
                    </Link>
                  </span>
                ))}
                {runTransparency.evidence_artifact_ids.length > 6 ? " …" : null}
              </p>
            ) : null}
            <div id="run-llm-usage" className="scroll-mt-20 border-t border-[var(--border)] pt-2">
              {runTransparency.llm_usage ? (
                <LlmPhaseUsageCard usage={runTransparency.llm_usage} />
              ) : (
                <div>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                    LLM usage by phase
                  </h3>
                  <p className="mt-1 text-[var(--muted)]">
                    No usage rollup on this response. Reload with{" "}
                    <code className="font-mono text-[var(--foreground)]">include_transparency=true</code> or call{" "}
                    <code className="font-mono text-[var(--foreground)]">GET /v1/runs/…/llm-usage</code>.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            Run was not loaded with transparency. Reload this page after API includes{" "}
            <code className="font-mono text-[var(--foreground)]">include_transparency=true</code> for prompt versions
            and LLM rollups.
          </p>
        )}
      </Section>
    </div>
  );
}
