import Link from "next/link";
import { redirect } from "next/navigation";

import { AutoRefresh } from "@/components/investigations/auto-refresh";
import { findInvestigationForRun } from "@/lib/api/investigations";
import { getRun } from "@/lib/api/runs";

export const dynamic = "force-dynamic";

const TERMINAL = new Set(["success", "partial_success", "no_data", "error", "cancelled"]);

export default async function InvestigationPendingPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
}>) {
  const { projectId, runId } = await params;

  // Once the worker has persisted the investigation, jump straight to it.
  const inv = await findInvestigationForRun(runId).catch(() => null);
  if (inv) {
    redirect(`/projects/${projectId}/investigations/${inv.id}`);
  }

  let status = "queued";
  let errorSummary: string | null = null;
  try {
    const run = await getRun(runId, false);
    status = run.status;
    errorSummary = run.error_summary ?? null;
  } catch {
    // treat an unreadable run as still pending
  }

  const terminalWithoutInvestigation = TERMINAL.has(status) && !inv;

  return (
    <div className="mx-auto max-w-2xl space-y-5 p-4">
      <Link
        href={`/projects/${projectId}/investigations`}
        className="text-sm text-neutral-500 underline dark:text-neutral-400"
      >
        ← All investigations
      </Link>

      {terminalWithoutInvestigation ? (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          <p className="font-medium">The investigation did not complete.</p>
          <p className="mt-1">{errorSummary || `Run ended with status “${status}”.`}</p>
          <Link
            href={`/projects/${projectId}/investigations/new`}
            className="mt-3 inline-block underline"
          >
            Try again
          </Link>
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 p-6 dark:border-neutral-800">
          <div className="flex items-center gap-3">
            <span
              className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-700 dark:border-neutral-700 dark:border-t-neutral-200"
              aria-hidden
            />
            <h1 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              Investigation running…
            </h1>
          </div>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            The agent is generating hypotheses, running experiments, and weighing evidence in the
            background. This page updates itself and will open the results when it finishes.
          </p>
          <p className="mt-3 font-mono text-xs text-neutral-400">status: {status}</p>
          <AutoRefresh />
        </div>
      )}
    </div>
  );
}
