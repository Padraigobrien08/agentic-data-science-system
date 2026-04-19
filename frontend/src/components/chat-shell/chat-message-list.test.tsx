import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessageList } from "@/components/chat-shell/chat-message-list";
import type { ChatMessage } from "@/components/chat-shell/types";

describe("ChatMessageList", () => {
  it("renders a structured answer card for completed assistant replies", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-1",
        role: "assistant",
        content: "MSFT margin pressure looks cyclical rather than structural.",
        answerCard: {
          goalDisplay: "Assess whether margin pressure is temporary or structural for MSFT",
          narrativeAnswer: {
            mode: "full",
            thesis: "MSFT margin pressure looks cyclical rather than structural.",
            sections: [
              {
                heading: "What's happening",
                body: "Revenue growth deterioration appears in several recent quarters.",
              },
              {
                heading: "Why we think that",
                body: "The summarized evidence is directionally consistent.",
              },
            ],
            fallbackReason: null,
          },
          summaryLine: "MSFT margin pressure looks cyclical rather than structural.",
          orchestrationStatus: "success",
          emptyStateReason: null,
          conclusionRider: null,
          takeawayRows: [
            {
              text: "Revenue growth deterioration appears in several recent quarters.",
              chips: [{ label: "Evidence", href: "/projects/project-1/runs/run-1/trace#run-artifacts" }],
            },
          ],
          alignmentFindings: [
            {
              code: "CASHFLOW",
              severity: "warning",
              detail: "Cash-flow deterioration is weaker than the revenue signal.",
              chips: [{ label: "Critic", href: "/projects/project-1/runs/run-1/trace#run-agents" }],
            },
          ],
          overallConfidence: "medium",
          blockingCaveats: ["Peer coverage is limited for this run."],
          criticPhaseStatus: "success",
          reportPhaseStatus: "success",
          weakEvidenceSignals: ["insufficient_peers_rows"],
          contextSignals: [],
          evidenceLinks: [{ role: "report_md", artifactId: "report-1" }],
          extraArtifactCount: 1,
          reportArtifactId: "report-1",
          evidenceProvenanceHint: "Deep dive includes the full artifact inventory.",
          navigationItems: [
            { key: "report", label: "Report", href: "/artifacts/report-1" },
            { key: "evidence", label: "Evidence", href: "/projects/project-1/runs/run-1/trace#run-artifacts" },
            { key: "artifacts", label: "Artifacts", href: "/projects/project-1/runs/run-1/trace#run-artifacts" },
            { key: "critic", label: "Critic", href: "/projects/project-1/runs/run-1/trace#run-agents" },
            { key: "trace", label: "Trace", href: "/projects/project-1/runs/run-1/trace" },
          ],
          traceHref: "/projects/project-1/runs/run-1/trace",
          caveatOverflowHref: "/projects/project-1/runs/run-1/trace#run-context-transparency",
        },
        runId: "run-1",
        runHref: "/projects/project-1/runs/run-1/trace",
        runStatus: "success",
        runCreatedAt: "2026-04-18T19:58:00Z",
        runFinishedAt: "2026-04-18T20:00:00Z",
        deliveryMode: "sync_only",
        deliveryDetail: "Background delivery was rerouted to immediate execution for this chat request.",
        reroutedFromBackground: true,
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(
      screen.getByText("Background delivery was rerouted to immediate execution for this chat request."),
    ).toBeTruthy();
    expect(screen.getByText("Answer")).toBeTruthy();
    expect(screen.getByText("What's happening")).toBeTruthy();
    expect(screen.getByText("Why we think that")).toBeTruthy();
    expect(screen.getByText("Findings")).toBeTruthy();
    expect(screen.getByText("Confidence")).toBeTruthy();
    expect(screen.getAllByText("Evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("MSFT margin pressure looks cyclical rather than structural.")).toBeTruthy();
    expect(screen.getByText("Revenue growth deterioration appears in several recent quarters.")).toBeTruthy();
    expect(screen.getByText("Cash-flow deterioration is weaker than the revenue signal.")).toBeTruthy();
    expect(screen.getByText("Evidence strength:")).toBeTruthy();
    expect(screen.getByText("Peer coverage is limited for this run.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Report" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Evidence" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Artifacts" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Critic" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Trace" })).toBeTruthy();
    const exactJumpLinks = screen.getAllByRole("link", { name: "Open source" });
    expect(exactJumpLinks.length).toBeGreaterThanOrEqual(2);
    expect(exactJumpLinks[0]?.getAttribute("href")).toBe("/projects/project-1/runs/run-1/trace#run-artifacts");
    expect(screen.queryByRole("link", { name: "Run answer" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Deep dive" })).toBeNull();
    expect(screen.queryByRole("link", { name: "All runs" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Open trace" })).toBeNull();
  });

  it("renders the structured pending footprint while analysis is running", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-pending",
        role: "assistant",
        content: "Running analysis...",
        pending: true,
        deliveryMode: "sync_only",
        deliveryDetail: "Workspace chat is executing synchronously right now.",
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("Running analysis...")).toBeTruthy();
    expect(screen.getByText("Updating…")).toBeTruthy();
  });

  it("renders rewriteSuggestions inline without run links for unsupported routing replies", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-unsupported",
        role: "assistant",
        content: "I couldn't route that request yet.",
        routingReason: "Requested tickers fall outside the current workspace scope.",
        rewriteSuggestions: [
          "Assess whether margin pressure is temporary or structural for MSFT.",
          "Compare AAPL versus MSFT on operating margin over the last eight quarters.",
        ],
        createdAt: "2026-04-18T20:05:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("Requested tickers fall outside the current workspace scope.")).toBeTruthy();
    expect(
      screen.getByText("Assess whether margin pressure is temporary or structural for MSFT."),
    ).toBeTruthy();
    expect(
      screen.getByText("Compare AAPL versus MSFT on operating margin over the last eight quarters."),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Open trace" })).toBeNull();
    expect(screen.queryByText("Answer")).toBeNull();
    expect(screen.queryByText("Goal")).toBeNull();
  });
});
