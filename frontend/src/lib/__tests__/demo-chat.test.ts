import { describe, expect, it } from "vitest";

import type { InvestigationDetail, InvestigationSummary } from "@/lib/api/types";
import type { ChatThreadSummary } from "@/components/chat-shell/types";
import { demoMessages, demoThreads, mergedThreads, recordedQuestion } from "@/lib/demo-chat";
import type { DemoChatThread } from "@/lib/demo-static/capture-types";

function detail(over: Partial<InvestigationDetail> = {}): InvestigationDetail {
  return {
    id: "inv-1",
    domain_id: "inv-1",
    analysis_run_id: "run-1",
    project_id: null,
    origin: "native",
    dataset_origin: "synthetic",
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

function capture(messages: Array<{ role: string; content: string | null }>): DemoChatThread[] {
  return [
    {
      id: "c1",
      title: "t",
      created_at: "2026-08-20T19:02:18Z",
      messages: messages.map((m, i) => ({
        sequence: i,
        id: `m${i}`,
        role: m.role,
        status: "complete",
        content: m.content,
        analysis_run_id: null,
        created_at: "2026-08-20T19:02:18Z",
      })),
    },
  ];
}

describe("recordedQuestion", () => {
  it("returns the first user turn that was actually recorded", () => {
    const found = recordedQuestion(
      capture([
        { role: "assistant", content: "preamble" },
        { role: "user", content: "Why did delivery slow down?" },
      ]),
    );

    expect(found).toBe("Why did delivery slow down?");
  });

  it("treats an empty or missing turn as no question at all", () => {
    expect(recordedQuestion(capture([{ role: "user", content: "   " }]))).toBeNull();
    expect(recordedQuestion(capture([{ role: "user", content: null }]))).toBeNull();
    expect(recordedQuestion(null)).toBeNull();
  });
});

describe("demoMessages", () => {
  it("opens with the question the run was asked", () => {
    const messages = demoMessages(
      detail(),
      capture([{ role: "user", content: "Why did delivery slow down?" }]),
    );

    expect(messages[0]).toMatchObject({
      role: "user",
      content: "Why did delivery slow down?",
    });
  });

  it("never promotes the objective into a user turn nobody typed", () => {
    // Two published runs predate `record_demo.py --chat`. Their goal is stated as a system
    // note, so the transcript cannot be read as a conversation that did not happen.
    const messages = demoMessages(detail(), null);

    expect(messages.some((m) => m.role === "user")).toBe(false);
    expect(messages[0]).toMatchObject({ role: "system" });
    expect(messages[0].content).toContain("Recorded before chat turns were captured");
    expect(messages[0].content).toContain(
      "Delivery times have worsened. Is quality degrading, or is it volume?",
    );
  });

  it("answers with the composed view of the run, not prose", () => {
    const messages = demoMessages(detail(), null);
    const answer = messages.at(-1);

    expect(answer?.role).toBe("assistant");
    expect(answer).toMatchObject({
      recordedAnswer: { footnote: "4 decisions, 1 experiment, 2 evidence items." },
    });
    // No live run behind a recording, so nothing may claim there is one.
    expect(answer).not.toHaveProperty("answerCard");
    expect(answer).not.toHaveProperty("runId");
  });
});

describe("demoThreads", () => {
  const summary = (slug: string | null, objective: string | null): InvestigationSummary =>
    ({ ...detail(), demo_slug: slug, objective }) as InvestigationSummary;

  it("turns the published set into the sidebar's run switcher", () => {
    expect(demoThreads([summary("a-demo", "Does staffing drive service?")])).toEqual([
      {
        id: "a-demo",
        title: "Does staffing drive service?",
        href: "/demos/a-demo",
        hasMessages: true,
        updatedAt: "2026-08-20T19:02:30Z",
        recorded: true,
      },
    ]);
  });

  it("drops anything unpublished rather than linking to a 404", () => {
    expect(demoThreads([summary(null, "not published")])).toEqual([]);
  });

  it("names a run with no objective instead of rendering a blank row", () => {
    expect(demoThreads([summary("a-demo", null)])[0].title).toBe("Recorded investigation");
  });
});

describe("mergedThreads", () => {
  const own = (id: string, updatedAt: string): ChatThreadSummary => ({
    id,
    title: id,
    href: `/projects/p/chat/${id}`,
    hasMessages: true,
    updatedAt,
  });
  const demo = (slug: string, updatedAt: string): InvestigationSummary =>
    ({ ...detail(), demo_slug: slug, objective: slug, updated_at: updatedAt }) as InvestigationSummary;

  it("interleaves recorded runs with the reader's own chats, newest first", () => {
    const merged = mergedThreads(
      [own("mine-old", "2026-08-01T00:00:00Z"), own("mine-new", "2026-08-30T00:00:00Z")],
      [demo("recorded", "2026-08-15T00:00:00Z")],
    );

    expect(merged.map((t) => t.id)).toEqual(["mine-new", "recorded", "mine-old"]);
  });

  it("marks only the published runs, so the reader can tell them apart", () => {
    const merged = mergedThreads([own("mine", "2026-08-01T00:00:00Z")], [demo("rec", "2026-08-02T00:00:00Z")]);

    expect(merged.find((t) => t.id === "rec")?.recorded).toBe(true);
    expect(merged.find((t) => t.id === "mine")?.recorded).toBeUndefined();
  });

  it("is just the reader's own chats when nothing is published", () => {
    expect(mergedThreads([own("mine", "2026-08-01T00:00:00Z")], [])).toHaveLength(1);
  });
});

describe("demoNote", () => {
  it("describes the unanswerable run as it actually ran", async () => {
    const { demoNote } = await import("@/lib/demo-notes");
    const note = demoNote("csv-unanswerable-moat");

    expect(note).not.toBeNull();
    expect(note!.body).toMatch(/cannot be answered/i);
    expect(note!.label).toBe("unanswerable");
    // The framing must not claim the documented failure occurred. It was recorded to
    // trigger a substituted metric at 0.95 and did the opposite every time, so saying so
    // would be a false statement about the run sitting directly above the run.
    expect(note!.body).not.toMatch(/substituted the nearest/i);
    expect(note!.body).toMatch(/did not reproduce/i);
  });

  it("leaves an ordinary run unframed", async () => {
    const { demoNote } = await import("@/lib/demo-notes");

    expect(demoNote("csv-staffing-vs-service")).toBeNull();
  });
});
