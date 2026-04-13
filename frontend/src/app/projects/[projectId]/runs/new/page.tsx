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
          <h1 className="text-lg font-semibold tracking-tight text-[var(--foreground)]">Advanced run</h1>
          <p className="mt-1 max-w-prose text-sm text-[var(--muted)]">
            Use workspace chat for normal queries. This page is for overriding tickers and execution options.
          </p>
        </div>
        <Link href={`/projects/${projectId}/runs`} className="text-sm text-[var(--muted)] underline">
          ← Runs
        </Link>
      </div>
      <NewRunForm projectId={projectId} />
    </div>
  );
}
