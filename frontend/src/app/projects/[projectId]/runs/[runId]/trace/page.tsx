import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ProjectWorkspaceNav } from "@/components/layout/project-workspace-nav";
import { AgenticTraceView } from "@/components/trace/agentic-trace-view";
import { StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import { getRun, listRunArtifacts, listRunModelCalls, listRunSteps } from "@/lib/api/runs";
import { formatDate } from "@/lib/format";
import { parseUserFacingReport } from "@/lib/orchestration-output";

export const dynamic = "force-dynamic";

export default async function RunTracePage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
}>) {
  const { projectId, runId } = await params;
  let run;
  let steps;
  let artifacts;
  let modelCalls;
  try {
    [run, steps, artifacts, modelCalls] = await Promise.all([
      getRun(runId, { includePayloads: true, includeTransparency: true }),
      listRunSteps(runId, { includePayloads: true, includeTransparency: true }),
      listRunArtifacts(runId),
      listRunModelCalls(runId, false),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Deep dive</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs/${runId}/trace`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="font-mono text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  if (run.project_id !== projectId) {
    notFound();
  }

  const userReport = parseUserFacingReport(run.output_payload_json);

  return (
    <div className="space-y-6">
      <ProjectWorkspaceNav projectId={projectId} runId={runId} current="trace" />

      <header className="border-b border-[var(--border)] pb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
              Inspection / audit workspace
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-[var(--foreground)]">Deep dive</h1>
            <p className="max-w-prose text-xs leading-relaxed text-[var(--muted)]">
              Full transparency for this run: interpreted goal, plan, MCP execution, persisted steps, LLM calls,
              critic and report phases, artifacts, and prompt metadata. Denser than the run answer page by design.
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
              <StatusBadge status={run.status} />
              <span className="hidden sm:inline">·</span>
              <span>
                {formatDate(run.created_at)}
                {run.finished_at ? ` → ${formatDate(run.finished_at)}` : ""}
              </span>
            </div>
            <details className="text-[10px] text-[var(--muted)]">
              <summary className="cursor-pointer font-mono underline">Run id</summary>
              <p className="mt-1 break-all">{runId}</p>
            </details>
          </div>
          <div className="flex flex-shrink-0 flex-wrap gap-2">
            <Link
              href={`/projects/${projectId}/runs/${runId}`}
              className="rounded-lg border border-[var(--border)] bg-[var(--foreground)] px-3 py-2 text-center text-sm font-medium text-[var(--background)]"
            >
              Run answer
            </Link>
            <Link
              href={`/projects/${projectId}/chat`}
              className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--foreground)]"
            >
              Chat
            </Link>
            <Link
              href={`/projects/${projectId}/runs`}
              className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)]"
            >
              All runs
            </Link>
          </div>
        </div>
      </header>

      <AgenticTraceView
        projectId={projectId}
        runId={runId}
        outputPayload={run.output_payload_json}
        metaJson={run.meta_json}
        steps={steps}
        artifacts={artifacts}
        modelCalls={modelCalls}
        userFacingReport={userReport}
        compactTraceLink
        runStatus={run.status}
        runErrorSummary={run.error_summary}
        runTransparency={run.transparency ?? null}
      />
    </div>
  );
}
