import "server-only";

import { apiGet, apiPost } from "./client";
import type {
  AnalysisRunCreateBody,
  AnalysisRunDetail,
  AnalysisRunSummary,
  ArtifactMetadata,
  ExecuteRunOverrides,
  ExecuteRunResponse,
  RunStepDetail,
} from "./types";

export async function listRuns(projectId: string): Promise<AnalysisRunSummary[]> {
  const q = new URLSearchParams({ project_id: projectId });
  return apiGet<AnalysisRunSummary[]>(`/v1/runs?${q.toString()}`);
}

export async function getRun(
  runId: string,
  includePayloads: boolean,
): Promise<AnalysisRunDetail> {
  const q = includePayloads ? "?include_payloads=true" : "";
  return apiGet<AnalysisRunDetail>(`/v1/runs/${runId}${q}`);
}

export async function listRunSteps(
  runId: string,
  includePayloads: boolean,
): Promise<RunStepDetail[]> {
  const q = includePayloads ? "?include_payloads=true" : "";
  return apiGet<RunStepDetail[]>(`/v1/runs/${runId}/steps${q}`);
}

export async function listRunArtifacts(runId: string): Promise<ArtifactMetadata[]> {
  return apiGet<ArtifactMetadata[]>(`/v1/runs/${runId}/artifacts`);
}

export async function createRun(body: AnalysisRunCreateBody): Promise<AnalysisRunSummary> {
  return apiPost<AnalysisRunSummary>("/v1/runs", body);
}

export async function executeRun(
  runId: string,
  overrides?: ExecuteRunOverrides | null,
): Promise<ExecuteRunResponse> {
  return apiPost<ExecuteRunResponse>(`/v1/runs/${runId}/execute`, overrides ?? {});
}
