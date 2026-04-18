import "server-only";

import { apiGet, apiPost } from "./client";
import type {
  AnalysisRunCreateBody,
  AnalysisRunDetail,
  AnalysisRunSummary,
  ArtifactQueryOptions,
  ArtifactMetadata,
  ExecuteRunOverrides,
  ExecuteRunResponse,
  LlmRunUsageSummary,
  ModelCallQueryOptions,
  ModelCallApiItem,
  RunPayloadQueryOptions,
  RunStepQueryOptions,
  RunStepDetail,
  RunTraceShell,
} from "./types";

export type RunFetchOptions = RunPayloadQueryOptions;

function runQueryString(opts: boolean | RunFetchOptions | undefined): string {
  const o: RunFetchOptions =
    typeof opts === "boolean" ? { includePayloads: opts } : opts ?? {};
  const p = new URLSearchParams();
  if (o.includePayloads) p.set("include_payloads", "true");
  if (o.includeTransparency) p.set("include_transparency", "true");
  const s = p.toString();
  return s ? `?${s}` : "";
}

function appendIfDefined(params: URLSearchParams, key: string, value: string | number | boolean | undefined) {
  if (value === undefined || value === null || value === "") return;
  params.set(key, String(value));
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

export async function getRunTraceSummary(
  runId: string,
  options?: { stepsLimit?: number; artifactsLimit?: number; modelCallsLimit?: number },
): Promise<RunTraceShell> {
  const params = new URLSearchParams();
  appendIfDefined(params, "steps_limit", options?.stepsLimit);
  appendIfDefined(params, "artifacts_limit", options?.artifactsLimit);
  appendIfDefined(params, "model_calls_limit", options?.modelCallsLimit);
  const query = params.toString();
  return apiGet<RunTraceShell>(`/v1/runs/${runId}/trace-summary${query ? `?${query}` : ""}`);
}

/** @param options Pass ``true`` for ``include_payloads`` only, or an object for transparency flags. */
export async function listRunSteps(
  runId: string,
  options?: boolean | RunStepQueryOptions,
): Promise<RunStepDetail[]> {
  const payloadOpts: RunFetchOptions =
    typeof options === "boolean"
      ? { includePayloads: options }
      : {
          includePayloads: options?.includePayloads,
          includeTransparency: options?.includeTransparency,
        };
  const params = new URLSearchParams(runQueryString(payloadOpts).replace(/^\?/, ""));
  if (typeof options !== "boolean") {
    appendIfDefined(params, "status", options?.status);
    appendIfDefined(params, "trace", options?.trace);
    appendIfDefined(params, "q", options?.q);
    appendIfDefined(params, "limit", options?.limit);
    appendIfDefined(params, "offset", options?.offset);
  }
  const query = params.toString();
  return apiGet<RunStepDetail[]>(`/v1/runs/${runId}/steps${query ? `?${query}` : ""}`);
}

export async function getRunStep(
  runId: string,
  stepId: string,
  options?: boolean | RunFetchOptions,
): Promise<RunStepDetail> {
  const q = runQueryString(options);
  return apiGet<RunStepDetail>(`/v1/runs/${runId}/steps/${stepId}${q}`);
}

export async function listRunArtifacts(
  runId: string,
  options?: ArtifactQueryOptions,
): Promise<ArtifactMetadata[]> {
  const params = new URLSearchParams();
  appendIfDefined(params, "role_key", options?.roleKey);
  appendIfDefined(params, "kind", options?.kind);
  appendIfDefined(params, "include_deleted", options?.includeDeleted);
  appendIfDefined(params, "limit", options?.limit);
  appendIfDefined(params, "offset", options?.offset);
  const query = params.toString();
  return apiGet<ArtifactMetadata[]>(`/v1/runs/${runId}/artifacts${query ? `?${query}` : ""}`);
}

export async function listRunModelCalls(
  runId: string,
  options?: boolean | ModelCallQueryOptions,
): Promise<ModelCallApiItem[]> {
  const params = new URLSearchParams();
  if (typeof options === "boolean") {
    appendIfDefined(params, "include_payloads", options);
  } else {
    appendIfDefined(params, "include_payloads", options?.includePayloads);
    appendIfDefined(params, "status", options?.status);
    appendIfDefined(params, "prompt_id", options?.promptId);
    appendIfDefined(params, "q", options?.q);
    appendIfDefined(params, "limit", options?.limit);
    appendIfDefined(params, "offset", options?.offset);
  }
  const query = params.toString();
  return apiGet<ModelCallApiItem[]>(`/v1/runs/${runId}/model-calls${query ? `?${query}` : ""}`);
}

export async function getRunModelCall(
  runId: string,
  modelCallId: string,
  options?: boolean | { includePayloads?: boolean },
): Promise<ModelCallApiItem> {
  const params = new URLSearchParams();
  if (typeof options === "boolean") {
    appendIfDefined(params, "include_payloads", options);
  } else {
    appendIfDefined(params, "include_payloads", options?.includePayloads);
  }
  const query = params.toString();
  return apiGet<ModelCallApiItem>(
    `/v1/runs/${runId}/model-calls/${modelCallId}${query ? `?${query}` : ""}`,
  );
}

/** Per-phase token, latency, and optional cost rollup (same aggregation as ``transparency.llm_usage``). */
export async function getRunLlmUsage(runId: string): Promise<LlmRunUsageSummary> {
  return apiGet<LlmRunUsageSummary>(`/v1/runs/${runId}/llm-usage`);
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
