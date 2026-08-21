import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DemoTranscript } from "@/components/demos/demo-transcript";
import type { InvestigationDetail } from "@/lib/api/types";
import type { DemoCapture } from "@/lib/demo-static/capture-types";

function detail(over: Partial<InvestigationDetail> = {}): InvestigationDetail {
  return {
    id: "inv-1",
    domain_id: "inv-1",
    analysis_run_id: "run-1",
    project_id: null,
    origin: "native",
    status: "exhausted",
    confidence: 0.4,
    objective: "Delivery times have worsened. Is quality degrading, or is it volume?",
    adapter_id: "in_memory",
    conclusion: "Mixed evidence.",
    demo_slug: "a-demo",
    counts: {
      hypotheses: 1, evidence: 2, experiments: 1,
      observations: 0, decisions: 4, critiques: 0, open_questions: 0,
    },
    outcome: {
      kind: "declined",
      termination_reason: "insufficient_evidence",
      claims_supported: 0, claims_rejected: 0, claims_weakened: 1, claims_unresolved: 0,
      contradiction_found: false,
    },
    created_at: "2026-08-20T19:02:18Z",
    updated_at: "2026-08-20T19:02:30Z",
    success_criteria: [],
    constraints: [],
    termination: null,
    hypotheses: [],
    evidence: [],
    experiments: [],
    observations: [],
    decisions: [],
    critiques: [],
    open_questions: [],
    conclusion_detail: null,
    datasets: [],
    events: [],
    ...over,
  };
}

function capture(userText: string): DemoCapture {
  return {
    demo_slug: "a-demo",
    investigation_id: "inv-1",
    analysis_run_id: "run-1",
    totals: {
      model_calls: 1, prompt_tokens: 1, completion_tokens: 1,
      total_tokens: 2, latency_ms: 10, est_cost_usd: 0.001, priced: true,
    },
    model_calls: [],
    chat: [
      {
        id: "c1",
        title: "t",
        created_at: "2026-08-20T19:02:18Z",
        messages: [
          {
            sequence: 0, id: "m1", role: "user", status: "complete",
            content: userText, analysis_run_id: null, created_at: "2026-08-20T19:02:18Z",
          },
        ],
      },
    ],
  };
}

describe("DemoTranscript", () => {
  it("shows the question that was actually asked", () => {
    render(<DemoTranscript detail={detail()} capture={capture("Why did delivery slow down?")} />);

    expect(screen.getByText("Why did delivery slow down?")).toBeTruthy();
    expect(screen.getByText("asked")).toBeTruthy();
  });

  it("falls back to the objective, labelled as a goal, when no turn was recorded", () => {
    // Two published runs predate `--chat`. Presenting their objective as a chat message would
    // put words in a user's mouth that nobody typed.
    render(<DemoTranscript detail={detail()} capture={null} />);

    expect(
      screen.getByText("Delivery times have worsened. Is quality degrading, or is it volume?"),
    ).toBeTruthy();
    expect(screen.getByText(/predates recorded chat turns/)).toBeTruthy();
    expect(screen.queryByText("asked")).toBeNull();
  });

  it("states the outcome and the run's own counts", () => {
    render(<DemoTranscript detail={detail()} capture={null} />);

    expect(screen.getByText("Declined to answer")).toBeTruthy();
    expect(screen.getByText(/4 decisions, 1 experiment, 2 evidence items/)).toBeTruthy();
  });

  it("renders a run with no claims or open questions without empty scaffolding", () => {
    render(<DemoTranscript detail={detail()} capture={null} />);

    expect(screen.queryByText(/Left open on purpose/i)).toBeNull();
  });
});
