/**
 * The unified entry routes one form to two adapters.
 *
 * Both sources produce the same kind of investigation — same loop, same evidence model, same
 * trace — so the only thing that differs is the dataset body the action builds. These pin that
 * mapping, and the one behaviour that is not a user preference: EDGAR always runs in the
 * background, because its panel is built from live SEC fetches before the loop starts.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { createInvestigationMock, revalidatePathMock, redirectMock } = vi.hoisted(() => ({
  createInvestigationMock: vi.fn(),
  revalidatePathMock: vi.fn(),
  redirectMock: vi.fn(() => {
    // The real redirect() throws a control-flow signal; mimic it so code after it does not run.
    throw new Error("NEXT_REDIRECT");
  }),
}));

vi.mock("next/cache", () => ({ revalidatePath: revalidatePathMock }));
vi.mock("next/navigation", () => ({ redirect: redirectMock }));
vi.mock("@/lib/api/investigations", () => ({ createInvestigation: createInvestigationMock }));

import { createInvestigationAction } from "@/actions/investigations";

const PROJECT = "11111111-1111-1111-1111-111111111111";

function form(fields: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.set(k, v);
  return fd;
}

async function submit(fields: Record<string, string>) {
  try {
    return await createInvestigationAction(PROJECT, {}, form(fields));
  } catch (e) {
    if (e instanceof Error && e.message === "NEXT_REDIRECT") return { redirected: true };
    throw e;
  }
}

beforeEach(() => {
  vi.clearAllMocks();
  createInvestigationMock.mockResolvedValue({
    analysis_run_id: "run-1",
    status: "converged",
    db_status: "success",
    investigation_id: "inv-1",
    queued: false,
  });
});

describe("edgar source", () => {
  it("sends normalised tickers and forces background execution", async () => {
    await submit({ goal: "has margin fallen?", source: "edgar", entities: "aapl, msft" });

    const body = createInvestigationMock.mock.calls[0][0];
    expect(body.dataset).toEqual({ source: "edgar", entities: ["AAPL", "MSFT"], refresh: false });
    // Not a preference: an EDGAR panel is built from live SEC fetches before the loop starts.
    expect(body.async_execution).toBe(true);
  });

  it("ignores a background checkbox rather than honouring a foreground request", async () => {
    await submit({ goal: "g", source: "edgar", entities: "AAPL" });
    expect(createInvestigationMock.mock.calls[0][0].async_execution).toBe(true);
  });

  it("passes refresh through when asked", async () => {
    await submit({ goal: "g", source: "edgar", entities: "AAPL", refresh: "on" });
    expect(createInvestigationMock.mock.calls[0][0].dataset.refresh).toBe(true);
  });

  it("splits tickers on commas and newlines", async () => {
    await submit({ goal: "g", source: "edgar", entities: "aapl\nmsft, nvda" });
    expect(createInvestigationMock.mock.calls[0][0].dataset.entities).toEqual([
      "AAPL",
      "MSFT",
      "NVDA",
    ]);
  });

  it("refuses an empty ticker list without calling the API", async () => {
    const result = await submit({ goal: "g", source: "edgar", entities: "  , ," });
    expect(result).toEqual({ error: expect.stringContaining("ticker") });
    expect(createInvestigationMock).not.toHaveBeenCalled();
  });
});

describe("tabular source", () => {
  it("sends the pasted CSV and respects the background choice", async () => {
    await submit({
      goal: "are sales trending up?",
      source: "tabular",
      csv: "a,b\n1,2",
      name: "sales",
      time_field: "week",
      entity_id_fields: "store, region",
    });

    const body = createInvestigationMock.mock.calls[0][0];
    expect(body.dataset).toEqual({
      source: "tabular",
      format: "csv",
      csv_text: "a,b\n1,2",
      name: "sales",
      time_field: "week",
      entity_id_fields: ["store", "region"],
    });
    expect(body.async_execution).toBe(false);
  });

  it("is the default when no source is supplied", async () => {
    await submit({ goal: "g", csv: "a,b\n1,2" });
    expect(createInvestigationMock.mock.calls[0][0].dataset.source).toBe("tabular");
  });

  it("opts into background when the box is ticked", async () => {
    await submit({ goal: "g", csv: "a,b\n1,2", background: "on" });
    expect(createInvestigationMock.mock.calls[0][0].async_execution).toBe(true);
  });

  it("refuses an empty CSV without calling the API", async () => {
    const result = await submit({ goal: "g", source: "tabular", csv: "   " });
    expect(result).toEqual({ error: expect.stringContaining("CSV") });
    expect(createInvestigationMock).not.toHaveBeenCalled();
  });
});

describe("shared validation", () => {
  it("requires a goal whichever source is chosen", async () => {
    const cases: Record<string, string>[] = [
      { goal: "  ", source: "edgar", entities: "AAPL" },
      { goal: "  ", source: "tabular", csv: "a,b\n1,2" },
    ];
    for (const fields of cases) {
      const result = await submit(fields);
      expect(result).toEqual({ error: expect.stringContaining("answer") });
    }
    expect(createInvestigationMock).not.toHaveBeenCalled();
  });
});
