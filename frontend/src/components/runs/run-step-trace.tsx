import Link from "next/link";

import type { RunStepDetail } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

function stepStatusClass(status: RunStepDetail["status"]): string {
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

function stepLane(s: RunStepDetail): { lane: string; trace: string } {
  const m =
    s.meta_json && typeof s.meta_json === "object" && !Array.isArray(s.meta_json)
      ? (s.meta_json as Record<string, unknown>)
      : null;
  if (!m) return { lane: "—", trace: "" };
  const trace = typeof m.trace === "string" ? m.trace : "";
  const phase = typeof m.phase === "string" ? m.phase : "";
  if (trace === "mcp_executor") return { lane: "MCP", trace: "executor" };
  if (trace === "critic_agent") return { lane: "LLM", trace: "critic" };
  if (trace === "report_agent") return { lane: "LLM", trace: "report" };
  if (phase === "llm") return { lane: "LLM", trace: trace || "llm" };
  if (trace) return { lane: "SYS", trace };
  return { lane: "—", trace: "" };
}

type Props = {
  steps: RunStepDetail[];
  projectId?: string;
  runId?: string;
};

function buildInspectHref(projectId: string, runId: string, stepId: string) {
  return `/projects/${projectId}/runs/${runId}/trace?collection=steps&focus=${stepId}#trace-collection`;
}

export function RunStepTrace({ steps, projectId, runId }: Props) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No steps persisted for this run yet. Execute the pipeline or wait for the worker if
        queued.
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {steps.map((s) => {
        const { lane, trace } = stepLane(s);
        const modelCallId =
          s.meta_json &&
          typeof s.meta_json === "object" &&
          !Array.isArray(s.meta_json) &&
          typeof (s.meta_json as Record<string, unknown>).model_call_id === "string"
            ? String((s.meta_json as Record<string, unknown>).model_call_id)
            : null;

        return (
          <li
            key={s.id}
            className="rounded border border-[var(--border)] bg-neutral-50/50 p-3 dark:bg-neutral-950/30"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-semibold text-[var(--muted)]">
                #{s.step_index}
              </span>
              <span
                className={`rounded border border-[var(--border)] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase ${
                  lane === "MCP"
                    ? "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-100"
                    : lane === "LLM"
                      ? "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-100"
                      : "bg-neutral-200 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200"
                }`}
                title={trace || undefined}
              >
                {lane}
              </span>
              <span className={`font-mono text-xs ${stepStatusClass(s.status)}`}>
                {s.status}
              </span>
              {s.planned_tool_name ? (
                <span className="font-mono text-xs">{s.planned_tool_name}</span>
              ) : null}
              {s.label ? (
                <span className="text-xs text-[var(--muted)]">{s.label}</span>
              ) : null}
            </div>
            {trace ? (
              <p className="mt-0.5 font-mono text-[10px] text-[var(--muted)]">trace: {trace}</p>
            ) : null}
            {modelCallId ? (
              <p className="font-mono text-[10px] text-[var(--muted)]">
                model_call_id: {modelCallId}
              </p>
            ) : null}
            {s.detail ? (
              <p className="mt-1 text-xs text-[var(--muted)]">{s.detail}</p>
            ) : null}
            <p className="mt-1 font-mono text-[10px] text-[var(--muted)]">
              {formatDate(s.started_at)} → {formatDate(s.finished_at)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              {projectId && runId ? (
                <Link
                  href={buildInspectHref(projectId, runId, s.id)}
                  className="text-xs font-medium text-[var(--foreground)] underline underline-offset-4"
                >
                  Inspect step details
                </Link>
              ) : (
                <span className="text-xs font-medium text-[var(--foreground)]">Inspect step details</span>
              )}
              {(s.planner_tool_input_json || s.meta_json) ? (
                <p className="text-[10px] text-[var(--muted)]">
                  Open raw payload from the summary-first trace view when you need planner inputs or persisted step metadata.
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
