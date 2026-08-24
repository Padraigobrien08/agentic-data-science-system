/**
 * The trace as the experimental loop it was.
 *
 * Grouped by iteration, a trace answers "what did it do next". That is the wrong question.
 * A reader wants to know what was claimed, whether it held, and what was done to find out —
 * and those three things are spread across iterations, so iteration order actively hides
 * them. A claim proposed in iteration 0, tested in 1, challenged in 2 and weakened in 3
 * appears as four unrelated rows in four places.
 *
 * So the unit here is the claim. Each one states itself, says where it landed, and carries
 * the steps taken to test it underneath — the experiments raised against it, the evidence
 * they produced, and the decisions that moved it. Sequence order is preserved within a
 * claim, because the order things happened is the story.
 *
 * Everything is a regrouping of persisted state. Nothing is inferred: a decision that names
 * no claim goes to a shared bucket rather than being attributed to a guess.
 */

import type {
  DecisionItem,
  EvidenceItem,
  ExperimentItem,
  HypothesisItem,
  InvestigationDetail,
} from "@/lib/api/types";
import { decisionGlyph, decisionLabel } from "@/lib/trace-view";

export type ClaimStepKind = "decision" | "experiment" | "evidence";

export type ClaimStep = {
  id: string;
  kind: ClaimStepKind;
  glyph: string;
  label: string;
  /** Monospace tail — the tool that ran, or the direction evidence pointed. */
  accent?: string;
  detail?: string;
  /** Orders steps within a claim; not shown. */
  sequence: number;
};

export type ClaimTrack = {
  id: string;
  statement: string;
  /** `supported` / `weakened` / `rejected` / `unresolved`, straight from the run. */
  status: string;
  confidence: number;
  /** One line naming the outcome in words, for readers who do not know the vocabulary. */
  verdict: string;
  supportingEvidence: number;
  refutingEvidence: number;
  experiments: string[];
  steps: ClaimStep[];
};

export type ClaimTrace = {
  claims: ClaimTrack[];
  /**
   * Steps belonging to the run rather than to any one claim — planning, the conclusion, and
   * anything whose targets were never recorded. Never silently attached to a claim.
   */
  shared: ClaimStep[];
};

const VERDICTS: Record<string, string> = {
  supported: "Held up",
  weakened: "Did not hold",
  rejected: "Rejected",
  unresolved: "Left unresolved",
  active: "Still open when the run stopped",
  proposed: "Never tested",
};

export function claimVerdict(status: string): string {
  return VERDICTS[status] ?? status;
}

function evidenceLabel(e: EvidenceItem): string {
  return e.claim || "Evidence recorded";
}

/**
 * Which claims a decision acted on, from its structured targets.
 *
 * Only `kind: "hypothesis"` counts. A decision targeting an experiment is about the
 * experiment; attributing it to whatever claim happens to be nearby would be a guess.
 */
function decisionClaims(d: DecisionItem): string[] {
  return (d.targets ?? []).filter((t) => t.kind === "hypothesis").map((t) => t.id);
}

export function claimTrace(detail: InvestigationDetail): ClaimTrace {
  const tracks = new Map<string, ClaimTrack>();
  for (const h of detail.hypotheses) {
    tracks.set(h.id, {
      id: h.id,
      statement: h.statement,
      status: h.status,
      confidence: h.confidence,
      verdict: claimVerdict(h.status),
      supportingEvidence: 0,
      refutingEvidence: 0,
      experiments: [],
      steps: [],
    });
  }

  const shared: ClaimStep[] = [];
  const push = (claimIds: string[], step: ClaimStep) => {
    const targets = claimIds.map((id) => tracks.get(id)).filter((t): t is ClaimTrack => !!t);
    if (!targets.length) {
      shared.push(step);
      return;
    }
    // A step bearing on two claims belongs to both. Filing it under the first would
    // misrepresent the second — a contradiction is exactly this case.
    for (const t of targets) t.steps.push({ ...step, id: `${t.id}:${step.id}` });
  };

  for (const d of detail.decisions) {
    push(decisionClaims(d), {
      id: d.id,
      kind: "decision",
      glyph: decisionGlyph(d.decision_type),
      label: decisionLabel(d.decision_type),
      accent: d.chosen_option ?? undefined,
      detail: d.rationale,
      sequence: d.sequence,
    });
  }

  // Experiments carry the claims they were raised to test. Runs recorded before that link
  // was persisted have none, and land in `shared` rather than being attributed by guess.
  detail.experiments.forEach((x: ExperimentItem, i) => {
    const targets = x.target_hypothesis_ids ?? [];
    for (const id of targets) tracks.get(id)?.experiments.push(x.tool_name);
    push(targets, {
      id: x.id,
      kind: "experiment",
      glyph: "▶",
      label: "Ran experiment",
      accent: x.tool_name,
      detail: x.summary ?? undefined,
      // After the decisions that proposed it, before the evidence it produced.
      sequence: detail.decisions.length + i,
    });
  });

  for (const e of detail.evidence) {
    const ids = e.hypothesis_ids ?? [];
    for (const id of ids) {
      const t = tracks.get(id);
      if (!t) continue;
      if (e.direction === "refutes") t.refutingEvidence += 1;
      else t.supportingEvidence += 1;
    }
    push(ids, {
      id: e.id,
      kind: "evidence",
      glyph: e.direction === "refutes" ? "−" : "+",
      label: evidenceLabel(e),
      accent: e.direction,
      sequence: detail.decisions.length + detail.experiments.length,
    });
  }

  for (const t of tracks.values()) t.steps.sort((a, b) => a.sequence - b.sequence);
  shared.sort((a, b) => a.sequence - b.sequence);

  return { claims: [...tracks.values()], shared };
}

/** One line summarising a claim's testing, for the collapsed row. */
export function claimSummary(track: ClaimTrack): string {
  const parts: string[] = [];
  if (track.experiments.length) {
    parts.push(`${track.experiments.length} experiment${track.experiments.length === 1 ? "" : "s"}`);
  }
  const evidence = track.supportingEvidence + track.refutingEvidence;
  if (evidence) {
    parts.push(
      track.refutingEvidence
        ? `${track.supportingEvidence} for · ${track.refutingEvidence} against`
        : `${track.supportingEvidence} supporting`,
    );
  }
  if (!parts.length) return `${track.steps.length} step${track.steps.length === 1 ? "" : "s"}`;
  return parts.join(" · ");
}

/** A hypothesis's evidence split, for callers that only need the counts. */
export function evidenceSplit(
  hypothesis: HypothesisItem,
  evidence: EvidenceItem[],
): { supporting: number; refuting: number } {
  let supporting = 0;
  let refuting = 0;
  for (const e of evidence) {
    if (!(e.hypothesis_ids ?? []).includes(hypothesis.id)) continue;
    if (e.direction === "refutes") refuting += 1;
    else supporting += 1;
  }
  return { supporting, refuting };
}
