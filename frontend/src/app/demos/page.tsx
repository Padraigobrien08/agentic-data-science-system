import type { Metadata } from "next";
import Link from "next/link";

import { Pill } from "@/components/investigations/pill";
import { listDemos } from "@/lib/api/demos";
import { formatConfidence, investigationStatusTone, titleize } from "@/lib/investigation-view";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Recorded investigations",
  description:
    "Real investigations run by the adaptive loop and published as-is — hypotheses, evidence, critiques, and the reason each one stopped.",
};

export default async function DemosPage() {
  const demos = await listDemos();

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-4">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Recorded investigations
        </h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          Real runs of the adaptive loop, published exactly as they ended — including the one
          that declined to pick a winner. Every claim links down to the evidence and the
          deterministic computation behind it; no number here was produced by a language model.
        </p>
      </header>

      <div className="space-y-4">
        {demos.map((d) => (
          <Link
            key={d.id}
            href={`/demos/${d.demo_slug}`}
            className="block rounded-lg border border-neutral-200 p-4 transition-colors hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-500"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {d.objective ?? "Investigation"}
              </p>
              <Pill tone={investigationStatusTone(d.status)} />
            </div>
            {d.conclusion ? (
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">{d.conclusion}</p>
            ) : null}
            <p className="mt-3 font-mono text-xs text-neutral-400">
              {titleize(d.status)} · confidence {formatConfidence(d.confidence)} ·{" "}
              {d.counts.hypotheses} hypotheses · {d.counts.experiments} experiments ·{" "}
              {d.counts.evidence} evidence · {d.counts.critiques} critique
              {d.counts.critiques === 1 ? "" : "s"}
            </p>
          </Link>
        ))}
      </div>

      <p className="text-xs text-neutral-400 dark:text-neutral-500">
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
