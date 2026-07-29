"use client";

import { Check, X } from "lucide-react";

import { PIPELINE_PHASES, type PipelinePhaseView } from "@/lib/run-pipeline-phases";

/**
 * Live pipeline progress while a run executes. Driven by real phase state polled from
 * the run's committed steps (see getRunProgress + the incremental commits in
 * traceable_analysis_pipeline). Before the first poll lands, shows a "starting" view.
 */
const STARTING_VIEW: PipelinePhaseView = {
  headline: "Starting analysis…",
  lines: PIPELINE_PHASES.map((p, i) => ({
    id: p.id,
    label: p.label,
    state: i === 0 ? "current" : "upcoming",
  })),
};

export function ChatRunProgress({ view, onStop }: { view?: PipelinePhaseView; onStop?: () => void }) {
  const { lines, headline } = view ?? STARTING_VIEW;

  return (
    <div className="mx-auto w-full max-w-[58rem]">
      <div className="rounded-card border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="h-4 w-4 shrink-0 rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] motion-safe:animate-spin"
              aria-hidden="true"
            />
            <p className="truncate text-[13px] font-semibold tracking-[-0.01em] text-[var(--foreground)]">
              {headline}
            </p>
          </div>
          {onStop ? (
            <button
              type="button"
              onClick={onStop}
              className="shrink-0 rounded-control border border-[var(--border)] px-2.5 py-1 text-[12px] font-medium text-[var(--muted)] transition-colors hover:border-[var(--foreground)]/30 hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              Stop
            </button>
          ) : null}
        </div>

        <ol className="mt-4 space-y-2.5" aria-label="Analysis progress">
          {lines.map((line) => {
            const done = line.state === "done";
            const current = line.state === "current";
            const failed = line.state === "failed";
            return (
              <li key={line.id} className="flex items-center gap-3">
                <span
                  className={
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full " +
                    (done
                      ? "bg-[var(--chat-primary)] text-[var(--chat-primary-ink)]"
                      : failed
                        ? "bg-red-600 text-white"
                        : current
                          ? "border-2 border-[var(--accent)] border-t-transparent motion-safe:animate-spin"
                          : "border border-[var(--border)]")
                  }
                  aria-hidden="true"
                >
                  {done ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                  {failed ? <X className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                </span>
                <span
                  className={
                    "text-[13.5px] leading-6 " +
                    (done || current || failed ? "text-[var(--foreground)]" : "text-[var(--muted)]")
                  }
                >
                  {line.label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
