/**
 * One vocabulary for reading a trace, whatever produced it.
 *
 * The product has two kinds of trace and they were drifting apart: an adaptive investigation
 * records decisions grouped by iteration, and an analysis run records pipeline steps. They
 * are different data, but they answer the same question in the same shape — *what did it do,
 * in what order, and why* — and a reader who has learned to read one should not have to
 * learn the other.
 *
 * So the shape lives here and the two sources adapt into it. This is presentation only: no
 * adapter computes a number, and neither invents an ordering the source does not carry.
 */

import type { DecisionItem, HypothesisItem, RunStepDetail } from "@/lib/api/types";
import { formatConfidence } from "@/lib/investigation-view";
import { decisionGlyph, decisionLabel, groupDecisionsByIteration } from "@/lib/trace-view";

export type TimelineTone = "default" | "notice" | "danger";

export type TimelineEntry = {
  id: string;
  /** Terse mark in the gutter — the decision/step vocabulary, not decoration. */
  glyph: string;
  label: string;
  /** Monospace tail on the label: the tool, the step key. */
  accent?: string;
  detail?: string;
  tone?: TimelineTone;
  /**
   * Replaces the row entirely when several records are one act — the contradiction pair
   * being the case that motivated it. `items` are the records it collapsed, kept so the
   * callout can show what it merged rather than asking the reader to take its word.
   */
  callout?: { heading: string; body: string; items?: { id: string; text: string; meta?: string }[] };
};

export type TimelineGroup = {
  id: string;
  /** "iter 0", "Steps 1–6" — whatever the source groups by. */
  label: string;
  /** Counts and anything notable about the group, already phrased. */
  meta: string;
  entries: TimelineEntry[];
};

function plural(n: number, one: string): string {
  return `${n} ${one}${n === 1 ? "" : "s"}`;
}

/**
 * An adaptive investigation: decisions, grouped by the iteration that made them.
 */
export function investigationTimeline(
  decisions: DecisionItem[],
  hypotheses: HypothesisItem[] = [],
): TimelineGroup[] {
  return groupDecisionsByIteration(decisions, hypotheses).map((group) => ({
    id: `iter-${group.iteration}`,
    label: group.label,
    meta: `${plural(group.decisionCount, "decision")}${
      group.hasContradiction ? " · contradiction" : ""
    }`,
    entries: group.rows.map((row) =>
      row.kind === "contradiction"
        ? {
            id: row.decisions[0].id,
            glyph: "±",
            label: "Contradiction",
            tone: "notice" as const,
            callout: {
              heading: `One event · ${row.decisions.length} confidence revisions`,
              body: "Both claims weakened: they cannot hold at the same time as each other.",
              // Where each claim landed, deliberately not a before/after arrow: the
              // confidence immediately before the contradiction is recorded nowhere —
              // `prior_confidence` is the claim's original prior, so both sides would read
              // "50% → 50%" and imply the contradiction changed nothing.
              items: row.claims.map((c) => ({
                id: c.id,
                text: c.statement,
                meta: `${c.status} · ${formatConfidence(c.confidence)}`,
              })),
            },
          }
        : {
            id: row.decision.id,
            glyph: decisionGlyph(row.decision.decision_type),
            label: decisionLabel(row.decision.decision_type),
            accent: row.decision.chosen_option ?? undefined,
            detail: row.decision.rationale,
          },
    ),
  }));
}

/** Steps that failed are the ones a reader is looking for; they carry the tone. */
function stepTone(status: string): TimelineTone {
  if (status === "error" || status === "failed") return "danger";
  if (status === "skipped" || status === "cancelled") return "notice";
  return "default";
}

const STEP_GLYPHS: Record<string, string> = {
  success: "▶",
  completed: "▶",
  error: "⚑",
  failed: "⚑",
  running: "•",
  pending: "·",
  skipped: "·",
  cancelled: "·",
};

/**
 * An analysis run: pipeline steps, in the order they executed.
 *
 * Grouped by status transition rather than by iteration, because a run has no iterations —
 * it has one pass whose interesting structure is where it stopped succeeding. A run that
 * went cleanly through is one group; one that failed part-way splits at the failure, which
 * is the point a reader is looking for.
 */
export function runTimeline(steps: RunStepDetail[]): TimelineGroup[] {
  const ordered = [...steps].sort((a, b) => a.step_index - b.step_index);
  if (!ordered.length) return [];

  const groups: TimelineGroup[] = [];
  let current: { tone: TimelineTone; steps: RunStepDetail[] } | null = null;

  for (const step of ordered) {
    const tone = stepTone(step.status);
    if (!current || current.tone !== tone) {
      current = { tone, steps: [] };
      groups.push({
        id: `steps-${step.step_index}`,
        label: "",
        meta: "",
        entries: [],
      });
    }
    current.steps.push(step);
    const group = groups[groups.length - 1];
    group.entries.push({
      id: step.id,
      glyph: STEP_GLYPHS[step.status] ?? "·",
      label: step.label?.trim() || `Step ${step.step_index + 1}`,
      accent: step.planned_tool_name ?? undefined,
      detail: step.detail ?? undefined,
      tone,
    });
    const first = current.steps[0].step_index + 1;
    const last = step.step_index + 1;
    group.label = first === last ? `step ${first}` : `steps ${first}–${last}`;
    group.meta =
      current.tone === "default"
        ? plural(current.steps.length, "step")
        : `${plural(current.steps.length, "step")} · ${current.steps[0].status}`;
  }

  return groups;
}
