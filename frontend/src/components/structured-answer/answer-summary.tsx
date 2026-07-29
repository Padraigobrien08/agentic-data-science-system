import Link from "next/link";

import type { AnalysisRunStatus } from "@/lib/api/types";
import type { AnswerSummaryProps } from "./types";

function emptySummaryMessage(runStatus: AnalysisRunStatus): string {
  switch (runStatus) {
    case "pending":
      return "No orchestration summary yet (run not executed).";
    case "error":
      return "No orchestration summary — see the error summary when available.";
    case "cancelled":
      return "No orchestration summary — this run was cancelled.";
    case "partial_success":
      return "No short summary line was emitted — use top findings and deep dive to interpret partial output.";
    case "no_data":
      return "No summary for a no-data outcome — deep dive shows what ran and what came back empty.";
    case "queued":
    case "running":
      return "Conclusion text usually appears once reporting completes. Deep dive may already show partial steps and artifacts.";
    default:
      return "No orchestration summary yet.";
  }
}

export function AnswerSummary({
  goalDisplay,
  summaryLine,
  orchestrationStatus,
  runStatus,
  conclusionRider,
  className,
}: AnswerSummaryProps) {
  return (
    <section
      className={
        className ??
        "rounded-control border border-[var(--border)] bg-[var(--background)] px-4 py-5 shadow-sm sm:px-5 sm:py-6"
      }
    >
      <div className="space-y-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Conclusion</p>
          <p className="mt-2 text-[15px] font-normal leading-relaxed text-[var(--foreground)] sm:text-base">
            {summaryLine ?? (
              <span className="text-[15px] text-[var(--muted)] sm:text-base">{emptySummaryMessage(runStatus)}</span>
            )}
          </p>
        </div>
        {conclusionRider ? (
          <div className="rounded-control border border-[color:var(--status-warning-border)] bg-[var(--status-warning-bg)] px-2.5 py-2 text-[11px] leading-snug text-[var(--foreground)]">
            <span className="font-medium text-[var(--foreground)]">Note · </span>
            {conclusionRider.text}{" "}
            <Link href={conclusionRider.href} className="font-medium text-[var(--foreground)] underline">
              Trace
            </Link>
          </div>
        ) : null}
        <div className="border-t border-[var(--border)] pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Goal</p>
          <p className="mt-1.5 text-sm leading-relaxed text-[var(--foreground)]">{goalDisplay}</p>
        </div>
        {orchestrationStatus ? (
          <details className="group text-[11px] text-[var(--muted)]">
            <summary className="cursor-pointer list-none font-medium text-[var(--foreground)] marker:content-none [&::-webkit-details-marker]:hidden">
              <span className="underline decoration-dotted underline-offset-2 group-open:decoration-solid">
                Orchestration status
              </span>
              <span className="ml-1.5 font-normal text-[var(--muted)]">(technical)</span>
            </summary>
            <div className="mt-2 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-2 font-mono text-[10px] leading-snug">
              {orchestrationStatus}
            </div>
          </details>
        ) : null}
      </div>
    </section>
  );
}
