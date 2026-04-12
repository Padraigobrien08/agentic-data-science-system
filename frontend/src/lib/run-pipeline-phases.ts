import type { AnalysisRunStatus, RunStepDetail } from "@/lib/api/types";
import { stepLaneFromMeta } from "@/lib/run-trace-derive";

function metaRecord(meta: unknown): Record<string, unknown> | null {
  return meta && typeof meta === "object" && !Array.isArray(meta) ? (meta as Record<string, unknown>) : null;
}

/** Canonical pipeline stages (order matches the traceable EDGAR pipeline). */
export const PIPELINE_PHASES = [
  { id: "plan", label: "Understanding goal & plan" },
  { id: "panels", label: "Building panels & fetching data" },
  { id: "signals", label: "Analyzing & connecting signals" },
  { id: "review", label: "Quality review" },
  { id: "report", label: "Writing report & summary" },
] as const;

export type PipelinePhaseId = (typeof PIPELINE_PHASES)[number]["id"];

export type PipelinePhaseLineState = "done" | "current" | "upcoming" | "failed" | "skipped";

export type PipelinePhaseLine = {
  id: PipelinePhaseId;
  label: string;
  state: PipelinePhaseLineState;
};

export type PipelinePhaseView = {
  lines: PipelinePhaseLine[];
  headline: string;
};

function sortSteps(steps: RunStepDetail[]): RunStepDetail[] {
  return [...steps].sort((a, b) => a.step_index - b.step_index);
}

/**
 * Map a persisted run step to a pipeline phase index (0–4) using `meta_json.trace`
 * and fallbacks aligned with `traceable_analysis_pipeline` / `persist_mcp_trace`.
 */
export function classifyStepToPhaseIndex(step: RunStepDetail): number {
  const m = metaRecord(step.meta_json);
  const rawTrace = m && typeof m.trace === "string" ? m.trace : "";
  /** Prefer persisted `meta_json.trace` — `stepLaneFromMeta` maps e.g. `mcp_executor` → `executor`. */
  if (rawTrace === "report_agent") return 4;
  if (rawTrace === "critic_agent") return 3;
  if (rawTrace === "mcp_executor") return 1;

  const { trace } = stepLaneFromMeta(step.meta_json);
  if (trace === "report") return 4;
  if (trace === "critic") return 3;
  if (trace === "executor") return 1;

  const lab = `${step.label ?? ""} ${step.planned_tool_name ?? ""}`.toLowerCase();
  if (lab.includes("report")) return 4;
  if (lab.includes("critic")) return 3;
  if (lab.includes("mcp") || lab.includes("tool") || lab.includes("panel") || lab.includes("sec")) return 1;
  return 2;
}

function terminalSuccess(status: AnalysisRunStatus): boolean {
  return status === "success" || status === "partial_success" || status === "no_data";
}

function findActiveStep(sorted: RunStepDetail[]): RunStepDetail | null {
  return sorted.find((s) => s.status === "running" || s.status === "pending") ?? null;
}

/** Run steps use `error` / `skipped` / `no_data` — there is no `cancelled` step status. */
function findFailedStepForRun(status: AnalysisRunStatus, sorted: RunStepDetail[]): RunStepDetail | null {
  if (status === "error") {
    return [...sorted].reverse().find((s) => s.status === "error") ?? null;
  }
  if (status === "cancelled") {
    return [...sorted].reverse().find((s) => s.status === "error") ?? null;
  }
  return null;
}

/**
 * Deterministic phase index (0–4) from run lifecycle + persisted steps only.
 */
export function deriveCurrentPhaseIndex(status: AnalysisRunStatus, steps: RunStepDetail[]): number {
  const sorted = sortSteps(steps);

  if (status === "pending" || status === "queued") {
    return 0;
  }

  if (terminalSuccess(status)) {
    return 4;
  }

  const active = findActiveStep(sorted);
  if (active) {
    return classifyStepToPhaseIndex(active);
  }

  if (status === "running") {
    if (sorted.length === 0) return 0;
    const last = sorted[sorted.length - 1];
    if (last.status === "success" || last.status === "skipped" || last.status === "no_data") {
      const lastPhase = classifyStepToPhaseIndex(last);
      return Math.min(lastPhase + 1, 4);
    }
    return classifyStepToPhaseIndex(last);
  }

  if (status === "error" || status === "cancelled") {
    const failed = findFailedStepForRun(status, sorted);
    if (failed) return classifyStepToPhaseIndex(failed);
    return 0;
  }

  return 0;
}

function buildLines(
  status: AnalysisRunStatus,
  currentIdx: number,
  failedIdx: number | null,
): PipelinePhaseLine[] {
  return PIPELINE_PHASES.map((p, i) => {
    let state: PipelinePhaseLineState;
    if (failedIdx !== null) {
      if (i < failedIdx) state = "done";
      else if (i === failedIdx) state = "failed";
      else state = "skipped";
    } else if (terminalSuccess(status)) {
      state = "done";
    } else if (i < currentIdx) {
      state = "done";
    } else if (i === currentIdx) {
      state = "current";
    } else {
      state = "upcoming";
    }
    return { id: p.id, label: p.label, state };
  });
}

export function derivePipelinePhaseView(status: AnalysisRunStatus, steps: RunStepDetail[]): PipelinePhaseView {
  const sorted = sortSteps(steps);
  const failed =
    status === "error" || status === "cancelled" ? findFailedStepForRun(status, sorted) : null;
  const failedIdx = failed ? classifyStepToPhaseIndex(failed) : null;
  const currentIdx =
    failedIdx !== null && (status === "error" || status === "cancelled")
      ? failedIdx
      : deriveCurrentPhaseIndex(status, steps);

  let headline: string;
  if (status === "pending") {
    headline = "Ready to run — planning will start when you execute the pipeline.";
  } else if (status === "queued") {
    headline = "In queue — the worker will start with goal interpretation and planning.";
  } else if (terminalSuccess(status)) {
    headline = "Pipeline finished — all stages below completed for this run.";
  } else if (status === "error") {
    headline = failed
      ? `Stopped during: ${PIPELINE_PHASES[failedIdx as number].label}.`
      : "Run ended with an error before steps were recorded.";
  } else if (status === "cancelled") {
    headline = failed
      ? `Stopped during: ${PIPELINE_PHASES[failedIdx as number].label}.`
      : "Run was cancelled — completed stages are shown below.";
  } else if (status === "running") {
    headline = `Now: ${PIPELINE_PHASES[currentIdx].label}`;
  } else {
    headline = PIPELINE_PHASES[currentIdx].label;
  }

  if (status === "error" && failedIdx === null) {
    return {
      lines: PIPELINE_PHASES.map((p, i) => ({
        id: p.id,
        label: p.label,
        state: i === 0 ? ("failed" as const) : ("skipped" as const),
      })),
      headline,
    };
  }

  if (status === "cancelled" && failedIdx === null) {
    return {
      lines: PIPELINE_PHASES.map((p) => ({ id: p.id, label: p.label, state: "done" as const })),
      headline,
    };
  }

  const useFailedLayout = failedIdx !== null && (status === "error" || status === "cancelled");
  const lines = buildLines(status, currentIdx, useFailedLayout ? failedIdx : null);

  return { lines, headline };
}
