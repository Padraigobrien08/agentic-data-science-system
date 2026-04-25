"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { parseAiAgents } from "@/lib/ai-agents-meta";
import { ApiError } from "@/lib/api/errors";
import type { AnalysisRunStatus } from "@/lib/api/types";
import { createRun, executeRun, getPromptRoutingPreview, getRun, listRunArtifacts } from "@/lib/api/runs";
import { parseOrchestrationOutput, parseUserFacingReport } from "@/lib/orchestration-output";
import { buildChatAnswerCardView, buildPrimaryAnswerView, type ChatAnswerCardView } from "@/lib/run-primary-view";

type DeliveryMode = "sync_only" | "background_ready" | "background_degraded";

type ChatReply = {
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

export async function createAnalysisRunFromChat(
  projectId: string,
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
      return {
        reply: {
          requestId,
          content: "I couldn't route that request yet.",
          rewriteSuggestions: preview.rewrite_suggestions,
          routingReason: normalizeRoutingReason(preview.reason),
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

export async function executeAnalysisRunAction(projectId: string, runId: string) {
  await executeRun(runId, {});
  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${runId}`);
  revalidatePath(`/projects/${projectId}/runs/${runId}/trace`);
  redirect(`/projects/${projectId}/runs/${runId}`);
}
