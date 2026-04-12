import { humanizeWeakEvidenceSignal } from "./signal-labels";
import type { CaveatBadgeGroupProps } from "./types";

function toneClasses(tone: "neutral" | "warning" | "info"): string {
  if (tone === "warning") {
    return "border-amber-400/70 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/35 dark:text-amber-50";
  }
  if (tone === "info") {
    return "border-blue-200 bg-blue-50 text-blue-950 dark:border-blue-900 dark:bg-blue-950/35 dark:text-blue-50";
  }
  return "border-[var(--border)] bg-[var(--background)] text-[var(--foreground)]";
}

/**
 * Weak-evidence ids, compact-context / truncation signals, and blocking caveat lines.
 * Badges only — no JSON dumps.
 */
export function CaveatBadgeGroup({
  blockingCaveats,
  weakEvidenceSignals,
  contextSignals,
  className,
}: CaveatBadgeGroupProps) {
  const weakLabels = weakEvidenceSignals.map(humanizeWeakEvidenceSignal);
  const hasBadges = weakLabels.length > 0 || contextSignals.length > 0;
  const hasBlocking = blockingCaveats.length > 0;

  if (!hasBadges && !hasBlocking) {
    return (
      <p className="mt-1 text-xs text-[var(--muted)]">No blocking caveats recorded in traceability.</p>
    );
  }

  return (
    <div className={className ?? "space-y-2"}>
      {hasBadges ? (
        <div className="flex flex-wrap gap-1.5">
          {contextSignals.map((s) => (
            <span
              key={s.id}
              className={`inline-flex max-w-full rounded-full border px-2 py-0.5 text-[10px] font-medium leading-tight ${toneClasses(s.tone)}`}
              title={s.label}
            >
              {s.label}
            </span>
          ))}
          {weakLabels.map((label, i) => (
            <span
              key={`${weakEvidenceSignals[i]}-${i}`}
              className={`inline-flex max-w-full rounded-full border px-2 py-0.5 text-[10px] font-medium leading-tight ${toneClasses("warning")}`}
            >
              {label}
            </span>
          ))}
        </div>
      ) : null}
      {hasBlocking ? (
        <ul className="list-inside list-disc text-xs text-amber-950 dark:text-amber-100">
          {blockingCaveats.map((c, i) => (
            <li key={i} className="max-w-prose">
              {c}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
