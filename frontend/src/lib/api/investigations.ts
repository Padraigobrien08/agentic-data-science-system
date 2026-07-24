import "server-only";

import { apiGet, apiPost } from "./client";
import type {
  HealthResponse,
  InvestigationCreateBody,
  InvestigationCreateResponse,
  InvestigationDetail,
  InvestigationSummary,
} from "./types";

/** Whether the agentic investigation engine is enabled on the backend (false on error). */
export async function agenticEngineEnabled(): Promise<boolean> {
  try {
    const health = await apiGet<HealthResponse>("/v1/health");
    return Boolean(health.agentic_engine_enabled);
  } catch {
    return false;
  }
}

/** Create an agentic investigation over a dataset and run it (synchronous). */
export async function createInvestigation(
  body: InvestigationCreateBody,
): Promise<InvestigationCreateResponse> {
  return apiPost<InvestigationCreateResponse>("/v1/investigations", body);
}

/** List investigations owned by the user, optionally scoped to a project. Newest first. */
export async function listInvestigations(
  projectId?: string,
): Promise<InvestigationSummary[]> {
  const q = new URLSearchParams();
  if (projectId) q.set("project_id", projectId);
  const s = q.toString();
  return apiGet<InvestigationSummary[]>(`/v1/investigations${s ? `?${s}` : ""}`);
}

/** Full investigation: hypotheses, evidence, decisions, critiques, experiments, conclusion, timeline. */
export async function getInvestigation(
  investigationId: string,
): Promise<InvestigationDetail> {
  return apiGet<InvestigationDetail>(`/v1/investigations/${investigationId}`);
}
