/**
 * Mirrors backend JSON shapes (`backend/schemas/api_phase_a.py`, etc.).
 * Keep loose where the API returns generic JSON blobs.
 */

export type AnalysisRunStatus =
  | "pending"
  | "queued"
  | "running"
  | "success"
  | "partial_success"
  | "no_data"
  | "error"
  | "cancelled";

export type RunStepStatus =
  | "pending"
  | "running"
  | "success"
  | "skipped"
  | "no_data"
  | "error";

export type ArtifactKind = "tabular" | "document" | "binary" | "json" | "other";

export interface AnalysisRunSummary {
  id: string;
  project_id: string;
  initiated_by_user_id: string | null;
  correlation_id: string | null;
  status: AnalysisRunStatus;
  orchestration_goal_text: string | null;
  error_summary: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  input_payload_json: Record<string, unknown> | unknown[] | null;
  output_payload_json: Record<string, unknown> | unknown[] | null;
  meta_json: Record<string, unknown> | unknown[] | null;
}

export interface RunStepDetail {
  id: string;
  analysis_run_id: string;
  step_index: number;
  status: RunStepStatus;
  label: string | null;
  planned_tool_name: string | null;
  detail: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  planner_tool_input_json: Record<string, unknown> | unknown[] | null;
  meta_json: Record<string, unknown> | unknown[] | null;
}

export interface ArtifactMetadata {
  id: string;
  analysis_run_id: string | null;
  evaluation_run_id: string | null;
  run_step_id: string | null;
  role_key: string;
  kind: ArtifactKind;
  mime_type: string | null;
  byte_size: number | null;
  content_sha256: string | null;
  storage_uri: string;
  created_at: string;
  updated_at: string;
}

export interface ArtifactDetail extends ArtifactMetadata {
  meta_json: Record<string, unknown> | unknown[] | null;
}

/** GET /v1/artifacts/{id}/preview */
export interface ArtifactPreviewResponse {
  format: "text" | "json";
  text: string;
  truncated: boolean;
  mime_type: string | null;
  total_bytes: number | null;
  json_valid: boolean | null;
}

export interface AnalysisRunCreateBody {
  project_id: string;
  initiated_by_user_id?: string | null;
  correlation_id?: string | null;
  orchestration_goal_text?: string | null;
  input_payload_json?: Record<string, unknown> | null;
  meta_json?: Record<string, unknown> | null;
  enqueue_execution?: boolean;
}

export interface ExecuteRunOverrides {
  tickers?: string[] | null;
  analysis_goal?: string | null;
  refresh?: boolean | null;
}

export interface ExecuteRunResponse {
  analysis_run_id: string;
  orchestration_run_id: string;
  orchestration_status: string;
  message: string;
  final_summary: string;
  artifact_count: number;
  db_status: AnalysisRunStatus;
}
