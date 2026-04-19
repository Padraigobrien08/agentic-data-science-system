import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ProjectWorkspaceNav } from "@/components/layout/project-workspace-nav";
import { ExecuteRunButton } from "@/components/runs/execute-run-button";
import { RunInspectionPanel } from "@/components/runs/run-inspection-panel";
import { RunPipelinePhaseTrack } from "@/components/runs/run-pipeline-phase-track";
import { RunStateBanner } from "@/components/runs/run-state-banner";
import { StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import { parseAiAgents } from "@/lib/ai-agents-meta";
import { getRun, listRunArtifacts, listRunSteps } from "@/lib/api/runs";
import { formatDate } from "@/lib/format";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { buildPrimaryAnswerView } from "@/lib/run-primary-view";

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
      getRun(runId, { includePayloads: true, includeTransparency: false }),
      listRunArtifacts(runId),
      listRunSteps(runId, false),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Run inspection</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs/${runId}`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return (
      <div className="space-y-2">
        <h1 className="text-lg font-semibold">Run inspection</h1>
        <p className="font-mono text-sm text-red-700 dark:text-red-400">{msg}</p>
      </div>
    );
  }

  if (run.project_id !== projectId) {
    notFound();
  }

  const orch = parseOrchestrationOutput(run.output_payload_json);
  const userReport = parseUserFacingReport(run.output_payload_json);
  const ai = parseAiAgents(run.meta_json);
  const view = buildPrimaryAnswerView(run, artifacts, orch, userReport, ai, { projectId, runId });
  const canExecute = EXECUTABLE_HINT.has(run.status);
  const traceHref = `/projects/${projectId}/runs/${runId}/trace`;
  const runAnswerHref = `/projects/${projectId}/runs/${runId}`;

  return (
    <div>
      <ProjectWorkspaceNav projectId={projectId} runId={runId} current="run" />

      <div className="mx-auto max-w-3xl space-y-6 pb-10 pt-1">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
              Inspection surface
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-[var(--foreground)]">Run inspection</h1>
            <p className="max-w-prose text-xs leading-relaxed text-[var(--foreground)]">
              Chat is the primary answer surface. Use this page to verify execution, inspect artifacts, and rerun when
              needed.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={run.status} variant="friendly" />
              <span className="text-xs text-[var(--muted)]">
                {formatDate(run.created_at)}
                {run.finished_at ? ` → ${formatDate(run.finished_at)}` : ""}
              </span>
            </div>
            <details className="text-[11px] text-[var(--muted)]">
              <summary className="cursor-pointer font-mono underline">Run id</summary>
              <p className="mt-1 break-all">{run.id}</p>
            </details>
          </div>
          <div className="flex flex-shrink-0 flex-wrap gap-2">
            <Link
              href={`/projects/${projectId}/chat`}
              className="rounded-lg border border-[var(--border)] bg-[var(--foreground)] px-3 py-2 text-sm font-medium text-[var(--background)]"
            >
              Back to chat
            </Link>
            {canExecute ? (
              <ExecuteRunButton projectId={projectId} runId={runId} />
            ) : null}
            <Link
              href={traceHref}
              className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--foreground)]"
            >
              Open trace
            </Link>
            <Link
              href={`/projects/${projectId}/runs`}
              className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)]"
            >
              All runs
            </Link>
          </div>
        </header>

        <RunStateBanner status={run.status} surface="run-answer" runAnswerHref={runAnswerHref} />

        <RunPipelinePhaseTrack status={run.status} steps={steps} />

        {run.error_summary ? (
          <div
            role="alert"
            className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100"
          >
            <p className="font-medium">Run error</p>
            <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs">{run.error_summary}</pre>
          </div>
        ) : null}

        <RunInspectionPanel
          projectId={projectId}
          runId={runId}
          runStatus={run.status}
          view={view}
          canExecute={canExecute}
        />
      </div>
    </div>
  );
}
