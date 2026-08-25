import type { InvestigationDetail } from "@/lib/api/types";

/**
 * The landing page's trace panel, derived from a published run.
 *
 * It used to be hand-typed JSX carrying a comment that promised "every id, confidence and
 * count below matches the published export". The counts did. The iteration stamps did not —
 * the panel showed a tidy four-iteration arc for a run that took eight, put the critique at
 * iteration 3 when it happened at 5, and described evidence as "artifact · linked" while
 * every evidence record in the export had a null link.
 *
 * None of that was dishonesty; it was a transcription made once and then left behind by the
 * data. Which is the point: a marketing surface that restates numbers by hand will drift from
 * them, and this is the one page whose entire claim is that its numbers can be checked. So it
 * reads the export instead, and `landing-trace.test.ts` holds it to the same run.
 */

export type TraceLine = {
  /** Left gutter: iteration stamp, or "stop" for the terminal line. */
  stamp: string;
  /** The decision or event, in the loop's own vocabulary. */
  event: string;
  /** Trailing detail. `tone` decides how it reads, not what it says. */
  detail: string;
  tone: "muted" | "tool" | "supported" | "rejected" | "terminal";
};

const DECISION_EVENT: Record<string, string> = {
  propose_hypothesis: "propose_hypothesis",
  select_experiment: "select_experiment",
  update_evidence: "record_evidence",
  revise_confidence: "revise_claim",
  request_critique: "critique",
  conclude: "conclude",
};

function statusTone(status: string): TraceLine["tone"] {
  if (status === "supported") return "supported";
  if (status === "rejected" || status === "weakened") return "rejected";
  return "muted";
}

/**
 * Condense a run into the handful of lines worth showing.
 *
 * Not every decision: a seven-experiment run produces twenty-five, and a wall of them is
 * scrolling rather than evidence. The selection is the shape of the loop — what it claimed,
 * what it ran, what changed its mind, what it stopped for — with the counts underneath.
 */
export function buildLandingTrace(detail: InvestigationDetail): TraceLine[] {
  const lines: TraceLine[] = [];
  const iterationOf = (iteration: number | null | undefined) =>
    `iter ${iteration ?? 0}`;

  const proposals = detail.decisions.filter((d) => d.decision_type === "propose_hypothesis");
  if (proposals.length) {
    lines.push({
      stamp: iterationOf(proposals[0].iteration),
      event: DECISION_EVENT.propose_hypothesis,
      detail: `→ ${detail.hypotheses.length} competing claims`,
      tone: "muted",
    });
  }

  const firstExperiment = detail.decisions.find((d) => d.decision_type === "select_experiment");
  if (firstExperiment) {
    lines.push({
      stamp: iterationOf(firstExperiment.iteration),
      event: DECISION_EVENT.select_experiment,
      detail: firstExperiment.chosen_option ?? "",
      tone: "tool",
    });
  }

  // Evidence is shown with its link to the computation, because that link is the product.
  const linked = detail.evidence.filter((e) => e.experiment_result_id).length;
  if (detail.evidence.length) {
    const first = detail.decisions.find((d) => d.decision_type === "update_evidence");
    lines.push({
      stamp: iterationOf(first?.iteration),
      event: `record_evidence[${detail.evidence.length}]`,
      detail:
        linked === detail.evidence.length
          ? "each linked to the experiment that computed it"
          : `${linked}/${detail.evidence.length} linked to an experiment`,
      tone: "muted",
    });
  }

  // A claim the run's own evidence overturned, if there is one — the most load-bearing line
  // on the page, so it is taken from the hypothesis rather than from prose about it.
  const overturned = detail.hypotheses.find(
    (h) => h.status === "rejected" || h.status === "weakened",
  );
  if (overturned) {
    const revision = detail.decisions.find((d) => d.decision_type === "revise_confidence");
    lines.push({
      stamp: iterationOf(revision?.iteration),
      event: "revise_claim",
      detail: `${overturned.status} (${overturned.confidence.toFixed(2)})`,
      tone: statusTone(overturned.status),
    });
  }

  const critique = detail.critiques[0];
  if (critique) {
    const raised = detail.decisions.find((d) => d.decision_type === "request_critique");
    lines.push({
      stamp: iterationOf(raised?.iteration),
      event: "critique",
      detail: `challenges its strongest claim → ${critique.suggested_action ?? "no tool"}`,
      tone: "muted",
    });
    // Whether the nominated tool actually ran. A critique the loop never acts on is a note.
    const acted = detail.experiments.some((x) => x.tool_name === critique.suggested_action);
    const ranAt = detail.decisions.find(
      (d) => d.decision_type === "select_experiment" && d.chosen_option === critique.suggested_action,
    );
    lines.push({
      stamp: iterationOf(ranAt?.iteration),
      event: acted ? "ran it" : "not run",
      detail: acted ? "critique acted on, not noted" : "no candidate left to run it",
      tone: "muted",
    });
  }

  const upheld = detail.hypotheses.find((h) => h.status === "supported");
  if (upheld) {
    lines.push({
      stamp: iterationOf(detail.termination?.at_iteration),
      event: "claim upheld",
      detail: `supported (${upheld.confidence.toFixed(2)})`,
      tone: "supported",
    });
  }

  if (detail.termination?.reason) {
    lines.push({
      stamp: "stop",
      event: detail.termination.reason,
      detail: `conclusion: ${detail.conclusion_detail?.disposition ?? detail.outcome.kind}`,
      tone: "terminal",
    });
  }

  return lines;
}

/** The footer counts, in the same order the README states them. */
export function buildLandingCounts(detail: InvestigationDetail): string {
  const artifacts = detail.experiments.reduce((n, x) => n + x.artifacts.length, 0);
  return [
    `${detail.experiments.length} experiments`,
    `${detail.evidence.length} evidence`,
    `${artifacts} artifacts`,
  ].join(" · ");
}
