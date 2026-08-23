import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatTraceRail } from "@/components/chat-shell/chat-trace-rail";

const loadRunTimeline = vi.hoisted(() => vi.fn());
vi.mock("@/actions/trace", () => ({ loadRunTimeline }));

/** The shape `runTimeline` produces for a three-step pipeline run that succeeded. */
const groups = [
  {
    id: "steps-0",
    label: "steps 1–3",
    meta: "3 steps",
    entries: [
      {
        id: "a",
        glyph: "▶",
        label: "run_pipeline:AAPL,MSFT",
        accent: "run_pipeline",
        tone: "default" as const,
      },
      { id: "b", glyph: "▶", label: "critic_agent", tone: "default" as const },
      { id: "c", glyph: "▶", label: "report_agent", tone: "default" as const },
    ],
  },
];

describe("ChatTraceRail", () => {
  it("draws the run's steps once they load, and counts them", async () => {
    loadRunTimeline.mockResolvedValue({ groups });

    render(<ChatTraceRail runId="run-1" onClose={vi.fn()} />);

    expect(screen.getByText("loading…")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("3 steps")).toBeTruthy());
    expect(screen.getByText("run_pipeline:AAPL,MSFT")).toBeTruthy();
    expect(screen.getByText("critic_agent")).toBeTruthy();
    expect(loadRunTimeline).toHaveBeenCalledWith("run-1");
  });

  it("says a run recorded no steps rather than showing a blank panel", async () => {
    // Real case: runs in this database that produced an answer but logged no steps.
    loadRunTimeline.mockResolvedValue({ groups: [] });

    render(<ChatTraceRail runId="run-empty" onClose={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("No steps recorded.")).toBeTruthy());
    expect(screen.getByText("0 steps")).toBeTruthy();
  });

  it("reports a load failure instead of implying the run had nothing in it", async () => {
    loadRunTimeline.mockResolvedValue({ groups: [], error: "Could not load the trace for this run." });

    render(<ChatTraceRail runId="run-broken" onClose={vi.fn()} />);

    await waitFor(() =>
      expect(screen.getByText("Could not load the trace for this run.")).toBeTruthy(),
    );
    expect(screen.queryByText("No steps recorded.")).toBeNull();
  });

  it("loads afresh for a different run rather than showing the previous one", async () => {
    // The shell keys this by run, so opening another trace is a new mount — asserted the
    // same way here, because a reconciled remount is what the component relies on.
    loadRunTimeline.mockResolvedValue({ groups });
    const { rerender } = render(<ChatTraceRail key="run-1" runId="run-1" onClose={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("3 steps")).toBeTruthy());

    loadRunTimeline.mockResolvedValue({ groups: [] });
    rerender(<ChatTraceRail key="run-2" runId="run-2" onClose={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("0 steps")).toBeTruthy());
    expect(screen.queryByText("critic_agent")).toBeNull();
    expect(loadRunTimeline).toHaveBeenLastCalledWith("run-2");
  });
});
