"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { createProject } from "@/lib/api/projects";

export type CreateProjectState = { error?: string };

export async function createProjectAction(
  _prev: CreateProjectState,
  formData: FormData,
): Promise<CreateProjectState> {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { error: "Project name is required." };
  }
  try {
    const row = await createProject({ name });
    revalidatePath("/projects");
    redirect(`/projects/${row.id}/runs`);
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }
}
