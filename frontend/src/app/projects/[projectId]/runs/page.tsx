import Link from "next/link";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { RunsListAutoRefresh } from "@/components/runs/runs-list-auto-refresh";
import { StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import { listRuns } from "@/lib/api/runs";
import { shouldPollRunStatus } from "@/lib/run-status-copy";
import type { AnalysisRunSummary } from "@/lib/api/types";
import { formatDate, shortId } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function RunsListPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;
  let runs: AnalysisRunSummary[];
  try {
    runs = await listRuns(projectId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Analysis runs</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return (
      <div className="space-y-2">
        <h1 className="text-lg font-semibold">Analysis runs</h1>
        <p className="font-mono text-sm text-red-700 dark:text-red-400">
          GET /v1/runs failed: {msg}
        </p>
      </div>
    );
  }

  const sorted = [...runs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  const hasActiveRuns = sorted.some((r) => shouldPollRunStatus(r.status));

  return (
    <div className="space-y-4">
      <RunsListAutoRefresh active={hasActiveRuns} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Analysis runs</h1>
          <p className="mt-1 font-mono text-xs text-[var(--muted)]">
            project_id={projectId}
          </p>
        </div>
        <Link
          href={`/projects/${projectId}/runs/new`}
          className="rounded border border-[var(--border)] px-3 py-1.5 font-mono text-sm"
        >
          Advanced run
        </Link>
      </div>

      {hasActiveRuns ? (
        <p className="text-xs text-[var(--muted)]" role="status">
          At least one run is queued or running — this list refreshes every few seconds until all settle.
        </p>
      ) : null}

      {sorted.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] bg-neutral-50/50 px-5 py-8 text-center dark:bg-neutral-950/30">
          <p className="text-sm font-medium text-[var(--foreground)]">No analysis runs yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)]">
            Runs created from workspace chat appear here with status, goal, and links into the answer and trace.
          </p>
          <Link
            href={`/projects/${projectId}/runs/new`}
            className="mt-5 inline-flex rounded-lg bg-[var(--foreground)] px-4 py-2 text-sm font-semibold text-[var(--background)]"
          >
            Advanced run
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto rounded border border-[var(--border)]">
          <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-neutral-50 text-xs dark:bg-neutral-900/50">
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Run ID</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Status</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Goal</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Deep dive</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Correlation</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Created</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-3 py-2 align-top font-mono text-xs">
                    <Link
                      href={`/projects/${projectId}/runs/${r.id}`}
                      className="underline decoration-dotted"
                      title={r.id}
                    >
                      {shortId(r.id)}…
                    </Link>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="max-w-xs px-3 py-2 align-top text-xs text-[var(--foreground)]">
                    {r.orchestration_goal_text ? (
                      <span className="line-clamp-2">{r.orchestration_goal_text}</span>
                    ) : (
                      <span className="text-[var(--muted)]">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 align-top text-xs">
                    <Link
                      href={`/projects/${projectId}/runs/${r.id}/trace`}
                      className="font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2"
                    >
                      Trace
                    </Link>
                  </td>
                  <td className="px-3 py-2 align-top font-mono text-[10px] text-[var(--muted)]">
                    {r.correlation_id ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 align-top font-mono text-[10px] text-[var(--muted)]">
                    {formatDate(r.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
