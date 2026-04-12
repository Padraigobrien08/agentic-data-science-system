import Link from "next/link";

import type { EvidenceSummaryProps } from "./types";

function inFlight(runStatus: EvidenceSummaryProps["runStatus"]): boolean {
  return runStatus === "queued" || runStatus === "running";
}

/** Role → artifact links; mentions extras without listing huge tables. */
export function EvidenceSummary({
  links,
  extraArtifactCount,
  provenanceHint,
  deepDiveHref,
  runStatus,
  className,
}: EvidenceSummaryProps) {
  const hasLinks = links.length > 0;
  const hasExtras = extraArtifactCount > 0;

  if (!hasLinks && !hasExtras) {
    const workerLine = inFlight(runStatus)
      ? "Evidence links usually appear as the worker writes artifacts — deep dive shows whatever is available so far."
      : "No evidence artifact map on this run yet — this is normal before execution or when the pipeline produced no linked roles.";
    return (
      <div className={className}>
        <p className="text-sm text-[var(--muted)]">{workerLine}</p>
        {provenanceHint ? (
          <p className="mt-2 text-[11px] leading-snug text-[var(--muted)]">
            {provenanceHint}{" "}
            {deepDiveHref ? (
              <Link href={deepDiveHref} className="font-medium text-[var(--foreground)] underline">
                Deep dive
              </Link>
            ) : null}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className={className ?? "space-y-2"}>
      {hasLinks ? (
        <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)]">
          {links.map(({ role, artifactId }) => (
            <li
              key={`${role}-${artifactId}`}
              className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
            >
              <span className="font-mono text-xs text-[var(--foreground)]">{role}</span>
              <Link href={`/artifacts/${artifactId}`} className="text-xs font-medium text-[var(--foreground)] underline">
                Open
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
      {hasExtras ? (
        <p className="text-xs text-[var(--muted)]">
          +{extraArtifactCount} other artifact{extraArtifactCount === 1 ? "" : "s"} (roles not in evidence map) —
          listed in deep dive.
        </p>
      ) : null}
      {provenanceHint ? (
        <p className="text-[11px] leading-snug text-[var(--muted)]">
          {provenanceHint}{" "}
          {deepDiveHref ? (
            <Link href={deepDiveHref} className="font-medium text-[var(--foreground)] underline">
              Deep dive
            </Link>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
