import "server-only";

import { listProjects } from "@/lib/api/projects";
import type { CurrentUser } from "@/lib/api/types";

/**
 * Project used for “start analysis” from the landing page: env default if valid, else first project.
 */
export async function resolveLandingProjectId(user: CurrentUser | null): Promise<string | null> {
  if (!user) return null;
  const envId = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim() ?? "";
  try {
    const projects = await listProjects();
    if (envId && projects.some((p) => p.id === envId)) {
      return envId;
    }
    return projects[0]?.id ?? null;
  } catch {
    return envId || null;
  }
}
