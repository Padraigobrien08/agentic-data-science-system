"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";

import { loadRunTimeline } from "@/actions/trace";
import { TraceTimeline } from "@/components/trace/trace-timeline";
import type { TimelineGroup } from "@/lib/trace-timeline";

const MONO = "font-mono text-[11px]";

/**
 * The trace for one live run, docked beside the conversation.
 *
 * Same component and same vocabulary the replay tier docks for a recorded investigation —
 * the two surfaces should not teach a reader two ways to read a trace. Loaded on open rather
 * than with the conversation, and failing to a message rather than to an empty panel.
 */
export function ChatTraceRail({
  runId,
  fullTraceHref,
  onClose,
}: Readonly<{ runId: string; fullTraceHref?: string; onClose: () => void }>) {
  const [state, setState] = useState<{
    status: "loading" | "ready";
    groups: TimelineGroup[];
    error?: string;
  }>({ status: "loading", groups: [] });

  // No reset on `runId` change: the shell keys this component by run, so a different run is
  // a different mount and the initial loading state is already correct. Resetting here would
  // be a synchronous setState in an effect — a cascading render for no gain.
  useEffect(() => {
    let live = true;
    void loadRunTimeline(runId).then((result) => {
      if (live) setState({ status: "ready", ...result });
    });
    return () => {
      live = false;
    };
  }, [runId]);

  const stepCount = state.groups.reduce((n, g) => n + g.entries.length, 0);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-[-0.01em] text-[var(--foreground)]">
            The trace
          </p>
          <p className={`mt-0.5 ${MONO} truncate text-[var(--chat-faint)]`}>
            {state.status === "loading"
              ? "loading…"
              : `${stepCount} step${stepCount === 1 ? "" : "s"}`}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close trace"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control text-[var(--chat-faint)] transition-colors hover:bg-[var(--chat-hover)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {state.error ? (
        <p className={`${MONO} text-[color:var(--status-danger-ink)]`}>{state.error}</p>
      ) : (
        <TraceTimeline
          groups={state.groups}
          emptyLabel={state.status === "loading" ? "Loading the trace…" : "No steps recorded."}
        />
      )}

      {fullTraceHref ? (
        <Link href={fullTraceHref} className={`${MONO} block text-[var(--accent)] hover:underline`}>
          full record →
        </Link>
      ) : null}
    </div>
  );
}
