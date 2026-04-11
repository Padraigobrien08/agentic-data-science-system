import Link from "next/link";
import type { ReactNode } from "react";

import { FinalReportWithEvidence } from "@/components/runs/final-report-with-evidence";
import { CriticFindingsCard } from "@/components/transparency/critic-findings-card";
import { ModelCallSummaryCard } from "@/components/transparency/model-call-summary-card";
import { PhaseStatusChip } from "@/components/transparency/phase-status-chip";
import { PlanningOutputCard } from "@/components/transparency/planning-output-card";
import { ReportEvidencePanel } from "@/components/transparency/report-evidence-panel";
import { StepStatusTimeline } from "@/components/transparency/step-status-timeline";
import { JsonPanel, MetaRow, Section } from "@/components/ui/technical";
import { indexModelCallsById } from "@/lib/agent-transparency";
import type { ArtifactMetadata, ModelCallApiItem, RunStepDetail } from "@/lib/api/types";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type {
  ParsedOrchestrationOutput,
  UserFacingReport,
} from "@/lib/orchestration-output";
import {
  deriveExecutionPlan,
  toolResultByOrder,
} from "@/lib/run-trace-derive";

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
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function phaseOutput(meta: unknown): Record<string, unknown> | null {
  if (!isRecord(meta)) return null;
  const po = meta.phase_output;
  return isRecord(po) ? po : null;
}

function InterpretedGoalBody({ goal }: { goal: unknown }): ReactNode {
  if (!goal || typeof goal !== "object" || Array.isArray(goal)) {
    return <JsonPanel value={goal} />;
  }
  const g = goal as Record<string, unknown>;
  const code = typeof g.code === "string" ? g.code : null;
  const desc = typeof g.description === "string" ? g.description : null;
  const userGoal = typeof g.user_goal_text === "string" ? g.user_goal_text : null;
  const intent = typeof g.intent === "string" ? g.intent : null;
  if (!code && !desc && !userGoal && !intent) return <JsonPanel value={goal} />;
  return (
    <div className="space-y-0 border-t border-[var(--border)]">
      {code ? <MetaRow label="goal_code">{code}</MetaRow> : null}
      {intent ? <MetaRow label="orchestration_intent">{intent}</MetaRow> : null}
      {desc ? (
        <MetaRow label="description">
          <span className="whitespace-pre-wrap">{desc}</span>
        </MetaRow>
      ) : null}
      {userGoal ? (
        <MetaRow label="user_goal_text">
          <span className="whitespace-pre-wrap">{userGoal}</span>
        </MetaRow>
      ) : null}
    </div>
  );
}

/**
 * Readable first-pass trace: goal → plan → timeline → LLM phases → tools → evidence → report.
 * Deep tables and raw JSON remain in sibling inspector panels.
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
}: Props) {
  const tr = ai?.traceability;
  const lps = orch?.llm_phases_summary;
  const planRows = deriveExecutionPlan(orch, ai);
  const resultByOrder = toolResultByOrder(orch?.tool_results_summary);
  const intentPo = phaseOutput(ai?.intent);
  const planPo = phaseOutput(ai?.planning);
  const criticPo = phaseOutput(ai?.critic);
  const reportPo = phaseOutput(ai?.report);
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

  return (
    <div className="space-y-4">
      <Section
        title="Pipeline outcome"
        description="Orchestration status and post-MCP LLM phase outcomes (from output_payload_json and meta_json)."
      >
        {!orch && !lps && !tr?.execution ? (
          <p className="text-sm text-[var(--muted)]">No orchestration snapshot on this run.</p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {orch?.status ? (
                <span className="font-mono text-xs">
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
                <span className="whitespace-pre-wrap text-xs">{orch.final_summary}</span>
              </MetaRow>
            ) : null}
            {tr?.execution?.decision_summary ? (
              <MetaRow label="execution (traceability)">
                <span className="whitespace-pre-wrap text-xs">
                  {tr.execution.decision_summary}
                </span>
              </MetaRow>
            ) : null}
            {tr?.execution?.orchestration_message ? (
              <MetaRow label="orchestration_message">
                <span className="whitespace-pre-wrap text-xs">
                  {tr.execution.orchestration_message}
                </span>
              </MetaRow>
            ) : null}
          </div>
        )}
      </Section>

      <Section
        title="Model calls"
        description="Persisted LLM invocations for this run (GET /v1/runs/{id}/model-calls). Expand a card for request/response JSON."
      >
        {modelCalls.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No model call rows. Traceable agents may not have run, or calls are not persisted for this
            run.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {modelCalls.map((c) => (
              <ModelCallSummaryCard key={c.id} call={c} />
            ))}
          </div>
        )}
      </Section>

      <Section
        title="Interpreted goal"
        description="What the pipeline understood as the analysis intent (structured phase_output when available, else orchestration interpreted_goal)."
      >
        {tr?.intent?.decision_summary ? (
          <p className="mb-3 max-w-prose whitespace-pre-wrap border-b border-[var(--border)] pb-3 text-sm">
            {tr.intent.decision_summary}
          </p>
        ) : null}
        {hasStructuredIntent ? (
          <div className="space-y-0 border-t border-[var(--border)]">
            {typeof intentPo.source === "string" ? (
              <MetaRow label="source">{intentPo.source}</MetaRow>
            ) : null}
            {typeof intentPo.goal_code === "string" ? (
              <MetaRow label="goal_code">{intentPo.goal_code}</MetaRow>
            ) : null}
            {typeof intentPo.orchestration_intent === "string" ? (
              <MetaRow label="orchestration_intent">{intentPo.orchestration_intent}</MetaRow>
            ) : null}
            {typeof intentPo.description_excerpt === "string" ? (
              <MetaRow label="description_excerpt">
                <span className="whitespace-pre-wrap">{intentPo.description_excerpt}</span>
              </MetaRow>
            ) : null}
            {typeof intentPo.user_goal_excerpt === "string" ? (
              <MetaRow label="user_goal_excerpt">
                <span className="whitespace-pre-wrap">{intentPo.user_goal_excerpt}</span>
              </MetaRow>
            ) : null}
            {typeof intentPo.confidence === "string" ? (
              <MetaRow label="confidence">{intentPo.confidence}</MetaRow>
            ) : null}
          </div>
        ) : intentGoal ? (
          <InterpretedGoalBody goal={intentGoal} />
        ) : (
          <p className="text-sm text-[var(--muted)]">No interpreted goal recorded.</p>
        )}
        {ai?.intent?.model_call_id ? (
          <p className="mt-2 font-mono text-[10px] text-[var(--muted)]">
            intent model_call_id: {ai.intent.model_call_id}
          </p>
        ) : null}
      </Section>

      <Section
        title="Planning output"
        description="Ordered tool chain and planning phase metadata (meta_json.ai_agents.planning)."
      >
        <PlanningOutputCard ai={ai} planRows={planRows} planningModelCall={planningMc} />
      </Section>

      <Section
        title="Execution plan"
        description="Ordered tools: planning.phase_output.ordered_plan when present, else step_statuses, LLM planning steps, or executed tool_call_sequence. MCP column from execution summaries when matched by order."
      >
        {tr?.planning?.decision_summary ? (
          <p className="mb-3 max-w-prose whitespace-pre-wrap text-xs text-[var(--muted)]">
            {tr.planning.decision_summary}
          </p>
        ) : null}
        {tr?.planning?.rationale_summary ? (
          <p className="mb-3 max-w-prose whitespace-pre-wrap text-xs text-[var(--muted)]">
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
            <table className="w-full min-w-[28rem] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-1.5 pr-2 font-medium">Order</th>
                  <th className="py-1.5 pr-2 font-medium">tool_name</th>
                  <th className="py-1.5 pr-2 font-medium">label</th>
                  <th className="py-1.5 pr-2 font-medium">MCP status</th>
                  <th className="py-1.5 font-medium">Result hint</th>
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
                      <td className="py-1.5 pr-2 font-mono">{row.order}</td>
                      <td className="py-1.5 pr-2 font-mono">{row.tool_name}</td>
                      <td className="max-w-[12rem] py-1.5 pr-2 text-[var(--muted)]">
                        {row.label ?? "—"}
                      </td>
                      <td className="py-1.5 pr-2 font-mono">
                        {row.mcp_status ?? r?.mcp_status ?? "—"}
                      </td>
                      <td className="py-1.5 font-mono text-[10px] text-[var(--muted)]">
                        {hint || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        title="Step timeline"
        description="Persisted RunStep rows; LLM steps show joined model metadata when model_call_id matches."
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
        title="Critic & report"
        description="Structured findings and report evidence (phase_output + traceability). Raw JSON only inside each card’s details."
      >
        <div className="grid gap-4 lg:grid-cols-2">
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

      <Section
        title="Tool call summaries"
        description="Per-order MCP outcomes and row counts (tool_results_summary)."
      >
        {!orch?.tool_results_summary?.length ? (
          <p className="text-sm text-[var(--muted)]">No tool_results_summary in orchestration output.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] border-collapse text-left text-[10px]">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-1.5 pr-2 font-medium">Ord</th>
                  <th className="py-1.5 pr-2 font-medium">Tool</th>
                  <th className="py-1.5 pr-2 font-medium">MCP</th>
                  <th className="py-1.5 pr-2 font-medium">Panel</th>
                  <th className="py-1.5 pr-2 font-medium">Features</th>
                  <th className="py-1.5 pr-2 font-medium">Anom</th>
                  <th className="py-1.5 font-medium">Report chars</th>
                </tr>
              </thead>
              <tbody>
                {orch.tool_results_summary.map((r) => (
                  <tr key={`${r.order}-${r.tool_name}`} className="border-b border-[var(--border)]">
                    <td className="py-1.5 pr-2 font-mono">{r.order}</td>
                    <td className="py-1.5 pr-2 font-mono">{r.tool_name}</td>
                    <td className="py-1.5 pr-2 font-mono">{r.mcp_status}</td>
                    <td className="py-1.5 pr-2 font-mono">{r.panel_row_count ?? "—"}</td>
                    <td className="py-1.5 pr-2 font-mono">{r.feature_row_count ?? "—"}</td>
                    <td className="py-1.5 pr-2 font-mono">{r.anomaly_count ?? "—"}</td>
                    <td className="py-1.5 font-mono">{r.report_character_count ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        title="Evidence & artifact links"
        description="Registered artifacts for this run; traceability maps roles to IDs when ingest completed."
      >
        {tr?.evidence_artifact_refs && tr.evidence_artifact_refs.length > 0 ? (
          <div className="mb-3">
            <p className="mb-1 text-[10px] font-semibold uppercase text-[var(--muted)]">
              Pipeline evidence refs (paths)
            </p>
            <ul className="font-mono text-xs">
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
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-1.5 pr-2 font-medium">role_key</th>
                  <th className="py-1.5 pr-2 font-medium">kind</th>
                  <th className="py-1.5 font-medium">id</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.id} className="border-b border-[var(--border)]">
                    <td className="py-1.5 pr-2 font-mono">
                      <Link href={`/artifacts/${a.id}`} className="underline">
                        {a.role_key}
                      </Link>
                    </td>
                    <td className="py-1.5 pr-2 font-mono">{a.kind}</td>
                    <td className="py-1.5 font-mono text-[10px] text-[var(--muted)]">{a.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {userFacingReport ? (
        <Section
          title="Final report"
          description="Conclusions tied to registered artifacts and critic context from meta_json / llm_phases_summary."
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
          title="Final report"
          description="user_facing_report is absent when the report phase did not produce merged markdown."
        >
          <p className="text-sm text-[var(--muted)]">
            No user-facing report on this run. Check model phase summaries and inspector panels for
            partial outputs.
          </p>
        </Section>
      )}
    </div>
  );
}
