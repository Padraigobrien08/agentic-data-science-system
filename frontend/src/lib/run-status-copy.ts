import type { AnalysisRunStatus } from "@/lib/api/types";

export function shouldPollRunStatus(status: AnalysisRunStatus): boolean {
  return status === "queued" || status === "running";
}

const FRIENDLY_LABEL: Record<AnalysisRunStatus, string> = {
  pending: "Not started",
  queued: "Queued",
  running: "Running",
  success: "Completed",
  partial_success: "Partial result",
  no_data: "No usable data",
  error: "Failed",
  cancelled: "Cancelled",
};

export function formatRunStatusLabel(status: AnalysisRunStatus): string {
  return FRIENDLY_LABEL[status] ?? status;
}

/** One-line explanation for tooltips and engineers. */
export function runStatusExplanation(status: AnalysisRunStatus): string {
  switch (status) {
    case "pending":
      return "The run record exists but the pipeline has not been executed yet.";
    case "queued":
      return "Waiting for a background worker to pick up this run.";
    case "running":
      return "Pipeline steps are executing; pages refresh automatically while in this state.";
    case "success":
      return "Finished without blocking errors.";
    case "partial_success":
      return "Finished with gaps or weaker phases — verify in deep dive before high-stakes use.";
    case "no_data":
      return "Finished without analyzable output for this goal — check inputs, tickers, and trace.";
    case "error":
      return "Execution stopped with an error; see the error panel when present.";
    case "cancelled":
      return "Stopped before completion; partial trace may still exist.";
    default:
      return status;
  }
}

export function runStatusBadgeTitle(status: AnalysisRunStatus): string {
  return `${formatRunStatusLabel(status)} (${status}) — ${runStatusExplanation(status)}`;
}

export type RunStateBannerSurface = "run-answer" | "trace";

export type RunStateBannerTone = "neutral" | "sky" | "amber" | "orange" | "violet" | "red";

export type RunStateBannerModel = {
  tone: RunStateBannerTone;
  title: string;
  body: string;
  showOutcomeCta: boolean;
  /** Extra line for in-flight states (progress / where to look). */
  progressLine?: string;
};

function progressCopy(surface: RunStateBannerSurface): string {
  return surface === "trace"
    ? "This view refreshes every few seconds while the run is active."
    : "This page refreshes every few seconds while the run is active.";
}

export function getRunStateBannerModel(
  status: AnalysisRunStatus,
  surface: RunStateBannerSurface,
): RunStateBannerModel | null {
  if (status === "success") {
    return null;
  }

  switch (status) {
    case "pending":
      return {
        tone: "neutral",
        title: "Ready to execute",
        body: "Nothing has run against this goal yet. When you execute the pipeline, status will move to queued or running.",
        showOutcomeCta: true,
      };
    case "queued":
      return {
        tone: "sky",
        title: "Queued for worker",
        body: "The job is waiting for an available worker. You can open deep dive now to watch steps and artifacts appear as they are recorded.",
        showOutcomeCta: true,
        progressLine: progressCopy(surface),
      };
    case "running":
      return {
        tone: "amber",
        title: "Pipeline running",
        body: "Steps are executing. Partial summaries and artifacts may appear before the run finishes.",
        showOutcomeCta: true,
        progressLine: progressCopy(surface),
      };
    case "partial_success":
      return {
        tone: "orange",
        title: "Partial success",
        body: "The pipeline completed but some phases reported gaps, skipped work, or lower confidence. Treat the primary answer as directional: verify critical claims in deep dive and linked artifacts before decisions.",
        showOutcomeCta: true,
      };
    case "no_data":
      return {
        tone: "violet",
        title: "No data outcome",
        body: "The run finished without enough structured output for a full answer (for example, no rows, empty panels, or filters excluded all sources). Use deep dive to see which tools ran, then adjust inputs or scope and retry if appropriate.",
        showOutcomeCta: true,
      };
    case "error":
      return {
        tone: "red",
        title: "Run ended with an error",
        body: "See the error summary when it is shown below. Deep dive may still list partial steps useful for debugging.",
        showOutcomeCta: true,
      };
    case "cancelled":
      return {
        tone: "neutral",
        title: "Cancelled",
        body: "This run was stopped before completion. Deep dive may still contain a partial trace.",
        showOutcomeCta: true,
      };
  }
}
