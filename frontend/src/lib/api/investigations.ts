import "server-only";

import { apiGet } from "./client";
import type { InvestigationDetail, InvestigationSummary } from "./types";

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
