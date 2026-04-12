import { describe, expect, it } from "vitest";

import { humanizeWeakEvidenceSignal } from "../signal-labels";

describe("humanizeWeakEvidenceSignal", () => {
  it("maps known ids", () => {
    expect(humanizeWeakEvidenceSignal("low_overall_confidence")).toBe("Low overall confidence");
    expect(humanizeWeakEvidenceSignal("thin_panel")).toBe("Thin evidence panel");
  });

  it("title-cases unknown snake ids", () => {
    expect(humanizeWeakEvidenceSignal("custom_signal_here")).toBe("Custom Signal Here");
  });
});
