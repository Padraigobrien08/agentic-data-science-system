/**
 * Editorial framing for a published run, keyed by slug.
 *
 * Deliberately *not* run data. Nothing here is derived from the investigation and nothing
 * here changes it — the recorded numbers, statuses and prose stay exactly as the loop
 * produced them. This is the curator saying why a run is on the site, which is a different
 * kind of claim and should not be able to masquerade as evidence.
 *
 * It exists for one run. `csv-unanswerable-moat` asks which region has the strongest
 * customer loyalty, and nothing in that dataset measures loyalty. The documented failure is
 * that the model substitutes the nearest available column and reports high confidence
 * anyway. Publishing that is the most honest thing on the site and the most damaging out of
 * context — a visitor arriving on it cold, with no framing, reads a confident wrong answer
 * from a system whose whole pitch is not doing that.
 *
 * So the framing ships with the run, on the run's own page, not only on the index a reader
 * may never see.
 */

export type DemoNote = {
  /** Short label beside the outcome, in the page header. */
  label: string;
  /** The framing itself, shown above the conversation. */
  body: string;
};

const NOTES: Record<string, DemoNote> = {
  "csv-unanswerable-moat": {
    label: "known limit",
    body:
      "This run is published because it fails. Nothing in this dataset measures customer " +
      "loyalty, so the honest answer is that the question cannot be answered from these " +
      "columns — and instead the model substituted the nearest available metric and " +
      "reported high confidence. The deterministic parts held: every number below is real " +
      "and every step is recorded. What failed is the judgement that the question was " +
      "answerable at all, and the loop does not currently catch it. It is documented in the " +
      "README as a known limit, and it is here in the same evidence format as the runs that " +
      "went well.",
  },
};

/** The framing for a published run, or null when it needs none — the usual case. */
export function demoNote(slug: string): DemoNote | null {
  return NOTES[slug] ?? null;
}
