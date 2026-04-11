import "server-only";

import { apiGet, apiPost } from "./client";
import type { ProjectRead } from "./types";

export async function listProjects(): Promise<ProjectRead[]> {
  return apiGet<ProjectRead[]>("/v1/projects");
}

export async function getProject(projectId: string): Promise<ProjectRead> {
  return apiGet<ProjectRead>(`/v1/projects/${projectId}`);
}

export async function createProject(body: { name: string }): Promise<ProjectRead> {
  return apiPost<ProjectRead>("/v1/projects", { name: body.name });
}
