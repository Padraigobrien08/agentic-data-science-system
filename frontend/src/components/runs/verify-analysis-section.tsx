import Link from "next/link";

import { ExecuteRunButton } from "@/components/runs/execute-run-button";
import type { EvidenceLink } from "@/lib/run-primary-view";

type Props = {
  traceHref: string;
  evidenceLinks: EvidenceLink[];
  reportArtifactId: string | null;
  projectId: string;
  runId: string;
  /** When true, show a compact re-execute control (same rules as the header button). */
  canExecute: boolean;
};

/**
 * Compact trust strip: where to double-check before acting on the summary.
 */
export function VerifyAnalysisSection({
  traceHref,
  evidenceLinks,
  reportArtifactId,
  projectId,
  runId,
  canExecute,
}: Props) {
  const artifactsTableHref = `${traceHref}#run-artifacts`;
  const topEvidence = evidenceLinks.slice(0, 3);

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Verify this analysis</p>
      <p className="mt-1 text-xs leading-snug text-[var(--muted)]">
        Conclusions are model-assisted — cross-check steps, sources, and stored artifacts before high-stakes use.
      </p>
      <div className="mt-2.5 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4 sm:gap-y-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
          <Link href={traceHref} className="font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2">
            Deep dive (steps &amp; calls)
          </Link>
          <span className="hidden text-[var(--muted)] sm:inline" aria-hidden>
            ·
          </span>
          <Link
            href={artifactsTableHref}
            className="font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2"
          >
            All artifacts
          </Link>
          {reportArtifactId ? (
            <>
              <span className="hidden text-[var(--muted)] sm:inline" aria-hidden>
                ·
              </span>
              <Link
                href={`/artifacts/${reportArtifactId}`}
                className="font-medium text-[var(--foreground)] underline decoration-dotted underline-offset-2"
              >
                Report file
              </Link>
            </>
          ) : null}
        </div>
        {topEvidence.length > 0 ? (
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 border-t border-[var(--border)] pt-2 text-[11px] text-[var(--muted)] sm:border-t-0 sm:border-l sm:pl-4 sm:pt-0">
            <span className="shrink-0 font-medium text-[var(--foreground)]">Evidence:</span>
            {topEvidence.map((l) => (
              <Link
                key={`${l.role}-${l.artifactId}`}
                href={`/artifacts/${l.artifactId}`}
                className="truncate font-mono underline decoration-dotted underline-offset-2"
                title={l.role}
              >
                {l.role}
              </Link>
            ))}
            {evidenceLinks.length > topEvidence.length ? (
              <Link href={artifactsTableHref} className="shrink-0 underline decoration-dotted underline-offset-2">
                +{evidenceLinks.length - topEvidence.length} more
              </Link>
            ) : null}
          </div>
        ) : null}
        {canExecute ? (
          <div className="flex items-center gap-2 border-t border-[var(--border)] pt-2 sm:ml-auto sm:border-t-0 sm:pt-0 md:border-l md:pl-4">
            <ExecuteRunButton projectId={projectId} runId={runId} size="compact" actionLabel="Re-run" />
          </div>
        ) : null}
      </div>
    </section>
  );
}
