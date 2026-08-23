import Link from "next/link";

import type {
  CritiqueItem,
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
  formatConfidence,
  hypothesisStatusTone,
  investigationStatusTone,
  outcomeSummary,
  outcomeTone,
  titleize,
} from "@/lib/investigation-view";
import { investigationTimeline } from "@/lib/trace-timeline";
import { groupEvidenceByClaim, traceSections } from "@/lib/trace-view";
import { TraceTimeline } from "@/components/trace/trace-timeline";

import { Pill } from "./pill";

/**
 * The recorded trace of one investigation.
 *
 * Shared deliberately between the public replay tier and the authenticated run page, so
 * "rendered by the same UI as a live run" stays true in code rather than as a claim. Both
 * surfaces improve or regress together.
 *
 * Everything here is coloured with CSS variables rather than Tailwind colour utilities.
 * `darkMode` is `class` and no `.dark` element is ever rendered, so `dark:` variants are dead
 * in this app; the surfaces invert through `prefers-color-scheme` on the tokens instead.
 */

const RULE = "border-[var(--border)]";
const MONO = "font-mono text-[11px]";

function SectionHeading({
  title,
  count,
  note,
  id,
}: Readonly<{ title: string; count?: number; note?: string; id?: string }>) {
  return (
    <div
      id={id}
      className={`flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b ${RULE} pb-2`}
    >
      <h2 className="text-sm font-semibold tracking-[-0.01em] text-[var(--foreground)]">{title}</h2>
      {count !== undefined ? (
        <span className={`${MONO} text-[var(--chat-faint)]`}>{count}</span>
      ) : null}
      {note ? <span className={`${MONO} text-[var(--chat-faint)]`}>· {note}</span> : null}
    </div>
  );
}

function Card({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className={`rounded-lg border ${RULE} bg-[var(--chat-raise)] p-4`}>{children}</div>
  );
}

function DeltaBadge({ h }: Readonly<{ h: HypothesisItem }>) {
  const delta = confidenceDelta(h);
  if (delta === null) return null;
  const up = delta > 0;
  return (
    <span
      className={`${MONO} ${up ? "text-[var(--status-success-ink)]" : "text-[var(--status-danger-ink)]"}`}
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
        <p className="text-[var(--foreground)]">{e.claim}</p>
        <p className={`mt-0.5 ${MONO} text-[var(--chat-faint)]`}>
          strength {formatConfidence(e.strength)} · reliability {formatConfidence(e.reliability)} ·
          coverage {formatConfidence(e.coverage)}
        </p>
      </div>
    </div>
  );
}

/**
 * A claim with the evidence that bears on it, split by direction.
 *
 * What supports a claim and what argues against it are different questions, and a single
 * undifferentiated list answers neither. Refuting evidence leads when it exists — it is the
 * part a reader is least likely to go looking for and most needs to see.
 */
function ClaimCard({
  claim,
  supporting,
  refuting,
}: Readonly<{ claim: HypothesisItem; supporting: EvidenceItem[]; refuting: EvidenceItem[] }>) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-[var(--foreground)]">{claim.statement}</p>
        <div className="flex shrink-0 items-center gap-2">
          <DeltaBadge h={claim} />
          <Pill tone={hypothesisStatusTone(claim.status)} />
        </div>
      </div>
      {claim.rationale ? (
        <p className="mt-1 text-sm text-[var(--muted)]">{claim.rationale}</p>
      ) : null}
      <p className={`mt-2 ${MONO} text-[var(--chat-faint)]`}>
        confidence {formatConfidence(claim.confidence)}
        {claim.metric_refs.length ? ` · ${claim.metric_refs.join(", ")}` : ""}
        {` · ${supporting.length} supporting`}
        {refuting.length ? ` · ${refuting.length} refuting` : ""}
      </p>
      {refuting.length || supporting.length ? (
        <div className={`mt-3 space-y-2 border-t ${RULE} pt-3`}>
          {[...refuting, ...supporting].map((e) => (
            <EvidenceRow key={e.id} e={e} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}

function formatBytes(n: number | null): string {
  if (n === null || !Number.isFinite(n)) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function ArtifactChip({
  a,
  href,
}: Readonly<{ a: InvestigationArtifactRef; href: string | null }>) {
  const size = formatBytes(a.byte_size);
  if (href === null) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md border border-dashed ${RULE} px-2 py-1 ${MONO} text-[var(--chat-faint)]`}
        title={`${a.name} — content not available in this showcase`}
      >
        <span className="truncate">{a.name}</span>
        <span className="uppercase">{a.kind}</span>
      </span>
    );
  }
  return (
    <a
      href={href}
      className={`inline-flex items-center gap-1.5 rounded-md border ${RULE} px-2 py-1 ${MONO} text-[var(--muted)] transition-colors hover:bg-[var(--chat-hover)] hover:text-[var(--foreground)]`}
      title={`Download ${a.name}${a.mime_type ? ` (${a.mime_type})` : ""}`}
    >
      <span className="select-none text-[var(--chat-faint)]" aria-hidden>
        ↓
      </span>
      <span className="truncate">{a.name}</span>
      <span className="uppercase text-[var(--chat-faint)]">{a.kind}</span>
      {size ? <span className="text-[var(--chat-faint)]">· {size}</span> : null}
    </a>
  );
}

function ExperimentRow({
  x,
  artifactHref,
}: Readonly<{ x: ExperimentItem; artifactHref: (a: InvestigationArtifactRef) => string | null }>) {
  const failed = x.status === "failed";
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-sm font-medium text-[var(--foreground)]">{x.tool_name}</span>
        <span
          className={`text-xs ${failed ? "text-[var(--status-danger-ink)]" : "text-[var(--status-success-ink)]"}`}
        >
          {titleize(x.status)}
        </span>
      </div>
      {x.summary ? <p className="mt-1 text-sm text-[var(--muted)]">{x.summary}</p> : null}
      {x.error?.message ? (
        <p className="mt-1 text-sm text-[var(--status-danger-ink)]">{String(x.error.message)}</p>
      ) : null}
      {x.artifacts.length ? (
        <div className={`mt-3 flex flex-wrap gap-2 border-t ${RULE} pt-3`}>
          {x.artifacts.map((a) => (
            <ArtifactChip key={a.id} a={a} href={artifactHref(a)} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}

function CritiqueCard({ c }: Readonly<{ c: CritiqueItem }>) {
  return (
    <div
      className={`rounded-r-lg border border-l-2 ${RULE} border-l-[var(--status-warning-border)] bg-[var(--chat-raise)] p-4`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span
          className={`${MONO} uppercase tracking-[0.08em] text-[var(--status-warning-ink)]`}
        >
          {titleize(c.critique_type)}
        </span>
        <span className={`${MONO} text-[var(--chat-faint)]`}>
          {c.severity}
          {c.resolved ? " · resolved" : " · unresolved"}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-[var(--foreground)]">{c.message}</p>
      {c.suggested_action ? (
        <p className={`mt-2 ${MONO} text-[var(--accent)]`}>→ {c.suggested_action}</p>
      ) : null}
    </div>
  );
}

function defaultArtifactHref(a: InvestigationArtifactRef): string {
  return `/api/artifacts/${a.id}/content?disposition=attachment`;
}

export function InvestigationDetailView({
  projectId,
  detail,
  artifactHref = defaultArtifactHref,
}: Readonly<{
  /** Null on the public demo surface, where there is no project to link back into. */
  projectId: string | null;
  detail: Detail;
  /** Where an artifact's bytes live; the demo surface serves them without auth. */
  artifactHref?: (a: InvestigationArtifactRef) => string | null;
}>) {
  const status = investigationStatusTone(detail.status);
  const concl = detail.conclusion_detail;
  const iterations = investigationTimeline(detail.decisions, detail.hypotheses);
  const claimGroups = groupEvidenceByClaim(detail.evidence, detail.hypotheses);
  const sections = traceSections(detail);
  const critiques = [...detail.critiques].sort((a, b) => Number(a.resolved) - Number(b.resolved));

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-xl font-semibold tracking-[-0.02em] text-[var(--foreground)]">
            {detail.objective ?? "Investigation"}
          </h1>
          {/* Outcome leads, stored status follows: a run that correctly declined is stored
              as `exhausted`, which reads as a crash to anyone meeting the page cold. */}
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={outcomeTone(detail.outcome.kind)} />
            <Pill tone={status} />
          </div>
        </div>
        <p className="text-sm text-[var(--foreground)]">{outcomeSummary(detail.outcome)}</p>
        <div
          className={`flex flex-wrap items-center gap-x-4 gap-y-1 ${MONO} text-[var(--muted)]`}
        >
          <span>confidence {formatConfidence(detail.confidence)}</span>
          {detail.adapter_id ? <span>· {detail.adapter_id}</span> : null}
          {detail.datasets[0] ? <span>· {detail.datasets[0].name}</span> : null}
          {detail.termination?.reason ? (
            <span>· stopped: {detail.termination.reason}</span>
          ) : null}
          {projectId && detail.analysis_run_id ? (
            <Link
              href={`/projects/${projectId}/runs/${detail.analysis_run_id}/trace`}
              className="underline"
            >
              parent run
            </Link>
          ) : null}
        </div>
        {/* Counts up front: what this run produced, before any of it is opened. */}
        <div className={`flex flex-wrap gap-x-4 gap-y-1 ${MONO} text-[var(--chat-faint)]`}>
          {sections.map((s) => (
            <a key={s.id} href={`#trace-${s.id}`} className="hover:text-[var(--foreground)]">
              {s.label.toLowerCase()} <span className="text-[var(--muted)]">{s.count}</span>
              {s.note ? ` · ${s.note}` : ""}
            </a>
          ))}
        </div>
      </header>

      {concl ? (
        <div className={`rounded-lg border ${RULE} bg-[var(--chat-rail)] p-4`}>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-semibold tracking-[-0.01em] text-[var(--foreground)]">
              Conclusion
            </span>
            <Pill tone={dispositionTone(concl.disposition)} />
            <span className={`ml-auto ${MONO} text-[var(--chat-faint)]`}>
              {formatConfidence(concl.confidence)}
            </span>
          </div>
          <p className="text-sm text-[var(--foreground)]">{concl.statement}</p>
          {concl.caveats.length ? (
            <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-[var(--muted)]">
              {concl.caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {iterations.length ? (
        <section className="space-y-1">
          <SectionHeading
            id="trace-decisions"
            title="Decisions"
            count={detail.decisions.length}
            note={`${iterations.length} iteration${iterations.length === 1 ? "" : "s"}`}
          />
          {/* Same component the docked rail renders, at page density — so a reader who
              learned the trace in the chat is reading the same thing here. */}
          <TraceTimeline groups={iterations} density="comfortable" />
        </section>
      ) : null}

      {claimGroups.length ? (
        <section className="space-y-3">
          <SectionHeading
            id="trace-hypotheses"
            title="Claims and the evidence for them"
            count={detail.hypotheses.length}
            note={`${detail.evidence.length} evidence items`}
          />
          {claimGroups.map((g) =>
            g.claim ? (
              <ClaimCard
                key={g.claim.id}
                claim={g.claim}
                supporting={g.supporting}
                refuting={g.refuting}
              />
            ) : (
              <Card key="unlinked">
                <p className="text-sm font-medium text-[var(--muted)]">{g.label}</p>
                <div className={`mt-3 space-y-2 border-t ${RULE} pt-3`}>
                  {g.items.map((e) => (
                    <EvidenceRow key={e.id} e={e} />
                  ))}
                </div>
              </Card>
            ),
          )}
        </section>
      ) : null}

      {detail.experiments.length ? (
        <section className="space-y-3">
          <SectionHeading
            id="trace-experiments"
            title="Experiments"
            count={detail.experiments.length}
            note={`${detail.experiments.reduce((n, x) => n + x.artifacts.length, 0)} artifacts`}
          />
          {detail.experiments.map((x) => (
            <ExperimentRow key={x.id} x={x} artifactHref={artifactHref} />
          ))}
        </section>
      ) : null}

      {critiques.length ? (
        <section className="space-y-2">
          <SectionHeading
            id="trace-critiques"
            title="Critiques"
            count={critiques.length}
            note={`${critiques.filter((c) => !c.resolved).length} unresolved`}
          />
          {critiques.map((c) => (
            <CritiqueCard key={c.id} c={c} />
          ))}
        </section>
      ) : null}

      {detail.open_questions.length ? (
        <section className="space-y-2">
          <SectionHeading
            id="trace-questions"
            title="Open questions"
            count={detail.open_questions.length}
            note="left open on purpose"
          />
          <ul className="space-y-2 text-sm text-[var(--muted)]">
            {detail.open_questions.map((q) => (
              <li key={q.id} className="flex gap-2">
                <span className="text-[var(--chat-faint)]" aria-hidden>
                  ?
                </span>
                <span className="text-[var(--foreground)]">{q.question}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
