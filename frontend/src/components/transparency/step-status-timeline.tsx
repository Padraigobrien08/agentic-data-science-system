import Link from "next/link";

import type { ModelCallApiItem, RunStepDetail, RunStepOutputSummary } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { stepLaneFromMeta } from "@/lib/run-trace-derive";
import { formatTokenTotal } from "@/lib/agent-transparency";

function statusClass(status: RunStepDetail["status"]): string {
  switch (status) {
    case "success":
      return "text-emerald-700 dark:text-emerald-400";
    case "error":
      return "text-red-700 dark:text-red-400";
    case "skipped":
      return "text-[var(--muted)]";
    case "running":
      return "text-amber-700 dark:text-amber-400";
    default:
      return "text-[var(--foreground)]";
  }
}

type Props = {
  steps: RunStepDetail[];
  modelCallById: Map<string, ModelCallApiItem>;
  projectId: string;
  runId: string;
  /** MCP tool names from orchestration (shown once as context). */
  toolNamesHint?: string[];
  hideTraceLink?: boolean;
};

function stepOutputSummaryLines(os: RunStepOutputSummary): string[] {
  const lines: string[] = [];
  if (os.phase_status) lines.push(`phase_status: ${os.phase_status}`);
  if (os.skipped === true) lines.push("skipped");
  if (os.skip_reason) lines.push(`skip_reason: ${os.skip_reason}`);
  if (os.issue_count != null) lines.push(`issue_count: ${os.issue_count}`);
  if (os.overall_confidence) lines.push(`overall_confidence: ${os.overall_confidence}`);
  if (os.markdown_char_count != null) lines.push(`markdown_char_count: ${os.markdown_char_count}`);
  if (os.key_takeaway_count != null) lines.push(`key_takeaways: ${os.key_takeaway_count}`);
  if (os.step_count != null) lines.push(`step_count: ${os.step_count}`);
  if (os.artifact_roles.length) lines.push(`artifact_roles: ${os.artifact_roles.join(", ")}`);
  if (os.weak_evidence_signals.length) {
    lines.push(`weak_evidence_signals: ${os.weak_evidence_signals.join(", ")}`);
  }
  return lines;
}

/**
 * Persisted steps with optional join to ModelCall rows (latency, model, tokens) for LLM steps.
 */
export function StepStatusTimeline({
  steps,
  modelCallById,
  projectId,
  runId,
  toolNamesHint,
  hideTraceLink,
}: Props) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No persisted steps for this run yet.
      </p>
    );
  }

  const ordered = steps.slice().sort((a, b) => a.step_index - b.step_index);

  return (
    <div className="space-y-2">
      {toolNamesHint && toolNamesHint.length > 0 ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          Orchestration tools: {toolNamesHint.join(" → ")}
        </p>
      ) : null}
      <ol className="space-y-2">
        {ordered.map((s) => {
          const { lane, trace } = stepLaneFromMeta(s.meta_json);
          const tr = s.transparency;
          const traceShow = tr?.trace ?? trace;
          const phaseShow = tr?.phase;
          const meta =
            s.meta_json && typeof s.meta_json === "object" && !Array.isArray(s.meta_json)
              ? (s.meta_json as Record<string, unknown>)
              : null;
          const modelCallId =
            tr?.model_call_id ??
            (typeof meta?.model_call_id === "string" ? meta.model_call_id : null);
          const mc = modelCallId ? modelCallById.get(modelCallId) : undefined;
          const tokens = mc ? formatTokenTotal(mc) : null;
          const outLines = tr?.output_summary ? stepOutputSummaryLines(tr.output_summary) : [];

          return (
            <li
              key={s.id}
              className="border-l-2 border-[var(--border)] py-2 pl-3"
            >
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span className="font-mono text-[10px] text-[var(--muted)]">#{s.step_index}</span>
                <span className="font-mono text-[10px] font-semibold uppercase text-[var(--muted)]">
                  {lane}
                </span>
                {traceShow ? (
                  <span className="font-mono text-[10px] text-[var(--muted)]">{traceShow}</span>
                ) : null}
                {phaseShow ? (
                  <span className="font-mono text-[10px] text-[var(--muted)]">phase:{phaseShow}</span>
                ) : null}
                <span className={`font-mono text-xs ${statusClass(s.status)}`}>{s.status}</span>
              </div>
              <div className="mt-0.5 font-mono text-xs">
                {s.planned_tool_name ? (
                  <span>{s.planned_tool_name}</span>
                ) : (
                  <span className="text-[var(--muted)]">—</span>
                )}
                {s.label ? <span className="ml-2 text-[var(--muted)]">{s.label}</span> : null}
              </div>
              {s.detail ? (
                <p className="mt-1 max-w-prose text-xs text-[var(--muted)]">{s.detail}</p>
              ) : null}
              <p className="mt-0.5 font-mono text-[10px] text-[var(--muted)]">
                {formatDate(s.started_at)} → {formatDate(s.finished_at)}
              </p>
              {modelCallId ? (
                <p className="font-mono text-[10px] text-[var(--muted)]">
                  model_call_id: {modelCallId}
                </p>
              ) : null}
              {mc ? (
                <div className="mt-1 rounded border border-[var(--border)] bg-neutral-50/80 px-2 py-1.5 font-mono text-[10px] dark:bg-neutral-950/50">
                  <span className="text-[var(--foreground)]">{mc.model_name}</span>
                  <span className="text-[var(--muted)]"> · {mc.provider}</span>
                  {mc.latency_ms != null ? (
                    <span className="text-[var(--muted)]"> · {mc.latency_ms}ms</span>
                  ) : null}
                  {tokens ? <span className="text-[var(--muted)]"> · {tokens}</span> : null}
                  {mc.prompt_version ? (
                    <span className="text-[var(--muted)]"> · prompt {mc.prompt_version}</span>
                  ) : null}
                </div>
              ) : null}
              {outLines.length > 0 ? (
                <ul className="mt-1.5 list-inside list-disc font-mono text-[10px] text-[var(--muted)]">
                  {outLines.map((line, i) => (
                    <li key={`${s.id}-out-${i}`}>{line}</li>
                  ))}
                </ul>
              ) : null}
              {tr && tr.linked_artifact_ids.length > 0 ? (
                <p className="mt-1 font-mono text-[10px] text-[var(--muted)]">
                  Linked artifacts:{" "}
                  {tr.linked_artifact_ids.map((aid, idx) => (
                    <span key={aid}>
                      {idx > 0 ? ", " : null}
                      <Link href={`/artifacts/${aid}`} className="underline">
                        {aid.slice(0, 8)}…
                      </Link>
                    </span>
                  ))}
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>
      {!hideTraceLink ? (
        <p className="text-[10px] text-[var(--muted)]">
          Full step payloads:{" "}
          <Link href={`/projects/${projectId}/runs/${runId}/trace`} className="underline">
            trace view
          </Link>
          .
        </p>
      ) : null}
    </div>
  );
}
