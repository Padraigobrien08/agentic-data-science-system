import Link from "next/link";

import type { EvidenceSummaryProps } from "./types";

/** Role → artifact links; mentions extras without listing huge tables. */
export function EvidenceSummary({ links, extraArtifactCount, className }: EvidenceSummaryProps) {
  const hasLinks = links.length > 0;
  const hasExtras = extraArtifactCount > 0;

  if (!hasLinks && !hasExtras) {
    return <p className="text-sm text-[var(--muted)]">No evidence artifact map on this run yet.</p>;
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
    </div>
  );
}
