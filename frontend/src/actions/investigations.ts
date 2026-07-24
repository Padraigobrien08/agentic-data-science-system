"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createInvestigation } from "@/lib/api/investigations";
import { ApiError } from "@/lib/api/errors";

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
  const csv = String(formData.get("csv") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim() || "dataset";
  const timeField = String(formData.get("time_field") ?? "").trim();
  const entityFields = parseList(String(formData.get("entity_id_fields") ?? ""));

  if (!goal) return { error: "Describe what you want the investigation to answer." };
  if (!csv) return { error: "Paste a small CSV dataset (a header row plus data rows)." };

  let created;
  try {
    created = await createInvestigation({
      project_id: projectId,
      goal,
      dataset: {
        format: "csv",
        csv_text: csv,
        name,
        time_field: timeField || null,
        entity_id_fields: entityFields,
      },
    });
  } catch (e) {
    if (e instanceof ApiError) return { error: e.body || e.message };
    return { error: e instanceof Error ? e.message : "Request failed." };
  }

  // Outside try/catch: redirect() throws a control-flow signal that must not be swallowed.
  revalidatePath(`/projects/${projectId}/investigations`);
  redirect(`/projects/${projectId}/investigations/${created.investigation_id}`);
}
