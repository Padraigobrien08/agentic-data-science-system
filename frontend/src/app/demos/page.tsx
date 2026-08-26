import type { Metadata } from "next";
import Link from "next/link";

import { Pill } from "@/components/investigations/pill";
import { listDemos } from "@/lib/api/demos";
import { demoNote } from "@/lib/demo-notes";
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
  const count = (kind: string) => kinds.filter((k) => k === kind).length;
  const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);
  const notes: string[] = [];

  const declined = count("declined");
  if (declined) {
    notes.push(plural(declined, "one declined to answer", `${declined} declined to answer`));
  }
  const unanswerable = count("unanswerable");
  if (unanswerable) {
    notes.push(
      plural(
        unanswerable,
        "one found the question unanswerable from the data it had",
        `${unanswerable} found their question unanswerable from the data they had`,
      ),
    );
  }
  const refuted = count("refuted");
  if (refuted) {
    notes.push(plural(refuted, "one disproved its own claims", `${refuted} disproved their own claims`));
  }
  const contradicted = count("contradicted");
  if (contradicted) {
    notes.push(
      plural(
        contradicted,
        "one caught itself holding two claims that could not both be true",
        `${contradicted} caught themselves holding two claims that could not both be true`,
      ),
    );
  }
  if (!notes.length) return "";
  const last = notes.pop()!;
  return ` — ${notes.length ? `${notes.join(", ")}, and ${last}` : last}`;
}

/**
 * "against live SEC filings and generated data", derived from what the runs actually used.
 *
 * The footer said "against live data" flat out while four of six published runs analysed a
 * generated CSV. Nobody wrote that to mislead — it was true when the only runs were EDGAR —
 * but a showcase whose argument is that it reports what it can and cannot support cannot be
 * the least accurate thing on its own page.
 */
function sourceBlurb(origins: string[]): string {
  const set = new Set(origins);
  const parts: string[] = [];
  if (set.has("live")) parts.push("live SEC filings");
  if (set.has("synthetic")) parts.push("a generated operational dataset");
  if (set.has("user_upload")) parts.push("uploaded data");
  if (!parts.length) return "recorded data";
  return parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}

export default async function DemosPage() {
  const demos = await listDemos();
  const blurb = outcomeBlurb(demos.map((d) => d.outcome.kind));
  const sources = sourceBlurb(demos.map((d) => d.dataset_origin));

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
              <span className="flex shrink-0 items-center gap-2">
                {/* Flagged here too: a reader scanning the list should know which run is on
                    the site because it failed, before they open it. */}
                {d.demo_slug && demoNote(d.demo_slug) ? (
                  <span className="rounded-chip border border-[color:var(--status-warning-border)] bg-[var(--status-warning-bg)] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.08em] text-[color:var(--status-warning-ink)]">
                    {demoNote(d.demo_slug)!.label}
                  </span>
                ) : null}
                {/* The outcome, not the stored status: `exhausted` reads as a crash to someone
                    meeting this page cold, and half these runs declined on purpose. */}
                <Pill tone={outcomeTone(d.outcome.kind)} />
                {/* Whether this run analysed real data. A set that mixes live filings with
                    generated rows has to say which is which on the card itself. */}
                <span className="rounded-chip border border-[var(--border)] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.08em] text-[var(--chat-faint)]">
                  {d.dataset_origin === "live" ? "live data" : d.dataset_origin}
                </span>
              </span>
            </div>
            <p className="mt-2 text-sm text-[var(--foreground)]">
              {outcomeSummary(d.outcome)}
            </p>
            {d.conclusion ? (
              <p className="mt-2 text-sm text-[var(--muted)]">{d.conclusion}</p>
            ) : null}
            <p className="mt-3 font-mono text-xs text-[var(--chat-faint)]">
              stopped: {d.outcome.termination_reason ?? "unknown"} · confidence{" "}
              {formatConfidence(d.confidence)} · {d.counts.hypotheses} hypothes
              {d.counts.hypotheses === 1 ? "is" : "es"} ·{" "}
              {d.counts.experiments} experiment{d.counts.experiments === 1 ? "" : "s"} ·{" "}
              {d.counts.evidence} evidence · {d.counts.critiques} critique
              {d.counts.critiques === 1 ? "" : "s"}
            </p>
          </Link>
        ))}
      </div>

      <p className="text-xs text-[var(--chat-faint)]">
        Recorded with{" "}
        <a
          className="underline"
          href="https://github.com/Padraigobrien08/auditable-agent-loop/blob/main/scripts/record_demo.py"
        >
          scripts/record_demo.py
        </a>{" "}
        against {sources}, then published unedited. A run that ends{" "}
        <span className="font-mono">insufficient_evidence</span> is a correct outcome, not a
        failed one.
      </p>
    </div>
  );
}
