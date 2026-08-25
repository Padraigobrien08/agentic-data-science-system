import { describe, expect, it } from "vitest";

import { DEMO_DETAILS } from "@/lib/demo-static/generated";
import { buildLandingCounts, buildLandingTrace } from "@/lib/landing-trace";

/**
 * The landing page's trace panel, held to the run it claims to show.
 *
 * The panel it replaced was hand-typed JSX under a comment promising that "every id,
 * confidence and count below matches the published export". The counts did. The iteration
 * stamps were wrong by four — hypotheses shown at iteration 1 when the export says 0, the
 * critique at 3 when it happened at 5, the whole run compressed into four iterations when it
 * took eight. And one line described evidence as "artifact · linked" while every evidence
 * record in that export carried a null link.
 *
 * The lesson is not "someone mistyped". It is that a hand-maintained restatement of data
 * drifts from the data, silently, on the one page whose argument is that its numbers can be
 * checked. These tests are what makes the derivation load-bearing rather than decorative.
 */

const FLAGSHIP = "edgar-margin-vs-growth";

describe("landing trace panel", () => {
  const detail = DEMO_DETAILS[FLAGSHIP];

  it("has the flagship run to derive from", () => {
    expect(detail).toBeDefined();
  });

  it("stamps every line with an iteration the run actually recorded", () => {
    const recorded = new Set(
      detail.decisions.map((d) => `iter ${d.iteration ?? 0}`),
    );
    recorded.add("stop");
    recorded.add(`iter ${detail.termination?.at_iteration ?? 0}`);

    for (const line of buildLandingTrace(detail)) {
      expect(recorded, `stamp ${line.stamp} appears nowhere in the run`).toContain(line.stamp);
    }
  });

  it("names only tools the run actually ran", () => {
    const ran = new Set(detail.experiments.map((x) => x.tool_name));
    const toolLines = buildLandingTrace(detail).filter((l) => l.tone === "tool");

    expect(toolLines.length).toBeGreaterThan(0);
    for (const line of toolLines) {
      expect(ran).toContain(line.detail);
    }
  });

  it("reports claim outcomes at the confidence the export records", () => {
    const lines = buildLandingTrace(detail);
    const confidences = detail.hypotheses.map((h) => h.confidence.toFixed(2));

    for (const line of lines.filter((l) => /\(\d\.\d\d\)$/.test(l.detail))) {
      const stated = line.detail.match(/\((\d\.\d\d)\)$/)?.[1];
      expect(confidences).toContain(stated);
    }
  });

  it("stops for the reason the run stopped for", () => {
    const terminal = buildLandingTrace(detail).at(-1);

    expect(terminal?.stamp).toBe("stop");
    expect(terminal?.event).toBe(detail.termination?.reason);
  });

  it("does not claim evidence is linked unless it is", () => {
    const line = buildLandingTrace(detail).find((l) => l.event.startsWith("record_evidence"));
    const linked = detail.evidence.filter((e) => e.experiment_result_id).length;

    expect(line).toBeDefined();
    if (linked === detail.evidence.length) {
      expect(line!.detail).toContain("each linked");
    } else {
      expect(line!.detail).toContain(`${linked}/${detail.evidence.length}`);
    }
  });

  it("counts what the export contains", () => {
    const artifacts = detail.experiments.reduce((n, x) => n + x.artifacts.length, 0);

    expect(buildLandingCounts(detail)).toBe(
      `${detail.experiments.length} experiments · ${detail.evidence.length} evidence · ${artifacts} artifacts`,
    );
  });

  it("survives a run with no critique and no overturned claim", () => {
    const bare = {
      ...detail,
      critiques: [],
      hypotheses: detail.hypotheses.map((h) => ({ ...h, status: "supported" })),
    };

    expect(() => buildLandingTrace(bare)).not.toThrow();
    expect(buildLandingTrace(bare).length).toBeGreaterThan(0);
  });
});
