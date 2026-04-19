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

/** ``GET /v1/auth/me`` */
export interface CurrentUser {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  preferences_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
}

/** ``GET /v1/auth/capabilities`` */
export interface AuthCapabilitiesResponse {
  allow_open_registration: boolean;
  bootstrap_required: boolean;
  bootstrap_completed: boolean;
}

export type BackgroundDeliveryMode = "sync_only" | "background_ready" | "background_degraded";

export interface BackgroundDeliveryHealth {
  delivery_mode: BackgroundDeliveryMode;
  background_available: boolean;
  detail: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: {
    ok: boolean;
    detail: string | null;
  };
  llm: {
    provider: string;
    ready: boolean;
    message: string;
  };
  evaluation: {
    state_known: boolean;
    sec_dependency_ok: boolean | null;
    storage_dependency_ok: boolean | null;
    recent_degraded_case_count: number | null;
    detail: string | null;
  };
  background_delivery: BackgroundDeliveryHealth;
}

export interface ProjectRead {
  id: string;
  owner_user_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  settings_json: Record<string, unknown> | unknown[] | null;
  tickers: string[] | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

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
  /** Derived from ``run_steps`` + status (no extra persistence). */
  current_phase: string;
  total_steps: number;
  completed_steps: number;
}

/** Per-phase rollup embedded in run transparency (also returned in full from ``GET /v1/runs/{id}/llm-usage``). */
export interface LlmUsageTotals {
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms_total: number;
  estimated_cost_usd: number | null;
  call_count: number;
}

export interface LlmPhaseUsageRow {
  phase: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms_total: number;
  estimated_cost_usd: number | null;
  model_names: string[];
}

/** Wire shape under ``transparency.llm_usage`` (no ``analysis_run_id``). */
export interface LlmRunUsageSummaryWire {
  phases: LlmPhaseUsageRow[];
  totals: LlmUsageTotals;
  pricing_configured: boolean;
  pricing_complete: boolean;
  pricing_source: string;
}

/** Full response from ``GET /v1/runs/{id}/llm-usage``. */
export interface LlmRunUsageSummary extends LlmRunUsageSummaryWire {
  analysis_run_id: string;
}

/** ``GET /v1/runs/{id}?include_transparency=true`` */
export interface NarrativeAnswerSectionPreview {
  heading: string;
  body: string;
}

export interface NarrativeAnswerPreview {
  mode: "full" | "partial";
  thesis: string;
  sections: NarrativeAnswerSectionPreview[];
  fallback_reason: string | null;
}

export interface RunTransparencySummary {
  evidence_artifact_ids: string[];
  evidence_artifacts_by_role: Record<string, string>;
  prompt_versions: Record<string, string> | null;
  model_call_count: number;
  /** Per-phase token, latency, and optional cost rollup when the API computes it. */
  llm_usage?: LlmRunUsageSummaryWire | null;
  report_key_takeaways_preview: string[];
  critic_blocking_caveats: string[];
  critic_overall_confidence: string | null;
  critic_phase_status: string | null;
  report_phase_status: string | null;
  narrative_answer?: NarrativeAnswerPreview | null;
}

export interface RunStepOutputSummary {
  phase_status: string | null;
  skipped: boolean | null;
  skip_reason: string | null;
  issue_count: number | null;
  overall_confidence: string | null;
  key_takeaway_count: number | null;
  markdown_char_count: number | null;
  step_count: number | null;
  artifact_roles: string[];
  weak_evidence_signals: string[];
}

/** Per-step slice from ``GET .../steps?include_transparency=true``. */
export interface RunStepTransparencyView {
  trace: string | null;
  phase: string | null;
  model_call_id: string | null;
  output_summary: RunStepOutputSummary | null;
  linked_artifact_ids: string[];
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  input_payload_json: Record<string, unknown> | unknown[] | null;
  output_payload_json: Record<string, unknown> | unknown[] | null;
  meta_json: Record<string, unknown> | unknown[] | null;
  /** Present when requested with ``include_transparency``; may be omitted on older responses. */
  transparency?: RunTransparencySummary | null;
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
  transparency?: RunStepTransparencyView | null;
}

export interface RunTraceCollectionSummary {
  total: number;
  limit: number;
  has_more: boolean;
}

export interface RunTraceStepPreview extends RunTraceCollectionSummary {
  items: RunStepDetail[];
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

export interface RunTraceArtifactPreview extends RunTraceCollectionSummary {
  items: ArtifactMetadata[];
}

export interface ArtifactDetail extends ArtifactMetadata {
  meta_json: Record<string, unknown> | unknown[] | null;
}

/** ``GET /v1/runs/{id}/model-calls`` — persisted LLM invocations. */
export type ModelCallStatus = "pending" | "running" | "success" | "error" | "cancelled";

export interface ModelCallApiItem {
  id: string;
  analysis_run_id: string | null;
  evaluation_run_id: string | null;
  tool_call_id: string | null;
  provider: string;
  model_name: string;
  prompt_id: string | null;
  prompt_version: string | null;
  status: ModelCallStatus;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  error_detail: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  request_payload_json: Record<string, unknown> | unknown[] | null;
  response_payload_json: Record<string, unknown> | unknown[] | null;
}

export interface RunTraceModelCallPreview extends RunTraceCollectionSummary {
  items: ModelCallApiItem[];
}

export interface RunTraceShell {
  run: AnalysisRunSummary;
  transparency: RunTransparencySummary | null;
  timeline_preview: RunStepDetail[];
  steps: RunTraceStepPreview;
  artifacts: RunTraceArtifactPreview;
  model_calls: RunTraceModelCallPreview;
}

export type TraceCollectionKey = "steps" | "artifacts" | "model-calls";

export type RunTraceRawDetail =
  | {
      kind: "step";
      selectedId: string;
      item: RunStepDetail | null;
      closeHref: string;
      errorMessage?: string | null;
    }
  | {
      kind: "model-call";
      selectedId: string;
      item: ModelCallApiItem | null;
      closeHref: string;
      errorMessage?: string | null;
    };

export interface RunPayloadQueryOptions {
  includePayloads?: boolean;
  includeTransparency?: boolean;
}

export interface RunStepQueryOptions extends RunPayloadQueryOptions {
  status?: RunStepStatus;
  trace?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface ArtifactQueryOptions {
  roleKey?: string;
  kind?: ArtifactKind;
  includeDeleted?: boolean;
  limit?: number;
  offset?: number;
}

export interface ModelCallQueryOptions {
  includePayloads?: boolean;
  status?: ModelCallStatus;
  promptId?: string;
  q?: string;
  limit?: number;
  offset?: number;
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

export type PromptRoutingSource = "deterministic";

export type PromptRoutingIntent = "anomaly_analysis" | "peer_report" | "full_pipeline_run";

export type PromptRoutingGoalCode =
  | "anomaly_unusual_changes"
  | "anomaly_for_companies"
  | "peer_comparison"
  | "full_pipeline"
  | "trend_deterioration"
  | "mixed_trend_and_anomaly"
  | "resolve_only"
  | "fetch_raw"
  | "planning_failed";

export type PromptRoutingPlanTemplateId =
  | "anomaly_unusual_changes"
  | "trend_deterioration"
  | "peer_comparison"
  | "mixed_trend_and_anomaly";

export interface PromptRoutingPreviewRequest {
  project_id: string;
  analysis_goal: string;
  tickers: string[];
  refresh?: boolean;
}

export interface PromptRoutingPreviewResponse {
  supported: boolean;
  routing_source: PromptRoutingSource;
  effective_tickers: string[];
  out_of_scope_tickers: string[];
  rewrite_suggestions: string[];
  reason: string | null;
  intent: PromptRoutingIntent | null;
  goal_code: PromptRoutingGoalCode | null;
  plan_template_id: PromptRoutingPlanTemplateId | null;
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
