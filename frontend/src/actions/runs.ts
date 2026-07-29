"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { parseAiAgents } from "@/lib/ai-agents-meta";
import { appendChatMessage } from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/errors";
import type { AnalysisRunStatus, ChatMessageCreateBody } from "@/lib/api/types";
import {
  cancelRun,
  createRun,
  executeRun,
  getPromptRoutingPreview,
  getRun,
  listRunArtifacts,
  listRunSteps,
} from "@/lib/api/runs";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { derivePipelinePhaseView, type PipelinePhaseView } from "@/lib/run-pipeline-phases";
import { buildChatAnswerCardView, buildPrimaryAnswerView, type ChatAnswerCardView } from "@/lib/run-primary-view";

type DeliveryMode = "sync_only" | "background_ready" | "background_degraded";

export type ChatReply = {
  requestId: string;
  content: string;
  runId?: string;
  runHref?: string;
  answerCard?: ChatAnswerCardView;
  runStatus?: AnalysisRunStatus;
  runCreatedAt?: string;
  runFinishedAt?: string | null;
  deliveryMode?: DeliveryMode;
  deliveryDetail?: string;
  reroutedFromBackground?: boolean;
  rewriteSuggestions?: string[];
  routingReason?: string;
};

function parseTickers(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function normalizeRoutingReason(reason: string | null | undefined): string | undefined {
  if (!reason) return undefined;
  return reason.replace(/workspace scope/g, "chat scope");
}

/**
 * Best-effort durable persistence of a chat turn. Failures never break the reply —
 * the optimistic client state already reflects the exchange, and history is a
 * projection that can tolerate a dropped write.
 */
async function persistMessage(
  conversationId: string | undefined,
  body: ChatMessageCreateBody,
): Promise<void> {
  if (!conversationId) return;
  try {
    await appendChatMessage(conversationId, body);
  } catch {
    // Swallow — durability is secondary to returning the answer.
  }
}

export async function createAnalysisRunFromChat(
  projectId: string,
  conversationId: string | undefined,
  _prev: {
    error?: string;
    reply?: ChatReply;
  },
  formData: FormData,
): Promise<{
  error?: string;
  reply?: ChatReply;
}> {
  const goal = String(formData.get("goal") ?? "").trim();
  const requestId = String(formData.get("request_id") ?? "").trim() || "local";
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  const refresh = formData.get("refresh") === "on";
  const reroutedFromBackground = formData.get("enqueue_execution") === "on";

  if (!goal) {
    return { error: "Analysis goal is required." };
  }
  if (tickers.length === 0) {
    return { error: "This chat has no tickers configured. Add tickers in the scope editor." };
  }

  // Record the user turn durably before doing any work.
  await persistMessage(conversationId, {
    role: "user",
    content: goal,
    status: "complete",
    client_request_id: requestId,
  });

  let run;
  let effectiveTickers = tickers;
  try {
    const preview = await getPromptRoutingPreview({
      project_id: projectId,
      analysis_goal: goal,
      tickers,
      refresh,
    });
    if (!preview.supported) {
      const routingReason = normalizeRoutingReason(preview.reason);
      const content = "I couldn't route that request yet.";
      await persistMessage(conversationId, {
        role: "assistant",
        content,
        status: "complete",
        client_request_id: requestId,
        meta_json: {
          routing_reason: routingReason ?? null,
          rewrite_suggestions: preview.rewrite_suggestions ?? [],
        },
      });
      revalidatePath(`/projects/${projectId}/chat`);
      return {
        reply: {
          requestId,
          content,
          rewriteSuggestions: preview.rewrite_suggestions,
          routingReason,
        },
      };
    }

    effectiveTickers = preview.effective_tickers;
    run = await createRun({
      project_id: projectId,
      orchestration_goal_text: goal,
      input_payload_json: {
        tickers: effectiveTickers,
        analysis_goal: goal,
        refresh,
      },
      enqueue_execution: false,
    });
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }

  let execution;
  let hydratedRun;
  let artifacts;
  try {
    execution = await executeRun(run.id, {});
    [hydratedRun, artifacts] = await Promise.all([
      getRun(run.id, { includeTransparency: true }),
      listRunArtifacts(run.id),
    ]);
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Execution failed." };
  }

  const orch = parseOrchestrationOutput(hydratedRun.output_payload_json);
  const userReport = parseUserFacingReport(hydratedRun.output_payload_json);
  const ai = parseAiAgents(hydratedRun.meta_json);
  const nav = {
    projectId,
    runId: run.id,
  };
  const answerView = buildPrimaryAnswerView(
    hydratedRun,
    artifacts,
    orch,
    userReport,
    ai,
    hydratedRun.transparency,
    nav,
  );
  const answerCard = buildChatAnswerCardView(answerView, nav);

  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${run.id}`);
  revalidatePath(`/projects/${projectId}/runs/${run.id}/trace`);
  const deliveryMode: DeliveryMode = "sync_only";
  const deliveryDetail = reroutedFromBackground
    ? "Background delivery was rerouted to immediate execution for this chat request."
    : "This chat is executing synchronously right now.";
  const content =
    answerCard.narrativeAnswer.thesis ??
    answerCard.emptyStateReason ??
    (execution.db_status === "error"
      ? `Run finished with an error for ${effectiveTickers.join(", ")}.`
      : `Analysis completed for ${effectiveTickers.join(", ")}.`);

  // Record the assistant turn durably, linked to the run that produced it.
  await persistMessage(conversationId, {
    role: "assistant",
    content,
    status: hydratedRun.status === "error" ? "error" : "complete",
    client_request_id: requestId,
    analysis_run_id: run.id,
    error_summary: hydratedRun.error_summary ?? null,
    meta_json: { delivery_mode: deliveryMode },
  });
  revalidatePath(`/projects/${projectId}/chat`);
  if (conversationId) {
    revalidatePath(`/projects/${projectId}/chat/${conversationId}`);
  }

  return {
    reply: {
      requestId,
      runId: run.id,
      runHref: `/projects/${projectId}/runs/${run.id}/trace`,
      answerCard,
      runStatus: hydratedRun.status,
      runCreatedAt: hydratedRun.created_at,
      runFinishedAt: hydratedRun.finished_at,
      content,
      deliveryMode,
      deliveryDetail,
      reroutedFromBackground,
    },
  };
}

/**
 * Phase 1 of the live-progress send: route the prompt and create the run (not executed
 * yet), so the client gets a runId to poll while phase 2 executes. Persists the user turn.
 */
export async function startAnalysisRun(
  projectId: string,
  conversationId: string | undefined,
  args: { goal: string; tickers: string[]; requestId: string; refresh?: boolean },
): Promise<{ error?: string; reply?: ChatReply; runId?: string }> {
  const goal = args.goal.trim();
  const requestId = args.requestId || "local";
  const tickers = args.tickers;
  const refresh = args.refresh ?? false;

  if (!goal) return { error: "Analysis goal is required." };
  if (tickers.length === 0) {
    return { error: "This chat has no tickers configured. Add tickers in the scope editor." };
  }

  await persistMessage(conversationId, {
    role: "user",
    content: goal,
    status: "complete",
    client_request_id: requestId,
  });

  try {
    const preview = await getPromptRoutingPreview({
      project_id: projectId,
      analysis_goal: goal,
      tickers,
      refresh,
    });
    if (!preview.supported) {
      const routingReason = normalizeRoutingReason(preview.reason);
      const content = "I couldn't route that request yet.";
      await persistMessage(conversationId, {
        role: "assistant",
        content,
        status: "complete",
        client_request_id: requestId,
        meta_json: {
          routing_reason: routingReason ?? null,
          rewrite_suggestions: preview.rewrite_suggestions ?? [],
        },
      });
      revalidatePath(`/projects/${projectId}/chat`);
      return { reply: { requestId, content, rewriteSuggestions: preview.rewrite_suggestions, routingReason } };
    }

    const run = await createRun({
      project_id: projectId,
      orchestration_goal_text: goal,
      input_payload_json: { tickers: preview.effective_tickers, analysis_goal: goal, refresh },
      enqueue_execution: false,
    });
    return { runId: run.id };
  } catch (e) {
    if (e instanceof ApiError) return { error: e.body || e.message };
    return { error: e instanceof Error ? e.message : "Request failed." };
  }
}

/**
 * Best-effort cancel. Records intent so the run can abort at its next status check;
 * a run already inside the executor finishes server-side, but the client stops waiting.
 */
export async function cancelAnalysisRun(runId: string): Promise<void> {
  try {
    await cancelRun(runId);
  } catch {
    // Swallow — the client has already stopped waiting; cancel is a courtesy.
  }
}

/** Live progress poll — real pipeline phases derived from the run's committed steps. */
export async function getRunProgress(
  runId: string,
): Promise<{ status: AnalysisRunStatus; view: PipelinePhaseView } | null> {
  try {
    const [run, steps] = await Promise.all([getRun(runId), listRunSteps(runId)]);
    return { status: run.status, view: derivePipelinePhaseView(run.status, steps) };
  } catch {
    return null;
  }
}

/**
 * Phase 2: execute the run to completion (blocking), then build + persist the answer.
 * The client awaits this for the final answer while polling getRunProgress meanwhile.
 */
export async function finalizeAnalysisRun(
  projectId: string,
  conversationId: string | undefined,
  args: { runId: string; requestId: string; tickers: string[] },
): Promise<{ error?: string; reply?: ChatReply }> {
  const { runId, requestId } = args;
  let execution;
  let hydratedRun;
  let artifacts;
  try {
    execution = await executeRun(runId, {});
    [hydratedRun, artifacts] = await Promise.all([
      getRun(runId, { includeTransparency: true }),
      listRunArtifacts(runId),
    ]);
  } catch (e) {
    if (e instanceof ApiError) return { error: e.body || e.message };
    return { error: e instanceof Error ? e.message : "Execution failed." };
  }

  const orch = parseOrchestrationOutput(hydratedRun.output_payload_json);
  const userReport = parseUserFacingReport(hydratedRun.output_payload_json);
  const ai = parseAiAgents(hydratedRun.meta_json);
  const nav = { projectId, runId };
  const answerView = buildPrimaryAnswerView(
    hydratedRun,
    artifacts,
    orch,
    userReport,
    ai,
    hydratedRun.transparency,
    nav,
  );
  const answerCard = buildChatAnswerCardView(answerView, nav);

  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${runId}`);
  revalidatePath(`/projects/${projectId}/runs/${runId}/trace`);
  const deliveryMode: DeliveryMode = "sync_only";
  const deliveryDetail = "This chat executed the analysis live.";
  const content =
    answerCard.narrativeAnswer.thesis ??
    answerCard.emptyStateReason ??
    (execution.db_status === "error"
      ? `Run finished with an error for ${args.tickers.join(", ")}.`
      : `Analysis completed for ${args.tickers.join(", ")}.`);

  await persistMessage(conversationId, {
    role: "assistant",
    content,
    status: hydratedRun.status === "error" ? "error" : "complete",
    client_request_id: requestId,
    analysis_run_id: runId,
    error_summary: hydratedRun.error_summary ?? null,
    meta_json: { delivery_mode: deliveryMode },
  });
  revalidatePath(`/projects/${projectId}/chat`);
  if (conversationId) revalidatePath(`/projects/${projectId}/chat/${conversationId}`);

  return {
    reply: {
      requestId,
      runId,
      runHref: `/projects/${projectId}/runs/${runId}/trace`,
      answerCard,
      runStatus: hydratedRun.status,
      runCreatedAt: hydratedRun.created_at,
      runFinishedAt: hydratedRun.finished_at,
      content,
      deliveryMode,
      deliveryDetail,
    },
  };
}

export async function executeAnalysisRunAction(projectId: string, runId: string) {
  await executeRun(runId, {});
  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${runId}`);
  revalidatePath(`/projects/${projectId}/runs/${runId}/trace`);
  redirect(`/projects/${projectId}/runs/${runId}`);
}
