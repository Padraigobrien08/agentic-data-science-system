"use client";

import Link from "next/link";
import { useFormState, useFormStatus } from "react-dom";

import { createAnalysisRunForm } from "@/actions/runs";

type Example = {
  label: string;
  goal: string;
  tickers: string;
};

const EXAMPLES: Example[] = [
  {
    label: "Peer comparison",
    goal: "Compare AAPL and MSFT to peers; highlight relative margin pressure over the last eight quarters.",
    tickers: "AAPL, MSFT",
  },
  {
    label: "Anomaly screen",
    goal: "Flag unusual one-off moves in cash flow and operating margins; de-emphasize single-quarter noise.",
    tickers: "AAPL, MSFT, NVDA",
  },
  {
    label: "Deterioration trend",
    goal: "Detect persistent negative profitability trends; prioritize sustained patterns over one-off spikes.",
    tickers: "NVDA",
  },
];

function Hero() {
  return (
    <div className="space-y-3 text-center sm:text-left">
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--foreground)] sm:text-3xl">
        Company analysis on SEC data
      </h1>
      <p className="text-sm text-[var(--muted)]">
        Natural-language goals, resolved tickers, deterministic pipeline, artifact-backed answers.
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
          <span>Goal + tickers define orchestration input.</span>
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-[var(--muted)]">2.</span>
          <span>Pipeline executes tools and writes artifacts.</span>
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-[var(--muted)]">3.</span>
          <span>Open the run page for status, report, and evidence.</span>
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
        {EXAMPLES.map((ex) => (
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

function RunButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded-lg bg-[var(--foreground)] px-4 py-3 text-sm font-semibold text-[var(--background)] transition-opacity hover:opacity-90 disabled:opacity-50 sm:w-auto sm:min-w-[12rem]"
    >
      {pending ? "Running…" : "Run analysis"}
    </button>
  );
}

function ExampleChipsInteractive({ onSelect }: { onSelect: (ex: Example) => void }) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-[var(--muted)]">Examples</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            type="button"
            onClick={() => onSelect(ex)}
            className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs text-[var(--foreground)] transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-900"
          >
            <span className="font-medium">{ex.label}</span>
            <span className="mt-0.5 block line-clamp-2 text-[var(--muted)]">{ex.goal}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function LandingRunForm({ projectId }: { projectId: string }) {
  const action = createAnalysisRunForm.bind(null, projectId);
  const [state, formAction] = useFormState(action, {});

  const applyExample = (ex: Example) => {
    const goalEl = document.getElementById("landing-goal") as HTMLTextAreaElement | null;
    const tickEl = document.getElementById("landing-tickers") as HTMLInputElement | null;
    if (goalEl) goalEl.value = ex.goal;
    if (tickEl) tickEl.value = ex.tickers;
    goalEl?.focus();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Hero />
      <HowItWorksStrip />
      <form action={formAction} className="space-y-5">
        <input type="hidden" name="execute_now" value="on" />

        {state.error ? (
          <div
            role="alert"
            className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100"
          >
            {state.error}
          </div>
        ) : null}

        <div className="space-y-2">
          <label htmlFor="landing-goal" className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Analysis goal
          </label>
          <textarea
            id="landing-goal"
            name="goal"
            required
            rows={4}
            className="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
            placeholder="What should the run optimize for?"
            autoComplete="off"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="landing-tickers" className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Tickers
          </label>
          <input
            id="landing-tickers"
            name="tickers"
            type="text"
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 font-mono text-sm uppercase text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
            placeholder="AAPL, MSFT, NVDA"
            autoComplete="off"
          />
          <p className="text-[11px] text-[var(--muted)]">Comma-separated symbols; normalized server-side.</p>
        </div>

        <ExampleChipsInteractive onSelect={applyExample} />

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <RunButton />
          <Link href={`/projects/${projectId}/runs`} className="text-center text-xs text-[var(--muted)] underline sm:text-left">
            All runs in this project
          </Link>
        </div>
      </form>
    </div>
  );
}

type Props = {
  isAuthenticated: boolean;
  projectId: string | null;
};

/**
 * High-signal landing: goal + tickers + CTA, examples, minimal how-it-works.
 * Successful submit redirects to run answer (`createAnalysisRunForm` + execute_now).
 */
export function LandingPageClient({ isAuthenticated, projectId }: Props) {
  if (!isAuthenticated) {
    return <LandingGuest />;
  }
  if (!projectId) {
    return <LandingNoProject />;
  }
  return <LandingRunForm projectId={projectId} />;
}
