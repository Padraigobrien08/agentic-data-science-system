import Link from "next/link";

import { CreateProjectForm } from "@/components/auth/create-project-form";
import { SignInHint } from "@/components/auth/sign-in-hint";
import { ApiError } from "@/lib/api/errors";
import { listProjects } from "@/lib/api/projects";
import type { ProjectRead } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ProjectsIndexPage() {
  let projects: ProjectRead[];
  try {
    projects = await listProjects();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3 text-sm">
          <h1 className="text-lg font-semibold">Projects</h1>
          <SignInHint nextPath="/projects" />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return (
      <div className="space-y-3 text-sm">
        <h1 className="text-lg font-semibold">Projects</h1>
        <p className="font-mono text-sm text-red-700 dark:text-red-400">GET /v1/projects failed: {msg}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      <div>
        <h1 className="text-lg font-semibold">Workspaces</h1>
        <p className="mt-1 max-w-prose text-xs text-[var(--muted)]">
          Each workspace has a default ticker scope; chat messages create runs in that scope.
        </p>
      </div>

      {projects.length === 0 ? (
        <p className="text-[var(--muted)]">No workspaces yet. Create one below.</p>
      ) : (
        <ul className="space-y-2">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                href={`/projects/${p.id}/chat`}
                className="font-mono text-sm underline decoration-dotted"
                title={p.id}
              >
                {p.name}
              </Link>
              {p.tickers?.length ? (
                <span className="ml-2 text-[10px] text-[var(--muted)]">
                  {p.tickers.join(", ")}
                </span>
              ) : null}
              <span className="ml-2 text-[10px] text-[var(--muted)]">{formatDate(p.created_at)}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded border border-[var(--border)] p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          New workspace
        </h2>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Pick tickers once; then use workspace chat to submit analysis questions.
        </p>
        <div className="mt-3">
          <CreateProjectForm />
        </div>
      </div>
    </div>
  );
}
