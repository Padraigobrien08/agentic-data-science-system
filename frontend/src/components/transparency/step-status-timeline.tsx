import Link from "next/link";

import type { ModelCallApiItem, RunStepDetail } from "@/lib/api/types";
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
          const meta =
            s.meta_json && typeof s.meta_json === "object" && !Array.isArray(s.meta_json)
              ? (s.meta_json as Record<string, unknown>)
              : null;
          const modelCallId = typeof meta?.model_call_id === "string" ? meta.model_call_id : null;
          const mc = modelCallId ? modelCallById.get(modelCallId) : undefined;
          const tokens = mc ? formatTokenTotal(mc) : null;

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
                {trace ? (
                  <span className="font-mono text-[10px] text-[var(--muted)]">{trace}</span>
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
