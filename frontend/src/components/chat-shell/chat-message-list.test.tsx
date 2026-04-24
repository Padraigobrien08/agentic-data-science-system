import { fireEvent, render, screen } from "@testing-library/react";
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
              {
                heading: "What weakens the claim",
                body: "Peer validation remains limited across the available evidence.",
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
          supplementalEvidence: [
            {
              id: "support-1",
              title: "Revenue growth deterioration appears",
              reason: "Revenue growth deterioration appears in several recent quarters.",
              jump: { label: "Open source", href: "/projects/project-1/runs/run-1/trace#run-artifacts" },
              source: "takeaway",
            },
            {
              id: "support-2",
              title: "Cash-flow deterioration is weaker",
              reason: "Cash-flow deterioration is weaker than the revenue signal.",
              jump: { label: "Open source", href: "/projects/project-1/runs/run-1/trace#run-agents" },
              source: "alignment",
            },
          ],
          supplementalEvidenceState: {
            mode: "available",
            closedLabel: "Show supporting evidence",
            openLabel: "Hide supporting evidence",
            heading: null,
            body: null,
          },
          overallConfidence: "medium",
          confidenceExplainer: {
            label: "Medium",
            tone: "medium",
            supports: ["Revenue growth deterioration appears in several recent quarters."],
            weakens: ["Peer coverage is limited for this run."],
            limits: [],
          },
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
    expect(screen.getByText("What weakens the claim")).toBeTruthy();
    expect(screen.getByText("Show supporting evidence")).toBeTruthy();
    expect(screen.getAllByText("Evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("MSFT margin pressure looks cyclical rather than structural.")).toBeTruthy();
    expect(screen.getByText("The summarized evidence is directionally consistent.")).toBeTruthy();
    expect(screen.getByText("Peer validation remains limited across the available evidence.")).toBeTruthy();
    expect(screen.getByText("Evidence strength:")).toBeTruthy();
    expect(screen.getByText("Medium")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Report" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Evidence" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Artifacts" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Critic" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Trace" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Open source" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Run answer" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Deep dive" })).toBeNull();
    expect(screen.queryByRole("link", { name: "All runs" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Open trace" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Show supporting evidence" }));

    expect(screen.getByText("Hide supporting evidence")).toBeTruthy();
    expect(screen.getByText("Cash-flow deterioration is weaker than the revenue signal.")).toBeTruthy();
    const expandedJumpLinks = screen.getAllByRole("link", { name: "Open source" });
    expect(expandedJumpLinks.length).toBeGreaterThanOrEqual(2);
    expect(expandedJumpLinks[0]?.getAttribute("href")).toBe("/projects/project-1/runs/run-1/trace#run-artifacts");
  });

  it("keeps the narrative sections ordered in one centered column without the old right rail", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-ordered",
        role: "assistant",
        content: "MSFT shows a cautious deterioration pattern.",
        answerCard: {
          goalDisplay: "Is MSFT showing persistent deterioration?",
          narrativeAnswer: {
            mode: "full",
            thesis: "MSFT shows a cautious deterioration pattern.",
            sections: [
              {
                heading: "Why we think that",
                body: "The supporting rows consistently point in the same direction.",
              },
              {
                heading: "What weakens the claim",
                body: "Peer coverage is incomplete.",
              },
              {
                heading: "What's happening",
                body: "Revenue growth weakens across several recent periods.",
              },
            ],
            fallbackReason: null,
          },
          summaryLine: "MSFT shows a cautious deterioration pattern.",
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
          weakEvidenceSignals: [],
          contextSignals: [],
          evidenceLinks: [],
          extraArtifactCount: 0,
          reportArtifactId: null,
          evidenceProvenanceHint: null,
          navigationItems: [],
          traceHref: "/projects/project-1/runs/run-2/trace",
          caveatOverflowHref: null,
        },
        runId: "run-2",
        runHref: "/projects/project-1/runs/run-2/trace",
        runStatus: "success",
        runCreatedAt: "2026-04-18T20:10:00Z",
        runFinishedAt: "2026-04-18T20:12:00Z",
        createdAt: "2026-04-18T20:12:00Z",
      },
    ];

    const { container } = render(<ChatMessageList messages={messages} />);

    const whatsHappening = screen.getByText("What's happening");
    const whyWeThinkThat = screen.getByText("Why we think that");
    const whatWeakensTheClaim = screen.getByText("What weakens the claim");

    expect(whatsHappening.compareDocumentPosition(whyWeThinkThat) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      whyWeThinkThat.compareDocumentPosition(whatWeakensTheClaim) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(container.innerHTML).not.toContain("lg:grid-cols-[minmax(0,1.55fr)_minmax(18rem,0.95fr)]");
    expect(screen.getByText("Show supporting evidence")).toBeTruthy();
  });

  it("renders partial answers with explicit limitation language in the narrative shell", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-partial",
        role: "assistant",
        content: "The evidence is limited, but the loaded summaries still point to weaker revenue growth.",
        answerCard: {
          goalDisplay: "Is MSFT showing persistent deterioration?",
          narrativeAnswer: {
            mode: "partial",
            thesis: "The evidence is limited, but the loaded summaries still point to weaker revenue growth.",
            sections: [
              {
                heading: "What weakens the claim",
                body: "Peer validation is incomplete, so the conclusion is only partial.",
              },
            ],
            fallbackReason: "limited_evidence",
          },
          summaryLine: "The evidence is limited, but the loaded summaries still point to weaker revenue growth.",
          orchestrationStatus: "partial_success",
          emptyStateReason: null,
          conclusionRider: null,
          takeawayRows: [],
          alignmentFindings: [],
          supplementalEvidence: [],
          supplementalEvidenceState: {
            mode: "limited",
            closedLabel: "Show supporting evidence",
            openLabel: "Hide supporting evidence",
            heading: "Supporting evidence is limited",
            body: "We checked for supporting evidence, but the mapped support for this answer is limited.",
          },
          overallConfidence: "medium",
          confidenceExplainer: {
            label: "Medium",
            tone: "medium",
            supports: [],
            weakens: ["Peer validation is incomplete."],
            limits: [],
          },
          blockingCaveats: ["Peer validation is incomplete."],
          criticPhaseStatus: "success",
          reportPhaseStatus: "success",
          weakEvidenceSignals: [],
          contextSignals: [],
          evidenceLinks: [],
          extraArtifactCount: 0,
          reportArtifactId: null,
          evidenceProvenanceHint: null,
          navigationItems: [],
          traceHref: "/projects/project-1/runs/run-3/trace",
          caveatOverflowHref: "/projects/project-1/runs/run-3/trace#run-context-transparency",
        },
        runId: "run-3",
        runHref: "/projects/project-1/runs/run-3/trace",
        runStatus: "partial_success",
        runCreatedAt: "2026-04-18T20:20:00Z",
        runFinishedAt: "2026-04-18T20:23:00Z",
        createdAt: "2026-04-18T20:23:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("Show supporting evidence")).toBeTruthy();
    expect(screen.getByText("Peer validation is incomplete, so the conclusion is only partial.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Show supporting evidence" }));
    expect(screen.getByText("Supporting evidence is limited")).toBeTruthy();
    expect(
      screen.getByText("We checked for supporting evidence, but the mapped support for this answer is limited."),
    ).toBeTruthy();
  });

  it("renders the explicit error narrative instead of generic success copy", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-error",
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
          weakEvidenceSignals: [],
          contextSignals: [],
          evidenceLinks: [],
          extraArtifactCount: 0,
          reportArtifactId: null,
          evidenceProvenanceHint: null,
          navigationItems: [{ key: "trace", label: "Trace", href: "/projects/project-1/runs/run-4/trace" }],
          traceHref: "/projects/project-1/runs/run-4/trace",
          caveatOverflowHref: null,
        },
        runId: "run-4",
        runHref: "/projects/project-1/runs/run-4/trace",
        runStatus: "error",
        runCreatedAt: "2026-04-18T20:30:00Z",
        runFinishedAt: "2026-04-18T20:31:00Z",
        createdAt: "2026-04-18T20:31:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("This analysis didn’t finish cleanly.")).toBeTruthy();
    expect(
      screen.getByText("Open trace to inspect what failed, then retry with narrower wording or refreshed SEC data."),
    ).toBeTruthy();
    expect(screen.queryByText("Run completed without a summary line.")).toBeNull();
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
