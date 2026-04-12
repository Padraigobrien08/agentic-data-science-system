import { describe, expect, it } from "vitest";

import type { ArtifactMetadata } from "@/lib/api/types";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import { buildPrimaryAnswerView } from "@/lib/run-primary-view";

const stubArtifact: ArtifactMetadata = {
  id: "art-1",
  analysis_run_id: "r1",
  evaluation_run_id: null,
  run_step_id: null,
  role_key: "report_md",
  kind: "document",
  mime_type: "text/markdown",
  byte_size: 10,
  content_sha256: null,
  storage_uri: "s3://x",
  created_at: "2020-01-01T00:00:00Z",
  updated_at: "2020-01-01T00:00:00Z",
};

describe("buildPrimaryAnswerView evidence linking", () => {
  it("adds takeaway and alignment chips when nav context is provided", () => {
    const ai: ParsedAiAgents = {
      traceability: {
        evidence_artifacts_by_role: { report_md: "art-1", panel_x: "art-2" },
        critic: {
          plan_alignment_findings: [{ code: "GAP", severity: "low", detail: "Minor" }],
          artifact_summary_roles_used: ["panel_x"],
        },
      },
    };

    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Test goal",
        input_payload_json: null,
        output_payload_json: {
          user_facing_report: { markdown: "# Hi", key_takeaways: ["Point A"] },
        },
      },
      [stubArtifact],
      null,
      { markdown: "# Hi", key_takeaways: ["Point A"] },
      ai,
      { projectId: "p1", runId: "r1" },
    );

    expect(view.takeawayRows).toHaveLength(1);
    expect(view.takeawayRows[0]!.chips.some((c) => c.label === "Report")).toBe(true);
    expect(view.takeawayRows[0]!.chips.some((c) => c.href.includes("/trace#run-artifacts"))).toBe(true);
    expect(view.alignmentFindings[0]!.chips[0]!.href).toContain("/trace#run-agents");
  });

  it("omits chips when nav context is omitted", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: null,
        input_payload_json: null,
        output_payload_json: {
          user_facing_report: { markdown: "# Hi", key_takeaways: ["Only"] },
        },
      },
      [],
      null,
      { markdown: "# Hi", key_takeaways: ["Only"] },
      null,
    );
    expect(view.takeawayRows[0]!.chips).toEqual([]);
  });
});
