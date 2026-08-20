import { describe, expect, it } from "vitest";

import { outcomeSummary, outcomeTone } from "@/lib/investigation-view";

function outcome(over: Partial<Parameters<typeof outcomeSummary>[0]> = {}) {
  return {
    kind: "declined",
    claims_supported: 0,
    claims_rejected: 0,
    claims_weakened: 0,
    claims_unresolved: 0,
    ...over,
  };
}

describe("outcomeTone", () => {
  it("names each outcome in a reader's terms rather than the database's", () => {
    expect(outcomeTone("supported").label).toBe("Concluded");
    expect(outcomeTone("mixed").label).toBe("Mixed verdict");
    expect(outcomeTone("declined").label).toBe("Declined to answer");
    expect(outcomeTone("contradicted").label).toBe("Caught its own contradiction");
    expect(outcomeTone("stopped").label).toBe("Stopped early");
  });

  it("does not colour declining as a failure", () => {
    // Declining is a correct outcome here. Painting it red would contradict the whole point
    // of publishing the runs that declined.
    expect(outcomeTone("declined").className).not.toContain("red");
    expect(outcomeTone("contradicted").className).not.toContain("red");
  });

  it("falls back readably on an outcome kind it does not know", () => {
    // The backend owns the vocabulary, so a new kind must not render as blank or crash.
    // Falls through to `titleize`, which is Title Case.
    const tone = outcomeTone("some_future_kind");
    expect(tone.label).toBe("Some Future Kind");
    expect(tone.className).toBeTruthy();
  });
});

describe("outcomeSummary", () => {
  it("counts what stood and what did not", () => {
    expect(outcomeSummary(outcome({ kind: "supported", claims_supported: 2 }))).toBe(
      "2 claims stood up to the evidence.",
    );
    expect(
      outcomeSummary(outcome({ kind: "mixed", claims_supported: 1, claims_rejected: 1 })),
    ).toBe("1 claim stood, 1 did not.");
  });

  it("singularises a lone claim", () => {
    expect(outcomeSummary(outcome({ kind: "supported", claims_supported: 1 }))).toBe(
      "1 claim stood up to the evidence.",
    );
  });

  it("explains a contradiction without implying either side won", () => {
    const text = outcomeSummary(outcome({ kind: "contradicted", claims_weakened: 2 }));
    expect(text).toContain("could not both be true");
    expect(text).toContain("neither");
  });

  it("distinguishes being cut off from declining", () => {
    expect(outcomeSummary(outcome({ kind: "stopped" }))).toContain("cut off");
    expect(outcomeSummary(outcome({ kind: "declined", claims_weakened: 2 }))).toContain(
      "No claim survived",
    );
  });

  it("handles a declined run that never raised a claim", () => {
    expect(outcomeSummary(outcome({ kind: "declined" }))).toBe(
      "The loop found nothing it could stand behind.",
    );
  });
});
