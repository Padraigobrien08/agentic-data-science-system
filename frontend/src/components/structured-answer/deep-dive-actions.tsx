import Link from "next/link";

import type { DeepDiveActionsProps } from "./types";

export function DeepDiveActions({ traceHref, reportArtifactId, chatHref, className }: DeepDiveActionsProps) {
  return (
    <div className={className ?? "flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center"}>
      <Link
        href={traceHref}
        className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--foreground)] px-4 py-2.5 text-center text-sm font-semibold text-[var(--background)]"
      >
        Deep dive (steps &amp; artifacts)
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
      <div className="hidden h-6 w-px bg-[var(--border)] sm:block" aria-hidden />
      <Link href={chatHref} className="inline-flex items-center justify-center text-sm text-[var(--muted)] underline">
        Chat
      </Link>
    </div>
  );
}
