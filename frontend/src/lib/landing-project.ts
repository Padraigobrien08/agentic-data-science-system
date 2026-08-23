import "server-only";

import { listProjects } from "@/lib/api/projects";
import type { CurrentUser, ProjectRead } from "@/lib/api/types";

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

const hasScope = (p: ProjectRead) => (p.tickers?.length ?? 0) > 0;

/**
 * Like the above, but prefers a project the chat composer can actually run in.
 *
 * A chat with no tickers refuses every prompt — `startAnalysisRun` rejects an empty scope
 * before it does any work. Picking merely the *first* project is how someone arriving with a
 * question lands in the one workspace that cannot answer it, which was observable: an
 * account whose first project was a scope-less recording workspace, while the next one along
 * was configured and ready.
 *
 * Falls back to the plain resolution when nothing has scope, so the destination is still a
 * real workspace — the scope editor is there, and the composer names what is missing.
 */
export async function resolveRunnableProjectId(user: CurrentUser | null): Promise<string | null> {
  if (!user) return null;
  const envId = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim() ?? "";
  try {
    const projects = await listProjects();
    const configured = projects.find((p) => p.id === envId && hasScope(p));
    return (configured ?? projects.find(hasScope))?.id ?? (await resolveLandingProjectId(user));
  } catch {
    return resolveLandingProjectId(user);
  }
}
