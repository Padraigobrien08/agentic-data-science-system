import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ApiError } from "@/lib/api/errors";
import { getProject } from "@/lib/api/projects";

export default async function ProjectLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;

  try {
    await getProject(projectId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-4">
          <SignInHint nextPath={`/projects/${projectId}/runs`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return (
      <div className="space-y-2">
        <p className="font-mono text-sm text-red-700 dark:text-red-400">Project load failed: {msg}</p>
        {children}
      </div>
    );
  }

  return children;
}
