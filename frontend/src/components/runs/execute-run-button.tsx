"use client";

import { useTransition } from "react";

import { executeAnalysisRunAction } from "@/actions/runs";

type Props = {
  projectId: string;
  runId: string;
};

export function ExecuteRunButton({ projectId, runId }: Props) {
  const [pending, start] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      aria-busy={pending}
      onClick={() => start(() => executeAnalysisRunAction(projectId, runId))}
      className="rounded border border-[var(--border)] bg-[var(--foreground)] px-3 py-1.5 text-sm text-[var(--background)] disabled:opacity-50"
    >
      {pending ? "Starting…" : "Execute pipeline"}
    </button>
  );
}
