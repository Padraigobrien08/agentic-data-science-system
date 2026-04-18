"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { createRun, executeRun, getPromptRoutingPreview } from "@/lib/api/runs";

type DeliveryMode = "sync_only" | "background_ready" | "background_degraded";

type ChatReply = {
  requestId: string;
  content: string;
  runId?: string;
  runHref?: string;
  deepDiveHref?: string;
  runsHref?: string;
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
    return { error: "This workspace has no tickers configured. Add tickers in workspace settings." };
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
          routingReason: preview.reason ?? undefined,
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
  try {
    execution = await executeRun(run.id, {});
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Execution failed." };
  }

  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${run.id}`);
  revalidatePath(`/projects/${projectId}/runs/${run.id}/trace`);
  const deliveryMode: DeliveryMode = "sync_only";
  const deliveryDetail = reroutedFromBackground
    ? "Background delivery was rerouted to immediate execution for this chat request."
    : "Workspace chat is executing synchronously right now.";
  const content =
    execution.db_status === "error"
      ? `Run finished with an error for ${effectiveTickers.join(", ")}. Open run answer or deep dive for details.`
      : `Analysis completed for ${effectiveTickers.join(", ")}. Open run answer or deep dive when ready.`;
  return {
    reply: {
      requestId,
      runId: run.id,
      runHref: `/projects/${projectId}/runs/${run.id}`,
      deepDiveHref: `/projects/${projectId}/runs/${run.id}/trace`,
      runsHref: `/projects/${projectId}/runs`,
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
