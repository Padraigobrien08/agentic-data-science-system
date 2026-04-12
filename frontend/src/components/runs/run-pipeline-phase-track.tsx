import type { AnalysisRunStatus, RunStepDetail } from "@/lib/api/types";
import { derivePipelinePhaseView, type PipelinePhaseLineState } from "@/lib/run-pipeline-phases";

function stateStyles(state: PipelinePhaseLineState): { row: string; marker: string; label: string } {
  switch (state) {
    case "current":
      return {
        row: "border-l-2 border-amber-500 bg-amber-50/40 pl-3 dark:border-amber-400 dark:bg-amber-950/20",
        marker: "border-amber-600 bg-amber-100 text-amber-950 ring-2 ring-amber-400/50 dark:border-amber-300 dark:bg-amber-900 dark:text-amber-50",
        label: "font-semibold text-[var(--foreground)]",
      };
    case "done":
      return {
        row: "border-l-2 border-emerald-500/70 pl-3 dark:border-emerald-600/60",
        marker: "border-emerald-600/80 bg-emerald-100 text-emerald-900 dark:border-emerald-500 dark:bg-emerald-950 dark:text-emerald-100",
        label: "text-[var(--muted)]",
      };
    case "failed":
      return {
        row: "border-l-2 border-red-500 bg-red-50/50 pl-3 dark:border-red-500 dark:bg-red-950/25",
        marker: "border-red-600 bg-red-100 text-red-900 dark:border-red-400 dark:bg-red-900 dark:text-red-50",
        label: "font-medium text-red-900 dark:text-red-50",
      };
    case "skipped":
      return {
        row: "border-l-2 border-[var(--border)] pl-3 opacity-60",
        marker: "border-[var(--border)] bg-neutral-100 text-[var(--muted)] dark:bg-neutral-800",
        label: "text-[var(--muted)] line-through decoration-[var(--muted)]/50",
      };
    default:
      return {
        row: "border-l-2 border-dashed border-[var(--border)] pl-3",
        marker: "border-[var(--border)] bg-[var(--background)] text-[var(--muted)]",
        label: "text-[var(--muted)]",
      };
  }
}

function markerGlyph(state: PipelinePhaseLineState): string {
  switch (state) {
    case "done":
      return "✓";
    case "current":
      return "●";
    case "failed":
      return "!";
    case "skipped":
      return "—";
    default:
      return "○";
  }
}

type Props = {
  status: AnalysisRunStatus;
  steps: RunStepDetail[];
  /** Visually anchor under banners / headers. */
  className?: string;
};

/**
 * Read-only pipeline checklist derived from `AnalysisRunStatus` + persisted `RunStep` rows.
 * Updates when the server page revalidates (same cadence as existing polling).
 */
export function RunPipelinePhaseTrack({ status, steps, className }: Props) {
  const { lines, headline } = derivePipelinePhaseView(status, steps);

  return (
    <section
      className={
        className ??
        "rounded-xl border border-[var(--border)] bg-neutral-50/60 px-4 py-4 dark:bg-neutral-950/40"
      }
      aria-label="Execution phases"
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">How this run is progressing</p>
      <p className="mt-1.5 text-sm leading-snug text-[var(--foreground)]">{headline}</p>
      <ol className="mt-4 space-y-0">
        {lines.map((line) => {
          const s = stateStyles(line.state);
          return (
            <li key={line.id} className={`relative py-2 ${s.row}`}>
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold ${s.marker}`}
                  aria-hidden
                >
                  {markerGlyph(line.state)}
                </span>
                <div className="min-w-0 pt-0.5">
                  <span className={`text-sm leading-snug ${s.label}`}>{line.label}</span>
                  {line.state === "current" ? (
                    <span className="mt-0.5 block text-[11px] text-[var(--muted)]">Working through this stage…</span>
                  ) : null}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
