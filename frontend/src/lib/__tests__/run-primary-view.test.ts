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
      null,
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

  it("explains successful runs that produced a report but no structured findings", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Find unusual financial changes",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Find unusual financial changes" },
        output_payload_json: null,
      },
      [stubArtifact],
      {
        status: "success",
        message: "Orchestration completed successfully.",
        final_summary: "success: Orchestration completed successfully. | intent=anomaly_analysis",
        tool_results_summary: [
          {
            order: 0,
            tool_name: "run_pipeline",
            mcp_status: "success",
            anomaly_count: 8,
            panel_row_count: 17,
            report_character_count: 1200,
          },
        ],
      },
      null,
      null,
      null,
      { projectId: "p1", runId: "r1" },
    );

    expect(view.narrativeAnswer.mode).toBe("legacy");
    expect(view.narrativeAnswer.fallbackReason).toBe("legacy_summary");
    expect(view.summaryLine).toBe(
      "The run completed and produced a report, but no structured findings were extracted into this answer card.",
    );
    expect(view.emptyStateReason).toBe(
      "The run completed and produced a report, but no structured findings were extracted into this answer card.",
    );
  });

  it("uses transparency takeaways when raw payloads are not available", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Is MSFT showing persistent deterioration?",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Is MSFT showing persistent deterioration?" },
        output_payload_json: null,
      },
      [stubArtifact],
      {
        status: "success",
        message: "Orchestration completed successfully.",
        final_summary: "success: Orchestration completed successfully. | intent=anomaly_analysis",
        tool_results_summary: [
          {
            order: 0,
            tool_name: "run_pipeline",
            mcp_status: "success",
            anomaly_count: 8,
            panel_row_count: 17,
            report_character_count: 1200,
          },
        ],
      },
      null,
      null,
      {
        evidence_artifact_ids: ["art-1"],
        evidence_artifacts_by_role: { report_md: "art-1" },
        prompt_versions: null,
        model_call_count: 2,
        llm_usage: null,
        narrative_answer: {
          mode: "full",
          thesis: "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
          sections: [
            {
              heading: "What's happening",
              body: "Recent summarized rows point to repeated revenue-growth weakness.",
            },
            {
              heading: "Why we think that",
              body: "The report preview ties that thesis to the loaded findings summaries.",
            },
          ],
          fallback_reason: null,
        },
        report_key_takeaways_preview: [
          "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
        ],
        confidence_explainer: {
          supports: ["Structured findings match the deterioration question."],
          weakens: ["Peer coverage is insufficient."],
          limits: ["Coverage only spans eight recent quarters."],
        },
        critic_blocking_caveats: ["Peer coverage is insufficient."],
        critic_overall_confidence: "medium",
        critic_phase_status: "success",
        report_phase_status: "success",
      },
      { projectId: "p1", runId: "r1" },
    );

    expect(view.summaryLine).toBe(
      "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
    );
    expect(view.narrativeAnswer.mode).toBe("full");
    expect(view.narrativeAnswer.sections[0]?.heading).toBe("What's happening");
    expect(view.takeawayRows).toHaveLength(1);
    expect(view.emptyStateReason).toBeNull();
    expect(view.blockingCaveats).toEqual(["Peer coverage is insufficient."]);
    expect(view.overallConfidence).toBe("medium");
    expect(view.confidenceExplainer.label).toBe("Medium");
    expect(view.confidenceExplainer.weakens).toEqual(["Peer coverage is insufficient."]);
  });

  it("promotes the first real takeaway when the orchestration summary is generic", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Is MSFT showing persistent deterioration?",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Is MSFT showing persistent deterioration?" },
        output_payload_json: {
          user_facing_report: {
            markdown: "# Report",
            key_takeaways: [
              "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
              "Margin quality is mixed rather than persistently deteriorating.",
            ],
          },
        },
      },
      [stubArtifact],
      {
        status: "success",
        message: "Orchestration completed successfully.",
        final_summary: "success: Orchestration completed successfully. | intent=anomaly_analysis",
        tool_results_summary: [
          {
            order: 0,
            tool_name: "run_pipeline",
            mcp_status: "success",
            anomaly_count: 8,
            panel_row_count: 17,
            report_character_count: 1200,
          },
        ],
      },
      {
        markdown: "# Report",
        key_takeaways: [
          "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
          "Margin quality is mixed rather than persistently deteriorating.",
        ],
      },
      null,
      null,
      { projectId: "p1", runId: "r1" },
    );

    expect(view.summaryLine).toBe(
      "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
    );
    expect(view.narrativeAnswer.mode).toBe("legacy");
    expect(view.narrativeAnswer.fallbackReason).toBe("legacy_summary");
    expect(view.emptyStateReason).toBeNull();
    expect(view.takeawayRows[0]?.text).toBe(
      "MSFT shows repeated revenue-growth deterioration across multiple Q1 periods.",
    );
  });

  it("prefers a partial narrative preview when evidence is limited", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Is MSFT showing persistent deterioration?",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Is MSFT showing persistent deterioration?" },
        output_payload_json: null,
      },
      [stubArtifact],
      null,
      null,
      null,
      {
        evidence_artifact_ids: ["art-1"],
        evidence_artifacts_by_role: { report_md: "art-1" },
        prompt_versions: null,
        model_call_count: 1,
        llm_usage: null,
        narrative_answer: {
          mode: "partial",
          thesis: "The evidence is limited, but the loaded summaries still point to weaker revenue growth.",
          sections: [
            {
              heading: "What weakens the claim",
              body: "Peer validation is incomplete, so the conclusion is only partial.",
            },
          ],
          fallback_reason: "limited_evidence",
        },
        report_key_takeaways_preview: [],
        critic_blocking_caveats: ["Peer validation is incomplete."],
        critic_overall_confidence: "medium",
        critic_phase_status: "success",
        report_phase_status: "success",
      },
      { projectId: "p1", runId: "r1" },
    );

    expect(view.narrativeAnswer.mode).toBe("partial");
    expect(view.narrativeAnswer.fallbackReason).toBe("limited_evidence");
    expect(view.summaryLine).toBe(
      "The evidence is limited, but the loaded summaries still point to weaker revenue growth.",
    );
    expect(view.emptyStateReason).toBeNull();
  });
});
