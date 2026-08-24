"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import { Pill } from "@/components/investigations/pill";
import { formatConfidence, hypothesisStatusTone } from "@/lib/investigation-view";
import { claimSummary, type ClaimStep, type ClaimTrace } from "@/lib/trace-claims";

/**
 * The trace read as an experimental loop: claim, verdict, and what was done to find out.
 *
 * Each claim states itself and says plainly whether it held. The steps taken to test it sit
 * underneath, collapsed — a reader following the argument does not need them, and a reader
 * checking the argument needs all of them. Nothing is summarised away; expanding shows every
 * recorded step in the order it happened.
 */

const MONO = "font-mono text-[11px]";
const RULE = "border-[var(--border)]";

function StepRow({ step }: Readonly<{ step: ClaimStep }>) {
  return (
    <li className="flex gap-2">
      <span className={`${MONO} select-none text-[var(--chat-faint)]`} aria-hidden>
        {step.glyph}
      </span>
      <div className="min-w-0">
        <p className="text-[12.5px] leading-snug text-[var(--foreground)]">
          {step.label}
          {step.accent ? (
            <span className={`${MONO} ml-1.5 text-[var(--accent)]`}>{step.accent}</span>
          ) : null}
        </p>
        {step.detail ? (
          <p className="mt-0.5 text-[11.5px] leading-snug text-[var(--muted)]">{step.detail}</p>
        ) : null}
      </div>
    </li>
  );
}

function Track({
  claim,
  index,
}: Readonly<{ claim: ClaimTrace["claims"][number]; index: number }>) {
  const [open, setOpen] = useState(false);
  const stepCount = claim.steps.length;

  return (
    <li className={`border-b ${RULE} py-3 last:border-b-0`}>
      <div className="flex items-start gap-2">
        <span className={`${MONO} mt-1 shrink-0 text-[var(--chat-faint)]`} aria-hidden>
          H{index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium leading-snug text-[var(--foreground)]">
            {claim.statement}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
            <Pill tone={hypothesisStatusTone(claim.status)} />
            <span className={`${MONO} text-[var(--chat-faint)]`}>
              {formatConfidence(claim.confidence)}
            </span>
            <span className={`${MONO} text-[var(--chat-faint)]`}>· {claimSummary(claim)}</span>
          </div>

          {stepCount ? (
            <>
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                className={`mt-2 flex items-center gap-1 rounded-control ${MONO} text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]`}
              >
                <ChevronRight
                  className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""} motion-reduce:transition-none`}
                  aria-hidden
                />
                {open ? "hide steps" : `${stepCount} step${stepCount === 1 ? "" : "s"}`}
              </button>
              {open ? (
                <ol className={`mt-2 space-y-2 border-l ${RULE} pl-3`}>
                  {claim.steps.map((s) => (
                    <StepRow key={s.id} step={s} />
                  ))}
                </ol>
              ) : null}
            </>
          ) : (
            // A claim with no recorded steps was proposed and never acted on. Saying so is
            // more useful than an empty expander.
            <p className={`mt-2 ${MONO} text-[var(--chat-faint)]`}>no recorded steps</p>
          )}
        </div>
      </div>
    </li>
  );
}

export function ClaimTrackList({
  trace,
  emptyLabel = "This run proposed no claims.",
}: Readonly<{ trace: ClaimTrace; emptyLabel?: string }>) {
  const [sharedOpen, setSharedOpen] = useState(false);

  if (!trace.claims.length) {
    return <p className={`${MONO} text-[var(--chat-faint)]`}>{emptyLabel}</p>;
  }

  return (
    <div>
      <ol className="space-y-0">
        {trace.claims.map((claim, i) => (
          <Track key={claim.id} claim={claim} index={i} />
        ))}
      </ol>

      {/* Steps belonging to the run rather than a claim — planning, the conclusion, and
          anything whose targets were never recorded. Kept visible but out of the way: they
          are part of the record, and attaching them to a claim would be a guess. */}
      {trace.shared.length ? (
        <div className={`mt-3 border-t ${RULE} pt-3`}>
          <button
            type="button"
            onClick={() => setSharedOpen((v) => !v)}
            aria-expanded={sharedOpen}
            className={`flex items-center gap-1 rounded-control ${MONO} text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]`}
          >
            <ChevronRight
              className={`h-3 w-3 transition-transform ${sharedOpen ? "rotate-90" : ""} motion-reduce:transition-none`}
              aria-hidden
            />
            {trace.shared.length} step{trace.shared.length === 1 ? "" : "s"} not tied to one
            claim
          </button>
          {sharedOpen ? (
            <ol className={`mt-2 space-y-2 border-l ${RULE} pl-3`}>
              {trace.shared.map((s) => (
                <StepRow key={s.id} step={s} />
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
