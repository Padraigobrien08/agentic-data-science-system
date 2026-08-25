import { describe, expect, it } from "vitest";

import type {
  DecisionItem,
  EvidenceItem,
  ExperimentItem,
  HypothesisItem,
} from "@/lib/api/types";
import {
  decisionGlyph,
  decisionLabel,
  groupDecisionsByIteration,
  groupEvidenceByClaim,
  traceSections,
} from "@/lib/trace-view";

let seq = 0;
function decision(over: Partial<DecisionItem> = {}): DecisionItem {
  seq += 1;
  return {
    id: `dec-${seq}`,
    sequence: seq,
    decision_type: "select_experiment",
    rationale: "because",
    iteration: 0,
    chosen_option: null,
    alternatives: [],
    targets: [],
    ...over,
  };
}

function hypothesis(id: string, over: Partial<HypothesisItem> = {}): HypothesisItem {
  return {
    id,
    statement: `claim ${id}`,
    status: "weakened",
    confidence: 0.5,
    prior_confidence: 0.95,
    rationale: null,
    metric_refs: [],
    entity_refs: [],
    ...over,
  };
}

function contradictionPair(ids: [string, string], iteration = 2): DecisionItem[] {
  const targets = ids.map((id) => ({ kind: "hypothesis", id }));
  return [
    decision({
      decision_type: "revise_confidence",
      rationale: `weakened: cannot hold at the same time as “claim ${ids[1]}”`,
      iteration,
      targets,
    }),
    decision({
      decision_type: "revise_confidence",
      rationale: `weakened: cannot hold at the same time as “claim ${ids[0]}”`,
      iteration,
      targets: [targets[1], targets[0]],
    }),
  ];
}

describe("groupDecisionsByIteration", () => {
  it("groups by iteration in loop order", () => {
    const groups = groupDecisionsByIteration([
      decision({ iteration: 2 }),
      decision({ iteration: 0 }),
      decision({ iteration: 1 }),
      decision({ iteration: 0 }),
    ]);

    expect(groups.map((g) => g.iteration)).toEqual([0, 1, 2]);
    expect(groups[0].decisionCount).toBe(2);
    expect(groups[0].label).toBe("iter 0");
  });

  it("orders rows within an iteration by sequence, not input order", () => {
    const later = decision({ iteration: 0, rationale: "second" });
    const earlier = decision({ iteration: 0, rationale: "first" });
    earlier.sequence = later.sequence - 10;

    const [group] = groupDecisionsByIteration([later, earlier]);

    const rationales = group.rows.map((r) => (r.kind === "decision" ? r.decision.rationale : ""));
    expect(rationales).toEqual(["first", "second"]);
  });

  it("collapses a contradiction pair into one event", () => {
    // The pair is one act — two claims weakened together — and rendering it as two
    // independent confidence revisions is what made the published trace misleading.
    const pair = contradictionPair(["h-a", "h-b"]);
    const claims = [hypothesis("h-a"), hypothesis("h-b")];

    const [group] = groupDecisionsByIteration(pair, claims);

    expect(group.rows).toHaveLength(1);
    const row = group.rows[0];
    expect(row.kind).toBe("contradiction");
    if (row.kind !== "contradiction") throw new Error("expected contradiction");
    expect(row.hypothesisIds.sort()).toEqual(["h-a", "h-b"]);
    expect(row.claims.map((c) => c.id).sort()).toEqual(["h-a", "h-b"]);
    expect(row.decisions).toHaveLength(2);
    // Still two acts for counting purposes; only the presentation collapses.
    expect(group.decisionCount).toBe(2);
    expect(group.hasContradiction).toBe(true);
  });

  it("pairs on the structured targets, not on the wording", () => {
    // Two separate contradictions in one iteration must not cross-pair.
    const first = contradictionPair(["h-a", "h-b"]);
    const second = contradictionPair(["h-c", "h-d"]);

    const [group] = groupDecisionsByIteration([first[0], second[0], first[1], second[1]]);

    const events = group.rows.filter((r) => r.kind === "contradiction");
    expect(events).toHaveLength(2);
    const pairs = events.map((e) =>
      e.kind === "contradiction" ? e.hypothesisIds.slice().sort().join("|") : "",
    );
    expect(pairs.sort()).toEqual(["h-a|h-b", "h-c|h-d"]);
  });

  it("leaves an unpaired contradiction decision as its own row", () => {
    const [lonely] = contradictionPair(["h-a", "h-b"]);

    const [group] = groupDecisionsByIteration([lonely]);

    expect(group.rows[0].kind).toBe("decision");
    expect(group.hasContradiction).toBe(false);
  });

  it("does not collapse runs recorded before targets were structured", () => {
    // Older runs carry the rationale but no targets; two rows is then the honest rendering.
    const legacy = [
      decision({
        decision_type: "revise_confidence",
        rationale: "weakened: cannot hold at the same time as something",
        iteration: 1,
      }),
      decision({
        decision_type: "revise_confidence",
        rationale: "weakened: cannot hold at the same time as something else",
        iteration: 1,
      }),
    ];

    const [group] = groupDecisionsByIteration(legacy);

    expect(group.rows).toHaveLength(2);
    expect(group.rows.every((r) => r.kind === "decision")).toBe(true);
  });

  it("does not treat an ordinary confidence revision as a contradiction", () => {
    const ordinary = decision({
      decision_type: "revise_confidence",
      rationale: "supported (support=6, refute=0)",
      targets: [{ kind: "hypothesis", id: "h-a" }],
    });

    const [group] = groupDecisionsByIteration([ordinary]);

    expect(group.rows[0].kind).toBe("decision");
  });

  it("returns nothing for an empty trace rather than an empty iteration", () => {
    expect(groupDecisionsByIteration([])).toEqual([]);
  });
});

// ------------------------------------------------------------------ evidence

function evidence(id: string, experimentId: string | null, hypothesisIds: string[] = []): EvidenceItem {
  return {
    id,
    claim: `claim ${id}`,
    evidence_type: "descriptive_stat",
    direction: "supports",
    strength: 0.6,
    reliability: 0.76,
    coverage: 1,
    experiment_result_id: experimentId,
    hypothesis_ids: hypothesisIds,
    statistics: null,
  };
}

function experiment(id: string, tool: string): ExperimentItem {
  return {
    id,
    tool_name: tool,
    status: "succeeded",
    summary: null,
    metrics: null,
    error: null,
    request_domain_id: null,
    target_hypothesis_ids: [],
    created_at: "2026-08-20T19:02:26Z",
    artifacts: [],
  };
}

describe("groupEvidenceByClaim", () => {
  it("files each item under the claim it bears on", () => {
    const claims = [hypothesis("h-a"), hypothesis("h-b")];
    const groups = groupEvidenceByClaim(
      [evidence("e1", null, ["h-a"]), evidence("e2", null, ["h-b"]), evidence("e3", null, ["h-a"])],
      claims,
    );

    expect(groups.map((g) => g.claim?.id)).toEqual(["h-a", "h-b"]);
    expect(groups[0].items.map((e) => e.id)).toEqual(["e1", "e3"]);
  });

  it("separates what supports a claim from what argues against it", () => {
    const groups = groupEvidenceByClaim(
      [
        evidence("e1", null, ["h-a"]),
        { ...evidence("e2", null, ["h-a"]), direction: "refutes" },
      ],
      [hypothesis("h-a")],
    );

    expect(groups[0].supporting.map((e) => e.id)).toEqual(["e1"]);
    expect(groups[0].refuting.map((e) => e.id)).toEqual(["e2"]);
    expect(groups[0].items).toHaveLength(2);
  });

  it("lists an item under every claim it bears on", () => {
    // It genuinely is evidence for both; filing it under the first would misrepresent the second.
    const groups = groupEvidenceByClaim(
      [evidence("shared", null, ["h-a", "h-b"])],
      [hypothesis("h-a"), hypothesis("h-b")],
    );

    expect(groups).toHaveLength(2);
    expect(groups.every((g) => g.items[0].id === "shared")).toBe(true);
  });

  it("keeps evidence that bears on no claim, in its own group, last", () => {
    const groups = groupEvidenceByClaim(
      [evidence("orphan", null, []), evidence("e1", null, ["h-a"])],
      [hypothesis("h-a")],
    );

    expect(groups).toHaveLength(2);
    expect(groups[1].claim).toBeNull();
    expect(groups[1].items.map((e) => e.id)).toEqual(["orphan"]);
  });

  it("treats an unknown hypothesis id as unlinked rather than dropping the row", () => {
    // Dropping would quietly shrink the evidence count the rest of the page reports.
    const groups = groupEvidenceByClaim([evidence("e1", null, ["nope"])], [hypothesis("h-a")]);

    expect(groups).toHaveLength(1);
    expect(groups[0].claim).toBeNull();
  });

  it("omits a claim that nothing bears on", () => {
    const groups = groupEvidenceByClaim([evidence("e1", null, ["h-a"])], [
      hypothesis("h-a"),
      hypothesis("h-b"),
    ]);

    expect(groups.map((g) => g.claim?.id)).toEqual(["h-a"]);
  });
});

// ------------------------------------------------------------------ sections + labels

describe("traceSections", () => {
  it("counts each section and notes what a reader would want to know", () => {
    const sections = traceSections({
      decisions: [decision({ iteration: 0 }), decision({ iteration: 1 })],
      hypotheses: [hypothesis("h-a"), hypothesis("h-b")],
      evidence: [evidence("e1", null)],
      experiments: [{ ...experiment("x1", "t"), artifacts: [{ id: "a", name: "n" }] as never }],
      critiques: [
        { resolved: false } as never,
        { resolved: true } as never,
      ],
      open_questions: [{ id: "q1" }],
    });

    const by = Object.fromEntries(sections.map((s) => [s.id, s]));
    expect(by.decisions.count).toBe(2);
    expect(by.decisions.note).toBe("2 iterations");
    expect(by.hypotheses.note).toBe("all weakened");
    expect(by.critiques.note).toBe("1 unresolved");
    expect(by.experiments.note).toBe("1 artifacts");
  });

  it("stays quiet when there is nothing to note", () => {
    const sections = traceSections({
      decisions: [],
      hypotheses: [],
      evidence: [],
      experiments: [],
      critiques: [],
      open_questions: [],
    });

    // No hypotheses must not read as "all weakened".
    expect(sections.find((s) => s.id === "hypotheses")?.note).toBe("");
    expect(sections.find((s) => s.id === "critiques")?.note).toBe("");
  });
});

describe("decision labels", () => {
  it("gives each decision type a glyph and a readable label", () => {
    expect(decisionGlyph("propose_hypothesis")).toBe("◇");
    expect(decisionLabel("propose_hypothesis")).toBe("Propose hypothesis");
    expect(decisionLabel("revise_confidence")).toBe("Revise confidence");
  });

  it("falls back readably on a type it does not know", () => {
    expect(decisionGlyph("some_future_type")).toBe("·");
    expect(decisionLabel("some_future_type")).toBe("Some future type");
  });
});
