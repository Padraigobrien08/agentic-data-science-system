import Link from "next/link";

import type {
  DecisionItem,
  EvidenceItem,
  ExperimentItem,
  HypothesisItem,
  InvestigationArtifactRef,
  InvestigationDetail as Detail,
} from "@/lib/api/types";
import {
  confidenceDelta,
  dispositionTone,
  evidenceDirectionTone,
  evidenceForHypothesis,
  formatConfidence,
  hypothesisStatusTone,
  investigationStatusTone,
  titleize,
} from "@/lib/investigation-view";

import { Pill } from "./pill";

function Section({
  title,
  count,
  children,
}: Readonly<{ title: string; count?: number; children: React.ReactNode }>) {
  return (
    <section className="space-y-3">
      <h2 className="flex items-baseline gap-2 text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
        {title}
        {count !== undefined ? (
          <span className="font-mono text-xs font-normal text-neutral-400">{count}</span>
        ) : null}
      </h2>
      {children}
    </section>
  );
}

function Card({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">{children}</div>
  );
}

function DeltaBadge({ h }: Readonly<{ h: HypothesisItem }>) {
  const delta = confidenceDelta(h);
  if (delta === null) return null;
  const up = delta > 0;
  return (
    <span
      className={`font-mono text-xs ${up ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}
      title={`prior ${formatConfidence(h.prior_confidence)} → ${formatConfidence(h.confidence)}`}
    >
      {up ? "▲" : "▼"} {formatConfidence(Math.abs(delta))}
    </span>
  );
}

function EvidenceRow({ e }: Readonly<{ e: EvidenceItem }>) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <Pill tone={evidenceDirectionTone(e.direction)} />
      <div className="min-w-0">
        <p className="text-neutral-700 dark:text-neutral-200">{e.claim}</p>
        <p className="mt-0.5 font-mono text-xs text-neutral-400">
          strength {formatConfidence(e.strength)} · reliability {formatConfidence(e.reliability)} ·
          coverage {formatConfidence(e.coverage)}
        </p>
      </div>
    </div>
  );
}

function HypothesisCard({ h, detail }: Readonly<{ h: HypothesisItem; detail: Detail }>) {
  const linked = evidenceForHypothesis(detail, h);
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{h.statement}</p>
        <div className="flex shrink-0 items-center gap-2">
          <DeltaBadge h={h} />
          <Pill tone={hypothesisStatusTone(h.status)} />
        </div>
      </div>
      {h.rationale ? (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{h.rationale}</p>
      ) : null}
      <p className="mt-2 font-mono text-xs text-neutral-400">
        confidence {formatConfidence(h.confidence)}
        {h.metric_refs.length ? ` · ${h.metric_refs.join(", ")}` : ""}
      </p>
      {linked.length ? (
        <div className="mt-3 space-y-2 border-t border-neutral-100 pt-3 dark:border-neutral-800">
          {linked.map((e) => (
            <EvidenceRow key={e.id} e={e} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}

const DECISION_GLYPH: Record<string, string> = {
  propose_hypothesis: "◇",
  select_experiment: "▶",
  update_evidence: "≡",
  revise_confidence: "±",
  spawn_sub_hypothesis: "⑂",
  request_critique: "⚑",
};

function DecisionRow({ d }: Readonly<{ d: DecisionItem }>) {
  return (
    <li className="flex gap-3">
      <span className="mt-0.5 select-none font-mono text-neutral-400" aria-hidden>
        {DECISION_GLYPH[d.decision_type] ?? "•"}
      </span>
      <div className="min-w-0 flex-1 border-b border-neutral-100 pb-3 dark:border-neutral-800">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
            {titleize(d.decision_type)}
          </span>
          <span className="font-mono text-xs text-neutral-400">iter {d.iteration}</span>
        </div>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">{d.rationale}</p>
        {d.chosen_option ? (
          <p className="mt-0.5 font-mono text-xs text-neutral-400">→ {d.chosen_option}</p>
        ) : null}
      </div>
    </li>
  );
}

function formatBytes(n: number | null): string {
  if (n === null || !Number.isFinite(n)) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function ArtifactChip({ a }: Readonly<{ a: InvestigationArtifactRef }>) {
  const size = formatBytes(a.byte_size);
  return (
    <a
      href={`/api/artifacts/${a.id}/content?disposition=attachment`}
      className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 px-2 py-1 font-mono text-xs text-neutral-600 transition-colors hover:border-neutral-400 hover:text-neutral-900 dark:border-neutral-700 dark:text-neutral-300 dark:hover:border-neutral-500 dark:hover:text-neutral-100"
      title={`Download ${a.name}${a.mime_type ? ` (${a.mime_type})` : ""}`}
    >
      <span className="select-none text-neutral-400" aria-hidden>
        ↓
      </span>
      <span className="truncate">{a.name}</span>
      <span className="text-[10px] uppercase text-neutral-400">{a.kind}</span>
      {size ? <span className="text-neutral-400">· {size}</span> : null}
    </a>
  );
}

function ExperimentRow({ x }: Readonly<{ x: ExperimentItem }>) {
  const failed = x.status === "failed";
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-sm font-medium text-neutral-800 dark:text-neutral-200">
          {x.tool_name}
        </span>
        <span
          className={`text-xs ${failed ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}
        >
          {titleize(x.status)}
        </span>
      </div>
      {x.summary ? (
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{x.summary}</p>
      ) : null}
      {x.error?.message ? (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{String(x.error.message)}</p>
      ) : null}
      {x.artifacts.length ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-neutral-100 pt-3 dark:border-neutral-800">
          {x.artifacts.map((a) => (
            <ArtifactChip key={a.id} a={a} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}

export function InvestigationDetailView({
  projectId,
  detail,
}: Readonly<{ projectId: string; detail: Detail }>) {
  const status = investigationStatusTone(detail.status);
  const concl = detail.conclusion_detail;
  const openCritiques = detail.critiques.filter((c) => !c.resolved);

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            {detail.objective ?? "Investigation"}
          </h1>
          <Pill tone={status} />
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-neutral-500 dark:text-neutral-400">
          <span>confidence {formatConfidence(detail.confidence)}</span>
          {detail.adapter_id ? <span>· {detail.adapter_id}</span> : null}
          {detail.datasets[0] ? <span>· {detail.datasets[0].name}</span> : null}
          {detail.analysis_run_id ? (
            <Link
              href={`/projects/${projectId}/runs/${detail.analysis_run_id}/trace`}
              className="underline"
            >
              parent run
            </Link>
          ) : null}
        </div>
        {detail.termination ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Stopped: <span className="font-medium">{titleize(detail.termination.reason ?? "")}</span>
            {detail.termination.rationale ? ` — ${detail.termination.rationale}` : ""}
          </p>
        ) : null}
      </header>

      {/* Conclusion */}
      {concl ? (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Conclusion
            </span>
            <Pill tone={dispositionTone(concl.disposition)} />
            <span className="ml-auto font-mono text-xs text-neutral-400">
              {formatConfidence(concl.confidence)}
            </span>
          </div>
          <p className="text-sm text-neutral-800 dark:text-neutral-100">{concl.statement}</p>
          {concl.caveats.length ? (
            <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-neutral-500 dark:text-neutral-400">
              {concl.caveats.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {/* Hypotheses (with their linked evidence) */}
      {detail.hypotheses.length ? (
        <Section title="Hypotheses" count={detail.hypotheses.length}>
          <div className="space-y-3">
            {detail.hypotheses.map((h) => (
              <HypothesisCard key={h.id} h={h} detail={detail} />
            ))}
          </div>
        </Section>
      ) : null}

      {/* Agent decisions timeline */}
      {detail.decisions.length ? (
        <Section title="Agent decisions" count={detail.decisions.length}>
          <ol className="space-y-3">
            {detail.decisions.map((d) => (
              <DecisionRow key={d.id} d={d} />
            ))}
          </ol>
        </Section>
      ) : null}

      {/* Experiments */}
      {detail.experiments.length ? (
        <Section title="Experiments" count={detail.experiments.length}>
          <div className="space-y-3">
            {detail.experiments.map((x) => (
              <ExperimentRow key={x.id} x={x} />
            ))}
          </div>
        </Section>
      ) : null}

      {/* Critiques */}
      {openCritiques.length ? (
        <Section title="Open critiques" count={openCritiques.length}>
          <div className="space-y-2">
            {openCritiques.map((c) => (
              <Card key={c.id}>
                <p className="text-sm text-neutral-800 dark:text-neutral-200">{c.message}</p>
                <p className="mt-1 font-mono text-xs text-neutral-400">
                  {titleize(c.critique_type)} · {c.severity} · target {c.target_kind}
                </p>
              </Card>
            ))}
          </div>
        </Section>
      ) : null}

      {/* Open questions */}
      {detail.open_questions.length ? (
        <Section title="Open questions" count={detail.open_questions.length}>
          <ul className="space-y-1 text-sm text-neutral-600 dark:text-neutral-300">
            {detail.open_questions.map((q) => (
              <li key={q.id} className="flex gap-2">
                <span className="text-neutral-400" aria-hidden>
                  ?
                </span>
                <span>{q.question}</span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </div>
  );
}
