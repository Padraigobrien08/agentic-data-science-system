"use client";

import Link from "next/link";

import { ANALYSIS_EXAMPLES } from "@/lib/analysis-examples";

function Hero() {
  return (
    <div className="space-y-3 text-center sm:text-left">
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--foreground)] sm:text-3xl">
        Company analysis on SEC data
      </h1>
      <p className="text-sm text-[var(--muted)]">
        Ask a question in your own words, add tickers, and run a deterministic pipeline — no perfect phrasing required.
      </p>
    </div>
  );
}

function HowItWorksStrip() {
  return (
    <div className="rounded-lg border border-[var(--border)] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">How it works</p>
      <ol className="mt-2 flex flex-col gap-2 text-xs text-[var(--foreground)] sm:flex-row sm:flex-wrap sm:gap-x-6 sm:gap-y-1">
        <li className="flex gap-2">
          <span className="font-mono text-[var(--muted)]">1.</span>
          <span>Describe what you want; tickers scope SEC panels.</span>
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-[var(--muted)]">2.</span>
          <span>Planner picks tools and writes artifacts.</span>
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-[var(--muted)]">3.</span>
          <span>Open the run answer, then deep dive for evidence and trace.</span>
        </li>
      </ol>
    </div>
  );
}

function ExampleCardsStatic() {
  return (
    <div>
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-[var(--muted)]">Examples</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {ANALYSIS_EXAMPLES.map((ex) => (
          <div
            key={ex.label}
            className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs"
          >
            <span className="font-medium text-[var(--foreground)]">{ex.label}</span>
            <span className="mt-0.5 block line-clamp-2 text-[var(--muted)]">{ex.goal}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LandingGuest() {
  const loginNext = encodeURIComponent("/");
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Hero />
      <HowItWorksStrip />
      <ExampleCardsStatic />
      <div className="rounded-xl border border-[var(--border)] bg-neutral-50/50 p-6 text-center dark:bg-neutral-950/30">
        <p className="text-sm text-[var(--foreground)]">Sign in to run an analysis from this page.</p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <Link
            href={`/login?next=${loginNext}`}
            className="inline-flex rounded-lg bg-[var(--foreground)] px-5 py-2.5 text-sm font-semibold text-[var(--background)]"
          >
            Sign in
          </Link>
          <Link
            href={`/register?next=${loginNext}`}
            className="inline-flex rounded-lg border border-[var(--border)] px-5 py-2.5 text-sm font-medium text-[var(--foreground)]"
          >
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
}

function LandingNoProject() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Hero />
      <HowItWorksStrip />
      <ExampleCardsStatic />
      <p className="text-center text-sm text-[var(--foreground)]">Create a project first, then return here to start.</p>
      <div className="text-center">
        <Link
          href="/projects"
          className="inline-flex rounded-lg bg-[var(--foreground)] px-5 py-2.5 text-sm font-semibold text-[var(--background)]"
        >
          Open projects
        </Link>
      </div>
    </div>
  );
}

function LandingWorkspace({ projectId }: { projectId: string }) {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Hero />
      <HowItWorksStrip />
      <div className="rounded-xl border border-[var(--border)] bg-neutral-50/50 p-6 text-center dark:bg-neutral-950/30">
        <p className="text-sm text-[var(--foreground)]">Go to your workspace chat to submit analysis questions.</p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <Link
            href={`/projects/${projectId}/chat`}
            className="inline-flex rounded-lg bg-[var(--foreground)] px-5 py-2.5 text-sm font-semibold text-[var(--background)]"
          >
            Open workspace chat
          </Link>
          <Link
            href={`/projects/${projectId}/runs`}
            className="inline-flex rounded-lg border border-[var(--border)] px-5 py-2.5 text-sm font-medium text-[var(--foreground)]"
          >
            View run history
          </Link>
        </div>
      </div>
    </div>
  );
}

type Props = {
  isAuthenticated: boolean;
  projectId: string | null;
};

export function LandingPageClient({ isAuthenticated, projectId }: Props) {
  if (!isAuthenticated) {
    return <LandingGuest />;
  }
  if (!projectId) {
    return <LandingNoProject />;
  }
  return <LandingWorkspace projectId={projectId} />;
}
