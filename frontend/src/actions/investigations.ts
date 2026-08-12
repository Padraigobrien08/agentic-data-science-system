"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createInvestigation } from "@/lib/api/investigations";
import { ApiError } from "@/lib/api/errors";
import type { InvestigationDatasetInput } from "@/lib/api/types";

export type CreateInvestigationState = { error?: string };

function parseList(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export async function createInvestigationAction(
  projectId: string,
  _prev: CreateInvestigationState,
  formData: FormData,
): Promise<CreateInvestigationState> {
  const goal = String(formData.get("goal") ?? "").trim();
  const source = String(formData.get("source") ?? "tabular").trim() === "edgar" ? "edgar" : "tabular";

  if (!goal) return { error: "Describe what you want the investigation to answer." };

  let dataset: InvestigationDatasetInput;
  let background = formData.get("background") != null;

  if (source === "edgar") {
    const entities = parseList(String(formData.get("entities") ?? "")).map((t) => t.toUpperCase());
    if (entities.length === 0) {
      return { error: "Enter at least one ticker symbol (for example AAPL, MSFT)." };
    }
    dataset = { source: "edgar", entities, refresh: formData.get("refresh") != null };
    // EDGAR builds its panel from live SEC fetches before the loop starts, which is far too
    // slow to hold a request open for. Background is not a preference here.
    background = true;
  } else {
    const csv = String(formData.get("csv") ?? "").trim();
    if (!csv) return { error: "Paste or upload a small CSV dataset (a header row plus data rows)." };
    dataset = {
      source: "tabular",
      format: "csv",
      csv_text: csv,
      name: String(formData.get("name") ?? "").trim() || "dataset",
      time_field: String(formData.get("time_field") ?? "").trim() || null,
      entity_id_fields: parseList(String(formData.get("entity_id_fields") ?? "")),
    };
  }

  let created;
  try {
    created = await createInvestigation({
      project_id: projectId,
      goal,
      async_execution: background,
      dataset,
    });
  } catch (e) {
    if (e instanceof ApiError) return { error: e.body || e.message };
    return { error: e instanceof Error ? e.message : "Request failed." };
  }

  // Outside try/catch: redirect() throws a control-flow signal that must not be swallowed.
  revalidatePath(`/projects/${projectId}/investigations`);
  if (created.queued || !created.investigation_id) {
    redirect(`/projects/${projectId}/investigations/pending/${created.analysis_run_id}`);
  }
  redirect(`/projects/${projectId}/investigations/${created.investigation_id}`);
}
