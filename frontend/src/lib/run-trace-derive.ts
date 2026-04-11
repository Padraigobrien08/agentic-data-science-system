/**
 * Derive a single coherent “run trace” view from orchestration output, ai_agents meta, and steps.
 */

import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type {
  ParsedOrchestrationOutput,
  StepStatusWire,
  ToolResultSummaryWire,
} from "@/lib/orchestration-output";
export type PlanRow = {
  order: number;
  tool_name: string;
  label?: string;
  mcp_status?: string;
  source: "phase_output" | "step_statuses" | "llm_planning" | "tool_call_sequence";
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Ordered MCP plan rows: prefer planning.phase_output, else step_statuses, else LLM planning steps. */
export function deriveExecutionPlan(
  orch: ParsedOrchestrationOutput | null,
  ai: ParsedAiAgents | null,
): PlanRow[] {
  const po = ai?.planning && isRecord((ai.planning as Record<string, unknown>).phase_output)
    ? ((ai.planning as Record<string, unknown>).phase_output as Record<string, unknown>)
    : null;
  const ordered = po?.ordered_plan;
  if (Array.isArray(ordered) && ordered.length > 0) {
    const out: PlanRow[] = [];
    for (const row of ordered) {
      if (!isRecord(row)) continue;
      const order = typeof row.order === "number" ? row.order : Number(row.order);
      const tool_name = typeof row.tool_name === "string" ? row.tool_name : "";
      if (!Number.isFinite(order) || !tool_name) continue;
      const label = typeof row.label === "string" ? row.label : undefined;
      const mcp_status = typeof row.mcp_status === "string" ? row.mcp_status : undefined;
      out.push({ order, tool_name, label, mcp_status, source: "phase_output" });
    }
    return out.sort((a, b) => a.order - b.order);
  }

  const steps = orch?.step_statuses;
  if (steps && steps.length > 0) {
    return steps
      .slice()
      .sort((a, b) => a.order - b.order)
      .map((s: StepStatusWire) => ({
        order: s.order,
        tool_name: s.tool_name,
        label: s.label,
        mcp_status: s.mcp_status,
        source: "step_statuses" as const,
      }));
  }

  const llm = ai?.planning?.steps;
  if (llm && llm.length > 0) {
    return llm.map((s) => ({
      order: s.order,
      tool_name: s.tool_name,
      label: s.label,
      source: "llm_planning" as const,
    }));
  }

  const seq = orch?.tool_call_sequence;
  if (seq && seq.length > 0) {
    return seq.map((t) => ({
      order: t.order,
      tool_name: t.tool_name,
      source: "tool_call_sequence" as const,
    }));
  }

  return [];
}

export function stepLaneFromMeta(meta: unknown): { lane: string; trace: string } {
  if (!isRecord(meta)) return { lane: "—", trace: "" };
  const trace = typeof meta.trace === "string" ? meta.trace : "";
  const phase = typeof meta.phase === "string" ? meta.phase : "";
  if (trace === "mcp_executor") return { lane: "MCP", trace: "executor" };
  if (trace === "critic_agent") return { lane: "LLM", trace: "critic" };
  if (trace === "report_agent") return { lane: "LLM", trace: "report" };
  if (phase === "llm") return { lane: "LLM", trace: trace || "llm" };
  if (trace) return { lane: "SYS", trace };
  return { lane: "—", trace: "" };
}

/** Map tool order → result summary row for cross-linking in the plan table. */
export function toolResultByOrder(
  rows: ToolResultSummaryWire[] | undefined,
): Map<number, ToolResultSummaryWire> {
  const m = new Map<number, ToolResultSummaryWire>();
  if (!rows) return m;
  for (const r of rows) {
    m.set(r.order, r);
  }
  return m;
}
