import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/runs/execute-run-button", () => ({
  ExecuteRunButton: () => <button type="button">Re-run</button>,
}));

import { RunInspectionPanel } from "@/components/runs/run-inspection-panel";
import type { PrimaryAnswerView } from "@/lib/run-primary-view";

const view: PrimaryAnswerView = {
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
  takeawayRows: [
    {
      text: "Revenue growth deterioration appears in several recent quarters.",
      chips: [{ label: "Evidence", href: "/projects/project-1/runs/run-1/trace#run-artifacts" }],
    },
  ],
  alignmentFindings: [],
  supplementalEvidence: [
    {
      id: "support-1",
      title: "Revenue growth deterioration appears",
      reason: "Revenue growth deterioration appears in several recent quarters.",
      jump: { label: "Open source", href: "/projects/project-1/runs/run-1/trace#run-artifacts" },
      source: "takeaway",
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
  inlineCharts: [],
  evidenceLinks: [{ role: "report_md", artifactId: "report-1" }],
  extraArtifactCount: 1,
  reportArtifactId: "report-1",
  weakEvidenceSignals: ["insufficient_peers_rows"],
  contextSignals: [],
  conclusionRider: null,
  evidenceProvenanceHint: "Deep dive includes the full artifact inventory.",
  suggestionGoalText: "Assess whether margin pressure is temporary or structural for MSFT",
  inputTickers: ["MSFT"],
};

describe("RunInspectionPanel", () => {
  it("frames the run page as a secondary inspection surface and keeps verification content", () => {
    render(
      <RunInspectionPanel
        projectId="project-1"
        runId="run-1"
        runStatus="success"
        view={view}
        canExecute={false}
      />,
    );

    expect(screen.getByText("Inspection focus")).toBeTruthy();
    expect(screen.getByText(/The full answer lives in workspace chat\./)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Back to chat" }).getAttribute("href")).toBe("/projects/project-1/chat");
    expect(screen.getByRole("link", { name: "Open trace" }).getAttribute("href")).toBe(
      "/projects/project-1/runs/run-1/trace",
    );
    expect(screen.getByText("Verify this analysis")).toBeTruthy();
    expect(screen.queryByText("Top findings")).toBeNull();
    expect(screen.queryByText("Confidence & caveats")).toBeNull();
  });
});
