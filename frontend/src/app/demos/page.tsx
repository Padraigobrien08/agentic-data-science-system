import type { Metadata } from "next";
import Link from "next/link";

import { Pill } from "@/components/investigations/pill";
import { listDemos } from "@/lib/api/demos";
import { formatConfidence, outcomeSummary, outcomeTone } from "@/lib/investigation-view";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Recorded investigations",
  description:
    "Real investigations run by the adaptive loop and published as-is — hypotheses, evidence, critiques, and the reason each one stopped.",
};

/**
 * The "…including the one that declined" clause, derived.
 *
 * It was written when there was exactly one declining run and went stale as soon as a second
 * was published. The outcomes are classified now, so the sentence can read them instead of
 * restating them.
 */
function outcomeBlurb(kinds: string[]): string {
  const set = new Set(kinds);
  const notes: string[] = [];
  const declined = kinds.filter((k) => k === "declined").length;
  if (declined) {
    notes.push(declined === 1 ? "one declined to answer" : `${declined} declined to answer`);
  }
  if (set.has("contradicted")) {
    notes.push("one caught itself holding two claims that could not both be true");
  }
  if (!notes.length) return "";
  return ` — ${notes.join(", and ")}`;
}

export default async function DemosPage() {
  const demos = await listDemos();
  const blurb = outcomeBlurb(demos.map((d) => d.outcome.kind));

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-4">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold text-[var(--foreground)]">
          Recorded investigations
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Real runs of the adaptive loop, published exactly as they ended{blurb}. Every claim
          links down to the evidence and the deterministic computation behind it; no number here
          was produced by a language model.
        </p>
      </header>

      <div className="space-y-4">
        {demos.map((d) => (
          <Link
            key={d.id}
            href={`/demos/${d.demo_slug}`}
            className="block rounded-lg border border-[var(--border)] bg-[var(--chat-raise)] p-4 transition-colors hover:bg-[var(--chat-hover)]"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium text-[var(--foreground)]">
                {d.objective ?? "Investigation"}
              </p>
              {/* The outcome, not the stored status: `exhausted` reads as a crash to someone
                  meeting this page cold, and half these runs declined on purpose. */}
              <Pill tone={outcomeTone(d.outcome.kind)} />
            </div>
            <p className="mt-2 text-sm text-[var(--foreground)]">
              {outcomeSummary(d.outcome)}
            </p>
            {d.conclusion ? (
              <p className="mt-2 text-sm text-[var(--muted)]">{d.conclusion}</p>
            ) : null}
            <p className="mt-3 font-mono text-xs text-[var(--chat-faint)]">
              stopped: {d.outcome.termination_reason ?? "unknown"} · confidence{" "}
              {formatConfidence(d.confidence)} · {d.counts.hypotheses} hypotheses ·{" "}
              {d.counts.experiments} experiments · {d.counts.evidence} evidence ·{" "}
              {d.counts.critiques} critique{d.counts.critiques === 1 ? "" : "s"}
            </p>
          </Link>
        ))}
      </div>

      <p className="text-xs text-[var(--chat-faint)]">
        Recorded with{" "}
        <a
          className="underline"
          href="https://github.com/Padraigobrien08/agentic-data-science-system/blob/main/scripts/record_demo.py"
        >
          scripts/record_demo.py
        </a>{" "}
        against live data, then published unedited. A run that ends{" "}
        <span className="font-mono">insufficient_evidence</span> is a correct outcome, not a
        failed one.
      </p>
    </div>
  );
}
