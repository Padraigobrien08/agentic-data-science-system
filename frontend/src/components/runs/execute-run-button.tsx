"use client";

import { useTransition } from "react";

import { executeAnalysisRunAction } from "@/actions/runs";

type Props = {
  projectId: string;
  runId: string;
  /** Button label when idle (default: Execute pipeline). */
  actionLabel?: string;
  size?: "default" | "compact";
};

export function ExecuteRunButton({ projectId, runId, actionLabel, size = "default" }: Props) {
  const [pending, start] = useTransition();
  const idle = actionLabel ?? "Execute pipeline";
  const pad = size === "compact" ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm";

  return (
    <button
      type="button"
      disabled={pending}
      aria-busy={pending}
      onClick={() => start(() => executeAnalysisRunAction(projectId, runId))}
      className={`shrink-0 rounded border border-[var(--border)] bg-[var(--foreground)] font-medium text-[var(--background)] disabled:opacity-50 ${pad}`}
    >
      {pending ? "Starting…" : idle}
    </button>
  );
}
