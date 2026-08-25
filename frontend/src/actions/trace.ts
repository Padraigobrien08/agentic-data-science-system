"use server";

import { listRunSteps } from "@/lib/api/runs";
import { runTimeline, type TimelineGroup } from "@/lib/trace-timeline";

/**
 * The steps behind one run, shaped for the shared trace timeline.
 *
 * A server action rather than a route handler because the JWT never leaves the server
 * (`frontend/src/lib/api/`), and rather than eager loading because a conversation can hold a
 * dozen answers and almost nobody opens a dozen traces — the cost belongs on the reader who
 * asks for it.
 */
export async function loadRunTimeline(
  runId: string,
): Promise<{ groups: TimelineGroup[]; error?: string }> {
  try {
    return { groups: runTimeline(await listRunSteps(runId)) };
  } catch {
    // The rail is a supplement; a failure here must not take the conversation with it.
    return { groups: [], error: "Could not load the trace for this run." };
  }
}
