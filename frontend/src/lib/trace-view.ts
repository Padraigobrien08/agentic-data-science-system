/**
 * Shaping a recorded run into something readable.
 *
 * The trace is stored flat — a decision list, an evidence list — because that is how it was
 * produced, one append at a time. Read back flat it is a wall: fifteen rows that do not say
 * which belong together, evidence detached from the experiment that computed it, and a
 * contradiction showing up as two unrelated confidence revisions.
 *
 * These are pure regroupings of persisted state. Nothing here invents a number, and where a
 * grouping cannot be established from the data it degrades to "ungrouped" rather than
 * guessing.
 */

import type {
  CritiqueItem,
  DecisionItem,
  EvidenceItem,
  ExperimentItem,
  HypothesisItem,
} from "@/lib/api/types";

/** Glyphs mirror the decision vocabulary; the label is the type made readable. */
const DECISION_GLYPHS: Record<string, string> = {
  propose_hypothesis: "◇",
  select_experiment: "▶",
  update_evidence: "≡",
  revise_confidence: "±",
  request_critique: "⚑",
  conclude: "•",
};

export function decisionGlyph(type: string): string {
  return DECISION_GLYPHS[type] ?? "·";
}

export function decisionLabel(type: string): string {
  const words = type.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export type ContradictionEvent = {
  kind: "contradiction";
  /** The decisions collapsed into this one event, in sequence order. */
  decisions: DecisionItem[];
  /** Every hypothesis involved, from the decisions' structured targets. */
  hypothesisIds: string[];
  claims: HypothesisItem[];
};

export type TraceRow =
  | { kind: "decision"; decision: DecisionItem }
  | ContradictionEvent;

export type IterationGroup = {
  iteration: number;
  label: string;
  rows: TraceRow[];
  /** Decision count, counting a collapsed contradiction as the acts it contains. */
  decisionCount: number;
  hasContradiction: boolean;
};

/** A contradiction is recorded as one weakening per claim; the pair is one act. */
const CONTRADICTION_MARKER = "cannot hold at the same time";

function isContradictionDecision(d: DecisionItem): boolean {
  return d.decision_type === "revise_confidence" && d.rationale.includes(CONTRADICTION_MARKER);
}

/**
 * Group decisions by the iteration they were made in, collapsing a contradiction into one row.
 *
 * The pair is recognised from the decisions' `targets`, not from their text: each carries both
 * hypotheses, so two decisions naming the same pair are the same act. Falls back to leaving
 * them as separate rows if the targets are missing, which is what older recorded runs look
 * like — they were written before the ids were structured.
 */
export function groupDecisionsByIteration(
  decisions: DecisionItem[],
  hypotheses: HypothesisItem[] = [],
): IterationGroup[] {
  const byId = new Map(hypotheses.map((h) => [h.id, h]));
  const ordered = [...decisions].sort((a, b) => a.sequence - b.sequence);
  const groups = new Map<number, IterationGroup>();

  const groupFor = (iteration: number): IterationGroup => {
    let g = groups.get(iteration);
    if (!g) {
      g = {
        iteration,
        label: `iter ${iteration}`,
        rows: [],
        decisionCount: 0,
        hasContradiction: false,
      };
      groups.set(iteration, g);
    }
    return g;
  };

  const consumed = new Set<string>();
  for (const d of ordered) {
    if (consumed.has(d.id)) continue;
    const group = groupFor(d.iteration);

    if (isContradictionDecision(d) && d.targets.length >= 2) {
      const pairKey = [...d.targets.map((t) => t.id)].sort().join("|");
      const partner = ordered.find(
        (o) =>
          o.id !== d.id &&
          !consumed.has(o.id) &&
          o.iteration === d.iteration &&
          isContradictionDecision(o) &&
          [...o.targets.map((t) => t.id)].sort().join("|") === pairKey,
      );
      if (partner) {
        consumed.add(d.id);
        consumed.add(partner.id);
        const ids = [...new Set(d.targets.map((t) => t.id))];
        group.rows.push({
          kind: "contradiction",
          decisions: [d, partner],
          hypothesisIds: ids,
          claims: ids.map((id) => byId.get(id)).filter((h): h is HypothesisItem => !!h),
        });
        group.decisionCount += 2;
        group.hasContradiction = true;
        continue;
      }
    }

    consumed.add(d.id);
    group.rows.push({ kind: "decision", decision: d });
    group.decisionCount += 1;
  }

  return [...groups.values()].sort((a, b) => a.iteration - b.iteration);
}

export type EvidenceGroup = {
  /** The claim this evidence bears on, or null for evidence linked to none. */
  claim: HypothesisItem | null;
  label: string;
  supporting: EvidenceItem[];
  refuting: EvidenceItem[];
  items: EvidenceItem[];
};

/**
 * Group evidence under the claim it bears on.
 *
 * Read flat, thirteen evidence rows say nothing about which claim any of them moved — and
 * "what supports this claim, and what argues against it" is the question a reader arrives
 * with. Grouping by the experiment that computed it would answer a different and currently
 * unanswerable question: the loop never populates `experiment_result_id`, so every item would
 * land in one "unattributed" pile.
 *
 * An item bearing on two claims appears under both. It genuinely is evidence for each, and
 * filing it under whichever came first would misrepresent the second.
 */
export function groupEvidenceByClaim(
  evidence: EvidenceItem[],
  hypotheses: HypothesisItem[],
): EvidenceGroup[] {
  const groups: EvidenceGroup[] = hypotheses.map((h) => ({
    claim: h,
    label: h.statement,
    supporting: [],
    refuting: [],
    items: [],
  }));
  const byId = new Map(groups.map((g) => [g.claim!.id, g]));
  const unlinked: EvidenceGroup = {
    claim: null,
    label: "Not linked to a claim",
    supporting: [],
    refuting: [],
    items: [],
  };

  for (const e of evidence) {
    const targets = e.hypothesis_ids
      .map((id) => byId.get(id))
      .filter((g): g is EvidenceGroup => !!g);
    for (const g of targets.length ? targets : [unlinked]) {
      g.items.push(e);
      (e.direction === "refutes" ? g.refuting : g.supporting).push(e);
    }
  }

  // Claim order, then anything that bears on none — the order the claims were proposed in.
  const out = groups.filter((g) => g.items.length > 0);
  if (unlinked.items.length) out.push(unlinked);
  return out;
}

export type TraceSection = {
  id: string;
  label: string;
  count: number;
  /** Short note about the section, or "" when the counts speak for themselves. */
  note: string;
};

/** The jump-rail entries, with the counts a reader uses to decide what to open. */
export function traceSections(detail: {
  decisions: DecisionItem[];
  hypotheses: HypothesisItem[];
  evidence: EvidenceItem[];
  experiments: ExperimentItem[];
  critiques: CritiqueItem[];
  open_questions: { id: string }[];
}): TraceSection[] {
  const unresolved = detail.critiques.filter((c) => !c.resolved).length;
  const artifacts = detail.experiments.reduce((n, x) => n + x.artifacts.length, 0);
  const weakened = detail.hypotheses.filter((h) => h.status === "weakened").length;

  return [
    {
      id: "decisions",
      label: "Decisions",
      count: detail.decisions.length,
      note: `${new Set(detail.decisions.map((d) => d.iteration)).size} iterations`,
    },
    {
      id: "hypotheses",
      label: "Hypotheses",
      count: detail.hypotheses.length,
      note: weakened === detail.hypotheses.length && weakened > 0 ? "all weakened" : "",
    },
    { id: "evidence", label: "Evidence", count: detail.evidence.length, note: "" },
    {
      id: "experiments",
      label: "Experiments",
      count: detail.experiments.length,
      note: artifacts ? `${artifacts} artifacts` : "",
    },
    {
      id: "critiques",
      label: "Critiques",
      count: detail.critiques.length,
      note: unresolved ? `${unresolved} unresolved` : "",
    },
    {
      id: "questions",
      label: "Open questions",
      count: detail.open_questions.length,
      note: "",
    },
  ];
}
