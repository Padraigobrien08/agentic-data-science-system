import { describe, expect, it } from "vitest";

import type { DecisionItem, HypothesisItem, RunStepDetail } from "@/lib/api/types";
import { investigationTimeline, runTimeline } from "@/lib/trace-timeline";

/**
 * Two sources, one shape. These pin the parts that carry meaning — ordering, grouping, and
 * the contradiction staying one event — rather than the wording of any label.
 */
const decision = (over: Partial<DecisionItem>): DecisionItem =>
  ({
    id: "d1",
    sequence: 0,
    iteration: 0,
    decision_type: "propose_hypothesis",
    rationale: "because",
    chosen_option: null,
    targets: [],
    ...over,
  }) as DecisionItem;

const step = (over: Partial<RunStepDetail>): RunStepDetail =>
  ({
    id: "s1",
    analysis_run_id: "run-1",
    step_index: 0,
    status: "success",
    label: null,
    planned_tool_name: null,
    detail: null,
    started_at: null,
    finished_at: null,
    created_at: "2026-08-20T19:02:18Z",
    updated_at: "2026-08-20T19:02:18Z",
    planner_tool_input_json: null,
    meta_json: null,
    ...over,
  }) as RunStepDetail;

describe("investigationTimeline", () => {
  it("groups decisions under the iteration that made them, in order", () => {
    const groups = investigationTimeline([
      decision({ id: "b", sequence: 1, iteration: 1 }),
      decision({ id: "a", sequence: 0, iteration: 0 }),
    ]);

    expect(groups.map((g) => g.label)).toEqual(["iter 0", "iter 1"]);
    expect(groups[0].entries[0].id).toBe("a");
  });

  it("carries the chosen tool as the accent and the rationale as the detail", () => {
    const groups = investigationTimeline([
      decision({
        decision_type: "select_experiment",
        chosen_option: "analyze_correlation",
        rationale: "highest information gain",
      }),
    ]);

    expect(groups[0].entries[0]).toMatchObject({
      accent: "analyze_correlation",
      detail: "highest information gain",
    });
  });

  it("keeps a contradiction as one event carrying both claims", () => {
    const targets = [{ id: "h-a" }, { id: "h-b" }] as DecisionItem["targets"];
    const pair = [
      decision({
        id: "c1",
        sequence: 0,
        decision_type: "revise_confidence",
        rationale: "they cannot hold at the same time as each other",
        targets,
      }),
      decision({
        id: "c2",
        sequence: 1,
        decision_type: "revise_confidence",
        rationale: "they cannot hold at the same time as each other",
        targets,
      }),
    ];
    const claims = [
      { id: "h-a", statement: "staffing drives it", status: "weakened", confidence: 0.5 },
      { id: "h-b", statement: "volume drives it", status: "weakened", confidence: 0.5 },
    ] as HypothesisItem[];

    const groups = investigationTimeline(pair, claims);

    expect(groups[0].entries).toHaveLength(1);
    expect(groups[0].meta).toContain("contradiction");
    expect(groups[0].entries[0].callout?.items?.map((i) => i.text)).toEqual([
      "staffing drives it",
      "volume drives it",
    ]);
    // Where each claim landed — never a before/after arrow, which the data cannot support.
    expect(groups[0].entries[0].callout?.items?.[0].meta).toBe("weakened · 50%");
  });
});

describe("runTimeline", () => {
  it("orders steps by index regardless of the order they arrive in", () => {
    const groups = runTimeline([
      step({ id: "s2", step_index: 1, label: "second" }),
      step({ id: "s1", step_index: 0, label: "first" }),
    ]);

    expect(groups[0].entries.map((e) => e.label)).toEqual(["first", "second"]);
  });

  it("splits at the point a run stopped succeeding — the row a reader is looking for", () => {
    const groups = runTimeline([
      step({ id: "a", step_index: 0, label: "plan" }),
      step({ id: "b", step_index: 1, label: "compute" }),
      step({ id: "c", step_index: 2, label: "report", status: "error" }),
    ]);

    expect(groups).toHaveLength(2);
    expect(groups[0].label).toBe("steps 1–2");
    expect(groups[1].label).toBe("step 3");
    expect(groups[1].entries[0].tone).toBe("danger");
  });

  it("is a single group when nothing went wrong", () => {
    const groups = runTimeline([
      step({ id: "a", step_index: 0 }),
      step({ id: "b", step_index: 1 }),
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0].meta).toBe("2 steps");
  });

  it("names an unlabelled step by its position rather than rendering blank", () => {
    expect(runTimeline([step({ step_index: 4, label: "   " })])[0].entries[0].label).toBe("Step 5");
  });

  it("has nothing to draw for a run with no steps", () => {
    expect(runTimeline([])).toEqual([]);
  });
});
