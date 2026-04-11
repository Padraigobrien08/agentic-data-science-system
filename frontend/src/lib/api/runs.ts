import "server-only";

import { apiGet, apiPost } from "./client";
import type {
  AnalysisRunCreateBody,
  AnalysisRunDetail,
  AnalysisRunSummary,
  ArtifactMetadata,
  ExecuteRunOverrides,
  ExecuteRunResponse,
  ModelCallApiItem,
  RunStepDetail,
} from "./types";

export type RunFetchOptions = {
  includePayloads?: boolean;
  includeTransparency?: boolean;
};

function runQueryString(opts: boolean | RunFetchOptions | undefined): string {
  const o: RunFetchOptions =
    typeof opts === "boolean" ? { includePayloads: opts } : opts ?? {};
  const p = new URLSearchParams();
  if (o.includePayloads) p.set("include_payloads", "true");
  if (o.includeTransparency) p.set("include_transparency", "true");
  const s = p.toString();
  return s ? `?${s}` : "";
}

export async function listRuns(projectId: string): Promise<AnalysisRunSummary[]> {
  const q = new URLSearchParams({ project_id: projectId });
  return apiGet<AnalysisRunSummary[]>(`/v1/runs?${q.toString()}`);
}

/** @param options Pass ``true`` for ``include_payloads`` only, or an object for transparency flags. */
export async function getRun(
  runId: string,
  options?: boolean | RunFetchOptions,
): Promise<AnalysisRunDetail> {
  const q = runQueryString(options);
  return apiGet<AnalysisRunDetail>(`/v1/runs/${runId}${q}`);
}

/** @param options Pass ``true`` for ``include_payloads`` only, or an object for transparency flags. */
export async function listRunSteps(
  runId: string,
  options?: boolean | RunFetchOptions,
): Promise<RunStepDetail[]> {
  const q = runQueryString(options);
  return apiGet<RunStepDetail[]>(`/v1/runs/${runId}/steps${q}`);
}

export async function listRunArtifacts(runId: string): Promise<ArtifactMetadata[]> {
  return apiGet<ArtifactMetadata[]>(`/v1/runs/${runId}/artifacts`);
}

export async function listRunModelCalls(
  runId: string,
  includePayloads: boolean,
): Promise<ModelCallApiItem[]> {
  const q = includePayloads ? "?include_payloads=true" : "";
  return apiGet<ModelCallApiItem[]>(`/v1/runs/${runId}/model-calls${q}`);
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
