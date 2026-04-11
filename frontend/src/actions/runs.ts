"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { createRun, executeRun } from "@/lib/api/runs";

function parseTickers(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export async function createAnalysisRunForm(
  projectId: string,
  _prev: { error?: string },
  formData: FormData,
): Promise<{ error?: string }> {
  const goal = String(formData.get("goal") ?? "").trim();
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  const refresh = formData.get("refresh") === "on";
  const executeNow = formData.get("execute_now") === "on";
  const enqueueExecution = formData.get("enqueue_execution") === "on";

  if (!goal) {
    return { error: "Analysis goal is required." };
  }

  if (executeNow && enqueueExecution) {
    return {
      error:
        "Choose either “Execute now” (synchronous) or “Queue for worker”, not both.",
    };
  }

  let run;
  try {
    run = await createRun({
      project_id: projectId,
      orchestration_goal_text: goal,
      input_payload_json: {
        tickers,
        analysis_goal: goal,
        refresh,
      },
      enqueue_execution: enqueueExecution,
    });
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }

  if (executeNow && !enqueueExecution) {
    try {
      await executeRun(run.id, {});
    } catch (e) {
      if (e instanceof ApiError) {
        return { error: e.body || e.message };
      }
      return { error: e instanceof Error ? e.message : "Execution failed." };
    }
  }

  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${run.id}`);
  redirect(`/projects/${projectId}/runs/${run.id}`);
}

export async function executeAnalysisRunAction(projectId: string, runId: string) {
  await executeRun(runId, {});
  revalidatePath(`/projects/${projectId}/runs`);
  revalidatePath(`/projects/${projectId}/runs/${runId}`);
  revalidatePath(`/projects/${projectId}/runs/${runId}/trace`);
  redirect(`/projects/${projectId}/runs/${runId}`);
}
