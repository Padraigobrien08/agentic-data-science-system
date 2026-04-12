import type { AnswerSummaryProps } from "./types";

export function AnswerSummary({
  goalDisplay,
  summaryLine,
  orchestrationStatus,
  isQueued,
  runStatus,
  className,
}: AnswerSummaryProps) {
  return (
    <section className={className ?? "space-y-3"}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Conclusion</p>
      {isQueued ? (
        <p className="text-sm text-[var(--foreground)]">
          Run is queued for the worker. Refresh shortly — results will appear here when finished.
        </p>
      ) : (
        <>
          <p className="text-sm leading-relaxed text-[var(--foreground)]">
            {summaryLine ?? (
              <span className="text-[var(--muted)]">
                No orchestration summary yet{runStatus === "pending" ? " (run not executed)." : "."}
              </span>
            )}
          </p>
          {orchestrationStatus ? (
            <div className="flex flex-wrap gap-2 text-[11px] text-[var(--muted)]">
              <span className="rounded border border-[var(--border)] px-2 py-0.5 font-mono">
                orchestration: {orchestrationStatus}
              </span>
            </div>
          ) : null}
        </>
      )}
      <div className="rounded-lg border border-[var(--border)] bg-neutral-50/50 px-3 py-2 text-xs text-[var(--muted)] dark:bg-neutral-950/40">
        <span className="font-medium text-[var(--foreground)]">Goal · </span>
        {goalDisplay}
      </div>
    </section>
  );
}
