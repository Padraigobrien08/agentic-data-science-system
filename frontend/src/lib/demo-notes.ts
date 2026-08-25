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
    label: "unanswerable",
    body:
      "Nothing in this dataset measures loyalty, so the question cannot be answered from it. " +
      "The run says so: it declined at 20% confidence and named the missing measure, instead " +
      "of reaching for the nearest column and presenting it as an answer. Knowing when not " +
      "to answer is the hardest thing to build here and the easiest to fake by never asking " +
      "a hard question — so the hard question is on the site. For completeness: the README " +
      "documents a benchmark case where this model does substitute a metric and report 95%. " +
      "Repeated recordings of this question did not reproduce that.",
  },
};

/** The framing for a published run, or null when it needs none — the usual case. */
export function demoNote(slug: string): DemoNote | null {
  return NOTES[slug] ?? null;
}
