/**
 * Helpers for `output_payload_json` after a full orchestration persist (full `OrchestrationOutput` dump
 * plus optional `user_facing_report` merge).
 */

export type StepStatusWire = {
  order: number;
  tool_name: string;
  label?: string;
  mcp_status: string;
  detail?: string | null;
};

export type ToolCallSequenceWire = {
  order: number;
  tool_name: string;
  params?: Record<string, unknown>;
};

export type ToolResultSummaryWire = {
  order: number;
  tool_name: string;
  mcp_status: string;
  panel_row_count?: number | null;
  feature_row_count?: number | null;
  anomaly_count?: number | null;
  report_character_count?: number | null;
  ciks_observed?: number[];
  artifact_paths?: Record<string, string>;
  provenance_keys?: string[];
};

export type ParsedOrchestrationOutput = {
  run_id?: string;
  status?: string;
  message?: string;
  final_summary?: string;
  interpreted_goal?: unknown;
  tool_call_sequence?: ToolCallSequenceWire[];
  tool_results_summary?: ToolResultSummaryWire[];
  step_statuses?: StepStatusWire[];
  errors?: unknown[];
  warnings?: unknown[];
  artifact_paths?: Record<string, string>;
  final_report_path?: string | null;
};

export type UserFacingReport = {
  markdown: string;
  key_takeaways: string[];
  model_call_id?: string | null;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Top-level orchestration fields when `output_payload_json` is the orchestration snapshot. */
export function parseOrchestrationOutput(
  output: unknown,
): ParsedOrchestrationOutput | null {
  if (!isRecord(output)) return null;
  const step_statuses = output.step_statuses;
  const tool_call_sequence = Array.isArray(output.tool_call_sequence)
    ? (output.tool_call_sequence as ToolCallSequenceWire[])
    : undefined;
  const tool_results_summary = Array.isArray(output.tool_results_summary)
    ? (output.tool_results_summary as ToolResultSummaryWire[])
    : undefined;
  return {
    run_id: typeof output.run_id === "string" ? output.run_id : undefined,
    status: typeof output.status === "string" ? output.status : undefined,
    message: typeof output.message === "string" ? output.message : undefined,
    final_summary:
      typeof output.final_summary === "string" ? output.final_summary : undefined,
    interpreted_goal: output.interpreted_goal,
    tool_call_sequence,
    tool_results_summary,
    step_statuses: Array.isArray(step_statuses)
      ? (step_statuses as StepStatusWire[])
      : undefined,
    errors: Array.isArray(output.errors) ? output.errors : undefined,
    warnings: Array.isArray(output.warnings) ? output.warnings : undefined,
    artifact_paths: isRecord(output.artifact_paths)
      ? (output.artifact_paths as Record<string, string>)
      : undefined,
    final_report_path:
      typeof output.final_report_path === "string"
        ? output.final_report_path
        : output.final_report_path === null
          ? null
          : undefined,
  };
}

/** `user_facing_report` object merged into output payload by the traceable pipeline. */
export function parseUserFacingReport(output: unknown): UserFacingReport | null {
  if (!isRecord(output)) return null;
  const block = output.user_facing_report;
  if (!isRecord(block)) return null;
  const md = block.markdown;
  if (typeof md !== "string" || !md.trim()) return null;
  const rawTakes = block.key_takeaways;
  const key_takeaways = Array.isArray(rawTakes)
    ? rawTakes.filter((x): x is string => typeof x === "string")
    : [];
  const model_call_id =
    typeof block.model_call_id === "string" ? block.model_call_id : null;
  return { markdown: md, key_takeaways, model_call_id };
}
