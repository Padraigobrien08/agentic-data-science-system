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
    expect(view.supplementalEvidence).toHaveLength(2);
    expect(view.supplementalEvidence[0]?.source).toBe("takeaway");
    expect(view.supplementalEvidence[0]?.jump?.href).toContain("/artifacts/art-1");
    expect(view.supplementalEvidence[1]?.source).toBe("alignment");
    expect(view.inlineCharts).toEqual([]);
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
    expect(view.supplementalEvidence[0]?.jump).toBeNull();
    expect(view.supplementalEvidenceState.mode).toBe("available");
    expect(view.inlineCharts).toEqual([]);
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
    expect(view.supplementalEvidence).toEqual([]);
    expect(view.supplementalEvidenceState.mode).toBe("limited");
    expect(view.supplementalEvidenceState.heading).toBe("Supporting evidence is limited");
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
    expect(view.supplementalEvidence).toHaveLength(1);
    expect(view.supplementalEvidence[0]?.title).toContain("MSFT shows repeated revenue-growth");
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
    expect(view.supplementalEvidence[0]?.reason).toBe(
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
    expect(view.supplementalEvidence).toEqual([]);
    expect(view.supplementalEvidenceState.mode).toBe("limited");
    expect(view.supplementalEvidenceState.body).toBe(
      "We checked for supporting evidence, but the mapped support for this answer is limited.",
    );
  });

  it("keeps an explicit empty evidence disclosure state when no support surfaces are available", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Find unusual financial changes",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Find unusual financial changes" },
        output_payload_json: null,
      },
      [],
      null,
      null,
      null,
      null,
      { projectId: "p1", runId: "r1" },
    );

    expect(view.supplementalEvidence).toEqual([]);
    expect(view.supplementalEvidenceState.mode).toBe("empty");
    expect(view.supplementalEvidenceState.heading).toBe("No mapped support is available");
    expect(view.supplementalEvidenceState.body).toBe(
      "Artifacts or mapped support were not available for this answer view.",
    );
    expect(view.inlineCharts).toEqual([]);
  });

  it("maps trusted inline chart previews and drops malformed chart rows", () => {
    const view = buildPrimaryAnswerView(
      {
        orchestration_goal_text: "Assess whether margin pressure is temporary or structural for MSFT",
        input_payload_json: { tickers: ["MSFT"], analysis_goal: "Assess whether margin pressure is temporary or structural for MSFT" },
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
          mode: "full",
          thesis: "MSFT margin pressure looks cyclical rather than structural.",
          sections: [],
          fallback_reason: null,
        },
        report_key_takeaways_preview: [],
        critic_blocking_caveats: [],
        critic_overall_confidence: "medium",
        critic_phase_status: "success",
        report_phase_status: "success",
        inline_charts: [
          {
            chart_id: "trend-msft-margin",
            kind: "line",
            metric_key: "operating_margin",
            metric_label: "Operating margin",
            caption: "Operating margin compressed in the latest quarters, which supports the cyclical pressure call.",
            x_axis_label: "Quarter",
            y_axis_label: "Operating margin",
            value_format: "percent",
            series: [{ key: "focal", label: "MSFT", color_token: "chart-1" }],
            rows: [
              { x_value: "2025-Q3", values: { focal: 0.41 } },
              { x_value: "2025-Q4", values: { focal: 0.38 } },
            ],
            markers: [{ x_value: "2025-Q4", label: "Shift" }],
            source_artifact_roles: ["features_csv", "trend_break_signals_csv"],
          },
          {
            chart_id: "ignored-empty",
            kind: "grouped_bar",
            metric_key: "peer_gap",
            metric_label: "Peer gap",
            caption: "This chart should not render because every row is empty.",
            x_axis_label: "Quarter",
            y_axis_label: "Peer gap",
            value_format: "number",
            series: [{ key: "focal", label: "MSFT", color_token: "chart-1" }],
            rows: [{ x_value: "2025-Q4", values: { focal: null } }],
            markers: [],
            source_artifact_roles: ["peer_signals_csv"],
          },
        ],
      },
      { projectId: "p1", runId: "r1" },
    );

    expect(view.inlineCharts).toHaveLength(1);
    expect(view.inlineCharts[0]).toMatchObject({
      chartId: "trend-msft-margin",
      kind: "line",
      metricKey: "operating_margin",
      valueFormat: "percent",
      caption:
        "Operating margin compressed in the latest quarters, which supports the cyclical pressure call.",
    });
    expect(view.inlineCharts[0]?.series).toEqual([{ key: "focal", label: "MSFT", colorToken: "chart-1" }]);
    expect(view.inlineCharts[0]?.markers).toEqual([{ xValue: "2025-Q4", label: "Shift" }]);
  });
});
