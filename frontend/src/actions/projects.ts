"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { createProject, updateProject } from "@/lib/api/projects";

export type CreateProjectState = { error?: string };
export type UpdateScopeState = { error?: string; saved?: boolean; tickers?: string[] };

function parseTickers(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function buildConversationName(tickers: string[]): string {
  if (tickers.length === 1) {
    return `${tickers[0]} chat`;
  }
  if (tickers.length === 2) {
    return `${tickers[0]} + ${tickers[1]} chat`;
  }
  if (tickers.length > 2) {
    return `${tickers[0]} + ${tickers.length - 1} more`;
  }
  return "New chat";
}

export async function createProjectAction(
  _prev: CreateProjectState,
  formData: FormData,
): Promise<CreateProjectState> {
  const name = String(formData.get("name") ?? "").trim();
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  if (tickers.length === 0) {
    return { error: "Add at least one ticker (comma or newline separated)." };
  }
  try {
    const row = await createProject({ name: name || buildConversationName(tickers), tickers });
    revalidatePath("/projects");
    redirect(`/projects/${row.id}/chat`);
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }
}

export async function updateWorkspaceScopeAction(
  projectId: string,
  _prev: UpdateScopeState,
  formData: FormData,
): Promise<UpdateScopeState> {
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  if (tickers.length === 0) {
    return { error: "Add at least one ticker (comma or newline separated)." };
  }
  try {
    const row = await updateProject(projectId, { tickers });
    revalidatePath(`/projects/${projectId}/chat`);
    revalidatePath(`/projects/${projectId}/runs`);
    return { saved: true, tickers: row.tickers ?? tickers };
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: e.body || e.message };
    }
    return { error: e instanceof Error ? e.message : "Request failed." };
  }
}

export async function startConversationFromScopeAction(projectId: string, formData: FormData) {
  const tickers = parseTickers(String(formData.get("tickers") ?? ""));
  if (tickers.length === 0) {
    redirect(`/projects/${projectId}/chat`);
  }

  const row = await createProject({
    name: buildConversationName(tickers),
    tickers,
  });
  revalidatePath("/projects");
  redirect(`/projects/${row.id}/chat`);
}
