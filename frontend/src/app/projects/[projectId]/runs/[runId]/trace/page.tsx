import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { AgenticTraceView } from "@/components/trace/agentic-trace-view";
import { ApiError } from "@/lib/api/errors";
import { getRun, listRunArtifacts, listRunModelCalls, listRunSteps } from "@/lib/api/runs";
import { parseUserFacingReport } from "@/lib/orchestration-output";

export const dynamic = "force-dynamic";

export default async function RunTracePage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
}>) {
  const { projectId, runId } = await params;
  let run;
  let steps;
  let artifacts;
  let modelCalls;
  try {
    [run, steps, artifacts, modelCalls] = await Promise.all([
      getRun(runId, true),
      listRunSteps(runId, true),
      listRunArtifacts(runId),
      listRunModelCalls(runId, false),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Full trace</h1>
          <SignInHint nextPath={`/projects/${projectId}/runs/${runId}/trace`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="font-mono text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  if (run.project_id !== projectId) {
    notFound();
  }

  const userReport = parseUserFacingReport(run.output_payload_json);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Full trace</h1>
          <p className="mt-1 max-w-prose text-xs text-[var(--muted)]">
            Planner, tools, agents, persisted steps, and artifact metadata for this run.
          </p>
        </div>
        <Link
          href={`/projects/${projectId}/runs/${runId}`}
          className="font-mono text-sm underline"
        >
          ← Run detail
        </Link>
      </div>
      <p className="font-mono text-xs text-[var(--muted)] break-all">{runId}</p>
      <AgenticTraceView
        projectId={projectId}
        runId={runId}
        outputPayload={run.output_payload_json}
        metaJson={run.meta_json}
        steps={steps}
        artifacts={artifacts}
        modelCalls={modelCalls}
        userFacingReport={userReport}
        compactTraceLink
      />
    </div>
  );
}
