import { describe, expect, it } from "vitest";

import { indexModelCallsById, modelCallLabel } from "@/lib/agent-transparency";
import {
  buildReportEvidenceItems,
  classifyReportEvidenceStrength,
} from "@/lib/report-evidence-context";
import { deriveExecutionPlan } from "@/lib/run-trace-derive";
import type { ModelCallApiItem } from "@/lib/api/types";
import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

describe("Sprint 3 transparency libs", () => {
  it("buildReportEvidenceItems links report phase_output roles to artifact ids", () => {
    const artifacts = [
      {
        id: "art-panel",
        analysis_run_id: "run-1",
        evaluation_run_id: null,
        run_step_id: null,
        role_key: "panel_csv",
        kind: "tabular" as const,
        mime_type: null,
        byte_size: 10,
        content_sha256: null,
        storage_uri: "local:x",
        created_at: "2020-01-01T00:00:00Z",
        updated_at: "2020-01-01T00:00:00Z",
      },
    ];
    const items = buildReportEvidenceItems(
      {
        artifact_refs: [{ role: "panel_csv", basename: "p.csv" }],
      },
      undefined,
      artifacts,
    );
    expect(items).toHaveLength(1);
    expect(items[0].roleKey).toBe("panel_csv");
    expect(items[0].artifactId).toBe("art-panel");
    expect(items[0].basename).toBe("p.csv");
  });

  it("classifyReportEvidenceStrength marks weak when critic confidence is low", () => {
    const out = classifyReportEvidenceStrength(
      { overall_confidence: "low", issues: [] },
      undefined,
      { phase_status: "success" },
      { phase_status: "success" },
    );
    expect(out.level).toBe("weak");
    expect(out.reasons.some((r) => r.includes("low"))).toBe(true);
  });

  it("deriveExecutionPlan prefers phase_output ordered_plan", () => {
    const orch: ParsedOrchestrationOutput = {
      step_statuses: [{ order: 0, tool_name: "from_status", mcp_status: "success" }],
    };
    const ai = {
      planning: {
        phase_output: {
          ordered_plan: [{ order: 0, tool_name: "from_po", label: "x" }],
        },
      },
    } as ParsedAiAgents;
    const rows = deriveExecutionPlan(orch, ai);
    expect(rows).toHaveLength(1);
    expect(rows[0].tool_name).toBe("from_po");
    expect(rows[0].source).toBe("phase_output");
  });

  it("indexModelCallsById and modelCallLabel map registered prompt ids", () => {
    const calls: ModelCallApiItem[] = [
      {
        id: "mc-1",
        analysis_run_id: "r1",
        evaluation_run_id: null,
        tool_call_id: null,
        provider: "openai",
        model_name: "gpt-test",
        prompt_id: "edgar.agent.critic",
        prompt_version: "2.0.0",
        status: "success",
        prompt_tokens: 1,
        completion_tokens: 2,
        latency_ms: 3,
        error_detail: null,
        started_at: null,
        finished_at: null,
        created_at: "2020-01-01T00:00:00Z",
        updated_at: "2020-01-01T00:00:00Z",
        request_payload_json: null,
        response_payload_json: null,
      },
    ];
    const m = indexModelCallsById(calls);
    expect(m.get("mc-1")?.model_name).toBe("gpt-test");
    expect(modelCallLabel(calls[0])).toBe("Critic");
  });
});
