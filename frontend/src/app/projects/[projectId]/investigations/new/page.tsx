import Link from "next/link";

import { NewInvestigationForm } from "@/components/investigations/new-investigation-form";
import { agenticEngineEnabled } from "@/lib/api/investigations";

export const dynamic = "force-dynamic";

export default async function NewInvestigationPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;
  const enabled = await agenticEngineEnabled();

  return (
    <div className="mx-auto max-w-2xl space-y-5 p-4">
      <Link
        href={`/projects/${projectId}/investigations`}
        className="text-sm text-neutral-500 underline dark:text-neutral-400"
      >
        ← All investigations
      </Link>
      <div>
        <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          New investigation
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Give the agent a goal and a dataset. It generates hypotheses, runs deterministic
          experiments, weighs the evidence, and concludes — all inspectable afterwards.
        </p>
      </div>

      {enabled ? (
        <NewInvestigationForm projectId={projectId} />
      ) : (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300">
          The agentic investigation engine is disabled on this server. An operator can enable it by
          setting <code className="font-mono">EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true</code> on the
          api (and worker) processes.
        </div>
      )}
    </div>
  );
}
