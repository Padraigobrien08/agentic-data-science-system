import Link from "next/link";

import type { DeepDiveActionsProps } from "./types";

export function DeepDiveActions({ traceHref, reportArtifactId, chatHref, runsHref, className }: DeepDiveActionsProps) {
  return (
    <div className={className ?? "flex flex-col gap-2 sm:flex-row sm:flex-wrap"}>
      <Link
        href={traceHref}
        className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--foreground)] px-4 py-2.5 text-center text-sm font-semibold text-[var(--background)]"
      >
        View deep dive
      </Link>
      {reportArtifactId ? (
        <Link
          href={`/artifacts/${reportArtifactId}`}
          className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-2.5 text-center text-sm font-medium text-[var(--foreground)]"
        >
          Open report artifact
        </Link>
      ) : (
        <span className="inline-flex items-center justify-center rounded-lg border border-dashed border-[var(--border)] px-4 py-2.5 text-center text-sm text-[var(--muted)]">
          Report artifact not linked yet
        </span>
      )}
      <Link
        href={traceHref}
        className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-2.5 text-center text-sm font-medium text-[var(--foreground)]"
      >
        Inspect artifacts &amp; trace
      </Link>
      <Link href={chatHref} className="inline-flex items-center justify-center text-sm text-[var(--muted)] underline">
        Chat workspace
      </Link>
      <Link href={runsHref} className="inline-flex items-center justify-center text-sm text-[var(--muted)] underline">
        All runs
      </Link>
    </div>
  );
}
