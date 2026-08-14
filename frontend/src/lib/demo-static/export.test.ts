import { describe, expect, it } from "vitest";

import artifactHrefs from "./artifacts.json";
import index from "./index.json";
import { DEMO_ARTIFACT_HREFS, DEMO_DETAILS, DEMO_INDEX } from "./generated";

/**
 * Guards the committed export produced by `scripts/export_demo_static.py`.
 *
 * The static showcase has no backend to fall back on, so a malformed export is a broken
 * public demo with no runtime error to notice it. CI cannot re-run the exporter (it has no
 * database holding the recordings), which is exactly why the committed artifact is checked
 * for internal consistency here instead.
 */
describe("static demo export", () => {
  it("publishes every indexed demo with a slug and a detail document", () => {
    expect(DEMO_INDEX.length).toBeGreaterThan(0);
    for (const summary of DEMO_INDEX) {
      expect(summary.demo_slug, `demo ${summary.id} is indexed without a slug`).toBeTruthy();
      expect(DEMO_DETAILS[summary.demo_slug!]).toBeDefined();
    }
    // No orphan detail files: every exported detail is reachable from the listing.
    expect(Object.keys(DEMO_DETAILS).sort()).toEqual(
      DEMO_INDEX.map((s) => s.demo_slug).sort(),
    );
  });

  it("keeps each listing's counts consistent with its detail document", () => {
    for (const summary of DEMO_INDEX) {
      const detail = DEMO_DETAILS[summary.demo_slug!];
      expect(detail.hypotheses).toHaveLength(summary.counts.hypotheses);
      expect(detail.evidence).toHaveLength(summary.counts.evidence);
      expect(detail.experiments).toHaveLength(summary.counts.experiments);
    }
  });

  it("resolves every artifact referenced by an experiment to an exported blob", () => {
    for (const [slug, detail] of Object.entries(DEMO_DETAILS)) {
      for (const experiment of detail.experiments) {
        for (const artifact of experiment.artifacts) {
          const href = DEMO_ARTIFACT_HREFS[slug]?.[String(artifact.id)];
          expect(href, `${slug}: artifact ${artifact.id} has no exported blob`).toBeTruthy();
          expect(href).toMatch(new RegExp(`^/demo-data/${slug}/artifacts/`));
        }
      }
    }
  });

  it("derives the typed entry point from the same JSON that is committed", () => {
    expect(DEMO_INDEX).toEqual(index);
    expect(DEMO_ARTIFACT_HREFS).toEqual(artifactHrefs);
  });
});
