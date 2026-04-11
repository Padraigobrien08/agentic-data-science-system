import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ExecuteRunButton } from "@/components/runs/execute-run-button";
import { MarkdownReport } from "@/components/runs/markdown-report";
import { AgenticTraceView } from "@/components/trace/agentic-trace-view";
import { JsonPanel, MetaRow, Section, StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import { getRun, listRunArtifacts, listRunSteps } from "@/lib/api/runs";
import { formatDate } from "@/lib/format";
import {
  parseOrchestrationOutput,
  parseUserFacingReport,
} from "@/lib/orchestration-output";

export const dynamic = "force-dynamic";

const EXECUTABLE_HINT = new Set([
  "pending",
  "error",
  "partial_success",
  "no_data",
  "cancelled",
]);

export default async function RunDetailPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
}>) {
  const { projectId, runId } = await params;
  let run;
  let artifacts;
  let steps;
  try {
    [run, artifacts, steps] = await Promise.all([
      getRun(runId, true),
      listRunArtifacts(runId),
      listRunSteps(runId, true),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Run detail</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs/${runId}`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return (
      <div className="space-y-2">
        <h1 className="text-lg font-semibold">Run detail</h1>
        <p className="font-mono text-sm text-red-700 dark:text-red-400">{msg}</p>
      </div>
    );
  }

  if (run.project_id !== projectId) {
    notFound();
  }

  const orch = parseOrchestrationOutput(run.output_payload_json);
  const userReport = parseUserFacingReport(run.output_payload_json);
  const canExecute = EXECUTABLE_HINT.has(run.status);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-lg font-semibold">Run detail</h1>
          <StatusBadge status={run.status} />
          <div className="mt-3 max-w-3xl border-t border-[var(--border)]">
            <MetaRow label="run.id">{run.id}</MetaRow>
            <MetaRow label="project_id">{run.project_id}</MetaRow>
            <MetaRow label="correlation_id">
              {run.correlation_id ?? "—"}
            </MetaRow>
            {orch?.run_id ? (
              <MetaRow label="orchestration_run_id">{orch.run_id}</MetaRow>
            ) : null}
            <MetaRow label="created_at">{formatDate(run.created_at)}</MetaRow>
            <MetaRow label="finished_at">{formatDate(run.finished_at)}</MetaRow>
            <MetaRow label="started_at">{formatDate(run.started_at)}</MetaRow>
          </div>
        </div>
        <div className="flex flex-shrink-0 flex-wrap gap-2">
          {canExecute ? (
            <ExecuteRunButton projectId={projectId} runId={runId} />
          ) : null}
          <Link
            href={`/projects/${projectId}/runs/${runId}/trace`}
            className="rounded border border-[var(--border)] px-3 py-2 font-mono text-sm"
          >
            Full trace view
          </Link>
          <Link
            href={`/projects/${projectId}/runs`}
            className="rounded border border-[var(--border)] px-3 py-2 font-mono text-sm"
          >
            All runs
          </Link>
        </div>
      </div>

      {run.status === "queued" ? (
        <p className="rounded border border-amber-200 bg-amber-50 p-2 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          Status <code className="font-mono">queued</code>: execution is handled by the backend
          worker. Refresh this page after the job completes.
        </p>
      ) : null}

      {run.error_summary ? (
        <Section title="Error summary" description="Persisted error_summary on the analysis run row.">
          <pre className="whitespace-pre-wrap font-mono text-sm text-red-800 dark:text-red-200">
            {run.error_summary}
          </pre>
        </Section>
      ) : null}

      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Agentic trace &amp; artifacts
        </h2>
        <p className="mb-3 max-w-prose text-xs text-[var(--muted)]">
          Planner output (goal + LLM plan), MCP tool sequence, LLM phases in{" "}
          <code>meta_json</code>, persisted <code>RunStep</code> rows, and registered artifacts —
          aligned for auditability.
        </p>
        <AgenticTraceView
          projectId={projectId}
          runId={runId}
          outputPayload={run.output_payload_json}
          metaJson={run.meta_json}
          steps={steps}
          artifacts={artifacts}
        />
      </div>

      {userReport ? (
        <Section
          title="Final report"
          description="Merged user_facing_report from the traceable pipeline (report agent output)."
        >
          {userReport.model_call_id ? (
            <p className="mb-3 font-mono text-[10px] text-[var(--muted)]">
              model_call_id: {userReport.model_call_id}
            </p>
          ) : null}
          {userReport.key_takeaways.length > 0 ? (
            <div className="mb-4">
              <p className="mb-1 text-xs font-semibold uppercase text-[var(--muted)]">
                Key takeaways
              </p>
              <ul className="list-inside list-disc font-mono text-sm">
                {userReport.key_takeaways.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <MarkdownReport source={userReport.markdown} />
        </Section>
      ) : null}

      <Section
        title="Raw payloads"
        description="Full JSON as returned by GET /v1/runs/{id}?include_payloads=true"
      >
        <div className="space-y-4">
          <JsonPanel title="input_payload_json" value={run.input_payload_json} />
          <JsonPanel title="output_payload_json" value={run.output_payload_json} />
          <JsonPanel title="meta_json" value={run.meta_json} />
        </div>
      </Section>
    </div>
  );
}
