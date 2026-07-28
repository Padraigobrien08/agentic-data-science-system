import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell/chat-shell";
import type { ChatMessage, ChatThreadSummary } from "@/components/chat-shell/types";

vi.mock("@/actions/projects", () => ({
  updateWorkspaceScopeAction: async () => ({}),
}));

vi.mock("@/actions/conversations", () => ({
  deleteConversationAction: async () => undefined,
  startNewConversationAction: async () => undefined,
}));

vi.mock("@/actions/runs", () => ({
  createAnalysisRunFromChat: async () => ({}),
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
    expect(screen.getAllByText("Running analysis...")).toHaveLength(1);
    expect(screen.getAllByText("This chat is executing synchronously right now.")).toHaveLength(1);
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
});
