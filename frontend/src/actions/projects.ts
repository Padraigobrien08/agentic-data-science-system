"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { createProject } from "@/lib/api/projects";

export type CreateProjectState = { error?: string };

function parseTickers(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export async function createProjectAction(
  _prev: CreateProjectState,
  formData: FormData,
): Promise<CreateProjectState> {
  const name = String(formData.get("name") ?? "").trim();
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  if (!name) {
    return { error: "Project name is required." };
  }
  if (tickers.length === 0) {
    return { error: "Add at least one ticker (comma or newline separated)." };
  }
  try {
    const row = await createProject({ name, tickers });
    revalidatePath("/projects");
    redirect(`/projects/${row.id}/chat`);
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }
}
