/**
 * Mirrors `backend/schemas/demo_capture.py`.
 *
 * Hand-written rather than generated because it is the *shape* that is stable, not the
 * data: `generated.ts` is rewritten on every export and must stay purely mechanical.
 *
 * This is not part of the `/v1` contract in `@/lib/api/types` — model payloads are
 * admin-gated on the live API, and these ship only for demos an operator deliberately
 * published.
 */

export type DemoModelCall = {
  sequence: number;
  id: string;
  provider: string;
  model_name: string;
  prompt_id: string | null;
  prompt_version: string | null;
  status: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  est_cost_usd: number | null;
  started_at: string | null;
  finished_at: string | null;
  request_payload_json: unknown;
  response_payload_json: unknown;
  error_detail: string | null;
};

export type DemoChatMessage = {
  sequence: number;
  id: string;
  role: string;
  status: string;
  content: string | null;
  analysis_run_id: string | null;
  created_at: string;
};

export type DemoChatThread = {
  id: string;
  title: string | null;
  created_at: string;
  messages: DemoChatMessage[];
};

export type DemoCaptureTotals = {
  model_calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  est_cost_usd: number;
  /** False when no price table was configured at export time — cost is unknown, not zero. */
  priced: boolean;
};

export type DemoCapture = {
  demo_slug: string;
  investigation_id: string;
  analysis_run_id: string | null;
  totals: DemoCaptureTotals;
  model_calls: DemoModelCall[];
  chat: DemoChatThread[];
};
