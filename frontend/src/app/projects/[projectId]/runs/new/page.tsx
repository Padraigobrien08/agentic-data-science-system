import Link from "next/link";

import { NewRunForm } from "@/components/runs/new-run-form";

export default async function NewRunPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Submit analysis run</h1>
          <p className="mt-1 max-w-prose text-sm text-[var(--muted)]">
            Create an analysis run and optionally trigger execution against the FastAPI backend.
          </p>
        </div>
        <Link
          href={`/projects/${projectId}/runs`}
          className="font-mono text-sm underline"
        >
          ← Runs list
        </Link>
      </div>
      <NewRunForm projectId={projectId} />
    </div>
  );
}
