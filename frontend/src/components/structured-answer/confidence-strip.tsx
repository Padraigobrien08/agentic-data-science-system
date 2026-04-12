import type { ConfidenceStripProps } from "./types";

function confidenceLabel(v: string | null): string {
  if (!v) return "Not rated";
  return v.charAt(0).toUpperCase() + v.slice(1);
}

/** Evidence strength + phase status chips (no caveat prose — use CaveatBadgeGroup). */
export function ConfidenceStrip({
  overallConfidence,
  criticPhaseStatus,
  reportPhaseStatus,
  reliabilityNote,
  className,
}: ConfidenceStripProps) {
  return (
    <div className={className ?? "mt-2 space-y-1.5"}>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span className="text-[var(--foreground)]">
          Evidence strength: <strong>{confidenceLabel(overallConfidence)}</strong>
        </span>
        {criticPhaseStatus ? (
          <span className="font-mono text-xs text-[var(--muted)]">critic: {criticPhaseStatus}</span>
        ) : null}
        {reportPhaseStatus ? (
          <span className="font-mono text-xs text-[var(--muted)]">report: {reportPhaseStatus}</span>
        ) : null}
      </div>
      {reliabilityNote ? (
        <p className="max-w-prose text-[11px] leading-snug text-[var(--muted)]" title={reliabilityNote}>
          {reliabilityNote}
        </p>
      ) : null}
    </div>
  );
}
