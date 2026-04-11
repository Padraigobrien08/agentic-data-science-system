import Link from "next/link";

import { StatusBadge } from "@/components/ui/technical";
import { ApiError } from "@/lib/api/errors";
import { listRuns } from "@/lib/api/runs";
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

  return (
    <div className="space-y-4">
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
          Submit run
        </Link>
      </div>

      {sorted.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No runs for this project.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-[var(--border)]">
          <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-neutral-50 text-xs dark:bg-neutral-900/50">
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Run ID</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Status</th>
                <th className="px-3 py-2 font-semibold text-[var(--muted)]">Goal</th>
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
