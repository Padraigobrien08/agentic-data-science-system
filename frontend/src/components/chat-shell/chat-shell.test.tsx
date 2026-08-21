import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell/chat-shell";
import type { ChatMessage, ChatThreadSummary } from "@/components/chat-shell/types";

// The command palette navigates between chats via the app router, which is not
// mounted in jsdom.
const routerPushMock = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPushMock, replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("@/actions/projects", () => ({
  updateWorkspaceScopeAction: async () => ({}),
}));

vi.mock("@/actions/conversations", () => ({
  deleteConversationAction: async () => undefined,
  startNewConversationAction: async () => undefined,
}));

vi.mock("@/actions/auth", () => ({
  logoutAction: async () => undefined,
}));

vi.mock("@/actions/runs", () => ({
  // Never resolve so the send flow stays in its live-progress state during assertions.
  startAnalysisRun: () => new Promise(() => {}),
  finalizeAnalysisRun: () => new Promise(() => {}),
  getRunProgress: () => new Promise(() => {}),
}));

describe("ChatShell", () => {
  beforeEach(() => {
    HTMLFormElement.prototype.requestSubmit = vi.fn();
  });

  it("renders hydrated history and appends new prompts to the same visible thread", () => {
    const initialMessages: ChatMessage[] = [
      {
        id: "user-run-1",
        role: "user",
        content: "Assess whether margin pressure is temporary or structural for MSFT",
        createdAt: "2026-04-18T19:58:00Z",
      },
      {
        id: "assist-run-1",
        role: "assistant",
        content: "MSFT margin pressure looks cyclical rather than structural.",
        answerCard: {
          goalDisplay: "Assess whether margin pressure is temporary or structural for MSFT",
          narrativeAnswer: {
            mode: "legacy",
            thesis: "MSFT margin pressure looks cyclical rather than structural.",
            sections: [],
            fallbackReason: "legacy_summary",
          },
          summaryLine: "MSFT margin pressure looks cyclical rather than structural.",
          orchestrationStatus: "success",
          emptyStateReason: null,
          conclusionRider: null,
          takeawayRows: [],
          alignmentFindings: [],
          supplementalEvidence: [],
          supplementalEvidenceState: {
            mode: "empty",
            closedLabel: "Show supporting evidence",
            openLabel: "Hide supporting evidence",
            heading: "No mapped support is available",
            body: "Artifacts or mapped support were not available for this answer view.",
          },
          overallConfidence: null,
          confidenceExplainer: {
            label: "Not rated",
            tone: "neutral",
            supports: [],
            weakens: [],
            limits: [],
          },
          blockingCaveats: [],
          criticPhaseStatus: null,
          reportPhaseStatus: null,
          inlineCharts: [
            {
              chartId: "trend-msft-margin",
              kind: "line",
              metricKey: "operating_margin",
              metricLabel: "Operating margin",
              caption:
                "Operating margin compressed in the latest quarters, which supports the cyclical pressure call.",
              xAxisLabel: "Quarter",
              yAxisLabel: "Operating margin",
              valueFormat: "percent",
              series: [{ key: "focal", label: "MSFT", colorToken: "chart-1" }],
              rows: [
                { xValue: "2025-Q3", values: { focal: 0.41 } },
                { xValue: "2025-Q4", values: { focal: 0.38 } },
              ],
              markers: [{ xValue: "2025-Q4", label: "Shift" }],
            },
          ],
          inlineChartNotice: null,
          weakEvidenceSignals: [],
          contextSignals: [],
          evidenceLinks: [],
          extraArtifactCount: 0,
          reportArtifactId: null,
          evidenceProvenanceHint: null,
          navigationItems: [{ key: "trace", label: "Trace", href: "/projects/project-1/runs/run-1/trace" }],
          traceHref: "/projects/project-1/runs/run-1/trace",
          caveatOverflowHref: "/projects/project-1/runs/run-1/trace#run-context-transparency",
        },
        runId: "run-1",
        runHref: "/projects/project-1/runs/run-1/trace",
        runStatus: "success",
        runCreatedAt: "2026-04-18T19:58:00Z",
        runFinishedAt: "2026-04-18T20:00:00Z",
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];
    const chatThreads: ChatThreadSummary[] = [
      {
        id: "project-1",
        title: "Assess whether margin pressure is temporary or structural for MSFT",
        href: "/projects/project-1/chat",
        hasMessages: true,
        updatedAt: "2026-04-18T20:00:00Z",
      },
    ];

    render(
      <ChatShell
        projectId="project-1"
        conversationId="conv-1"
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
          background_available: false,
          detail: "This chat is executing synchronously right now.",
        }}
        initialMessages={initialMessages}
        chatThreads={chatThreads}
      />,
    );

    expect(screen.getAllByText("Assess whether margin pressure is temporary or structural for MSFT").length).toBe(
      2,
    );
    expect(screen.getAllByText("MSFT margin pressure looks cyclical rather than structural.")).toHaveLength(1);

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, {
      target: { value: "Detect unusual financial changes for MSFT" },
    });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(screen.getAllByText("Detect unusual financial changes for MSFT")).toHaveLength(1);
    expect(screen.getByText("Starting analysis…")).toBeTruthy();
    expect(screen.getByText("Understanding goal & plan")).toBeTruthy();
    expect(screen.getByText("Visual evidence")).toBeTruthy();
    expect(screen.getByText("Show supporting evidence")).toBeTruthy();
    expect(screen.getByRole("button", { name: "New chat" })).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: "Delete Assess whether margin pressure is temporary or structural for MSFT",
      }),
    ).toBeTruthy();
    expect(screen.getAllByText("History").length).toBeGreaterThan(0);
    expect(screen.queryByText("Home")).toBeNull();
    expect(screen.queryByText("Workspace")).toBeNull();
    expect(screen.queryByText("Recent analyses")).toBeNull();
    const visualEvidence = screen.getByText("Visual evidence");
    const supportingEvidence = screen.getByText("Show supporting evidence");
    expect(
      visualEvidence.compareDocumentPosition(supportingEvidence) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("renders the Phase 17 error shell for failed assistant answers", () => {
    const initialMessages: ChatMessage[] = [
      {
        id: "assist-run-error",
        role: "assistant",
        content: "Run failed",
        answerCard: {
          goalDisplay: "Is MSFT showing persistent deterioration?",
          narrativeAnswer: {
            mode: "legacy",
            thesis: "Run failed",
            sections: [],
            fallbackReason: "legacy_summary",
          },
          summaryLine: "Run failed",
          orchestrationStatus: "error",
          emptyStateReason: "The pipeline encountered an execution failure.",
          conclusionRider: null,
          takeawayRows: [],
          alignmentFindings: [],
          supplementalEvidence: [],
          supplementalEvidenceState: {
            mode: "empty",
            closedLabel: "Show supporting evidence",
            openLabel: "Hide supporting evidence",
            heading: "No mapped support is available",
            body: "Artifacts or mapped support were not available for this answer view.",
          },
          overallConfidence: null,
          confidenceExplainer: {
            label: "Not rated",
            tone: "neutral",
            supports: [],
            weakens: [],
            limits: [],
          },
          blockingCaveats: [],
          criticPhaseStatus: null,
          reportPhaseStatus: null,
          inlineCharts: [],
          inlineChartNotice: null,
          weakEvidenceSignals: [],
          contextSignals: [],
          evidenceLinks: [],
          extraArtifactCount: 0,
          reportArtifactId: null,
          evidenceProvenanceHint: null,
          navigationItems: [{ key: "trace", label: "Trace", href: "/projects/project-1/runs/run-error/trace" }],
          traceHref: "/projects/project-1/runs/run-error/trace",
          caveatOverflowHref: null,
        },
        runId: "run-error",
        runHref: "/projects/project-1/runs/run-error/trace",
        runStatus: "error",
        runCreatedAt: "2026-04-18T20:40:00Z",
        runFinishedAt: "2026-04-18T20:41:00Z",
        createdAt: "2026-04-18T20:41:00Z",
      },
    ];

    render(
      <ChatShell
        projectId="project-1"
        conversationId="conv-1"
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
          background_available: false,
          detail: "This chat is executing synchronously right now.",
        }}
        initialMessages={initialMessages}
        chatThreads={[]}
      />,
    );

    expect(screen.getByText("This analysis didn’t finish cleanly.")).toBeTruthy();
    expect(
      screen.getByText("Open trace to inspect what failed, then retry with narrower wording or refreshed SEC data."),
    ).toBeTruthy();
  });

  describe("read-only (replay tier)", () => {
    const recorded: ChatMessage[] = [
      {
        id: "demo-user-inv-1",
        role: "user",
        content: "Does staffing or volume drive service times?",
        createdAt: "2026-08-20T19:02:18Z",
      },
      {
        id: "demo-assistant-inv-1",
        role: "assistant",
        content: "Two claims could not both be true, so neither was allowed to stand.",
        recordedAnswer: {
          headline: "Two claims could not both be true, so neither was allowed to stand.",
          conclusion: null,
          claims: [{ id: "h-a", statement: "staffing drives it", status: "weakened", confidence: 0.5 }],
          openQuestions: ["which of the two holds?"],
          footnote: "15 decisions, 3 experiments, 13 evidence items.",
        },
        createdAt: "2026-08-20T19:02:30Z",
      },
    ];
    const threads: ChatThreadSummary[] = [
      {
        id: "a-demo",
        title: "Does staffing or volume drive service times?",
        href: "/demos/a-demo",
        hasMessages: true,
        updatedAt: "2026-08-20T19:02:30Z",
      },
    ];

    function renderReplay() {
      render(
        <ChatShell
          readOnly
          conversationId="a-demo"
          initialMessages={recorded}
          chatThreads={threads}
          header={<header>recorded · declined</header>}
          rail={<aside>The trace</aside>}
        />,
      );
    }

    // Every one of these controls would reach a backend that is not there on the replay
    // tier. Absent, not disabled — a demo that offers a composer and then fails is worse
    // than one that never offered.
    it("renders no affordance that would need a backend", () => {
      renderReplay();

      expect(screen.queryByLabelText("Message input")).toBeNull();
      expect(screen.queryByRole("button", { name: "New chat" })).toBeNull();
      expect(
        screen.queryByRole("button", { name: "Delete Does staffing or volume drive service times?" }),
      ).toBeNull();
      expect(screen.queryByRole("button", { name: "Sign out" })).toBeNull();
      expect(screen.queryByText("Edit scope")).toBeNull();
      expect(screen.queryByLabelText(/Open command palette/)).toBeNull();
      expect(screen.queryByText("Scope")).toBeNull();
    });

    it("shows the recorded answer, the supplied header, and the docked trace", () => {
      renderReplay();

      expect(screen.getByText("recorded · declined")).toBeTruthy();
      // Twice: the question in the transcript, and the run's row in the sidebar.
      expect(screen.getAllByText("Does staffing or volume drive service times?")).toHaveLength(2);
      expect(
        screen.getByText("Two claims could not both be true, so neither was allowed to stand."),
      ).toBeTruthy();
      expect(screen.getByText("staffing drives it")).toBeTruthy();
      expect(screen.getByText("which of the two holds?")).toBeTruthy();
      expect(screen.getByText("15 decisions, 3 experiments, 13 evidence items.")).toBeTruthy();
      expect(screen.getByText("The trace")).toBeTruthy();
    });

    it("keeps the sidebar as the run switcher, named for what it lists", () => {
      renderReplay();

      expect(screen.getAllByText("Recorded runs").length).toBeGreaterThan(0);
      expect(screen.queryByText("History")).toBeNull();
      expect(screen.getByRole("link", { name: /Does staffing or volume drive service times/ })).toBeTruthy();
    });

    it("leaves the command palette shortcut inert", () => {
      renderReplay();

      fireEvent.keyDown(window, { key: "k", metaKey: true });

      expect(screen.queryByPlaceholderText(/Search/i)).toBeNull();
    });
  });
});
