"use client";

import Link from "next/link";
import { useActionState } from "react";

import { enterDemoAction, submitInterestAction, type InterestState } from "@/actions/auth";
import { ANALYSIS_EXAMPLES } from "@/lib/analysis-examples";

const PLATFORM_PILLARS = [
  {
    title: "Run isolation",
    body: "Every execution stays attached to the right chat context, so artifacts and follow-up evidence do not drift.",
  },
  {
    title: "Evidence trail",
    body: "Answer pages, deep dives, and artifact routes point back to traceable outputs instead of opaque prompt-only summaries.",
  },
  {
    title: "Secure defaults",
    body: "Auth, telemetry, and payload exposure fail closed unless an operator intentionally opens a path.",
  },
  {
    title: "Truthful ops",
    body: "Queue health, worker status, and retention surfaces tell operators when the system is degraded instead of pretending everything is idle.",
  },
] as const;

const WORKFLOW_STEPS = [
  {
    label: "Scope the question",
    detail: "Write the analysis goal in plain language, then anchor it with company tickers and time-horizon hints.",
  },
  {
    label: "Run the pipeline",
    detail: "The planner selects deterministic tools, writes artifacts, and records attempt history with isolated paths.",
  },
  {
    label: "Inspect the proof",
    detail: "Open the run answer, dive into trace context, and verify the exact artifacts that support each conclusion.",
  },
] as const;

const PROOF_STRIP = [
  { value: "Isolated runs", label: "Each analysis keeps its own chat context and evidence." },
  { value: "Clear proof", label: "Answer pages link directly to files and trace context." },
  { value: "Honest ops", label: "Worker and retention surfaces report degraded state clearly." },
] as const;

type ActionConfig = {
  badge: string;
  title: string;
  note: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref: string;
  secondaryLabel: string;
};

function getActionConfig(isAuthenticated: boolean, projectId: string | null): ActionConfig {
  const loginNext = encodeURIComponent("/");
  if (!isAuthenticated) {
    return {
      badge: "Live demo",
      title: "Try it now — no sign-up.",
      note: "Jump straight into a sandbox workspace and run real SEC analysis. Leave your email only if you want product updates.",
      primaryHref: `/login?next=${loginNext}`,
      primaryLabel: "Sign in",
      secondaryHref: `/register?next=${loginNext}`,
      secondaryLabel: "Create account",
    };
  }

  if (!projectId) {
    return {
      badge: "Chat setup",
      title: "Create or open a chat before starting a run.",
      note: "Projects still hold persistence underneath, but the product now opens as chat with history and scope.",
      primaryHref: "/projects",
      primaryLabel: "Open chats",
      secondaryHref: "#workflow",
      secondaryLabel: "Review the workflow",
    };
  }

  return (
    {
      badge: "Chat ready",
      title: "Open the chat or review previous answers.",
      note: "Use the landing page as a clean entry point into live analysis, answer history, and evidence review.",
      primaryHref: `/projects/${projectId}/chat`,
      primaryLabel: "Open chat",
      secondaryHref: `/projects/${projectId}/chat`,
      secondaryLabel: "Review answer history",
    }
  );
}

function DemoEntry() {
  const [interest, interestAction] = useActionState(submitInterestAction, {} as InterestState);
  return (
    <div className="space-y-4">
      <form action={enterDemoAction}>
        <button
          type="submit"
          className="inline-flex min-h-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))] px-6 py-3 text-sm font-semibold text-white shadow-[0_18px_36px_-20px_rgba(31,111,255,0.56)] transition hover:-translate-y-0.5"
        >
          Enter the live demo →
        </button>
      </form>

      {interest.ok ? (
        <p className="text-sm font-medium text-[var(--foreground)]">Thanks — we&rsquo;ll keep you posted.</p>
      ) : (
        <form action={interestAction} className="flex flex-wrap items-center gap-2">
          <input
            name="email"
            type="email"
            required
            placeholder="you@work.com"
            aria-label="Email for product updates"
            className="min-h-11 min-w-[15rem] flex-1 rounded-full border border-[var(--border)] bg-white px-4 py-3 text-sm text-[var(--foreground)] outline-none transition focus:border-[var(--accent)] placeholder:text-[var(--muted)]"
          />
          <button
            type="submit"
            className="min-h-11 rounded-full border border-[var(--border)] bg-white px-4 py-3 text-sm font-semibold text-[var(--foreground)] transition hover:-translate-y-0.5"
          >
            Keep me posted
          </button>
        </form>
      )}
      {interest.error ? <p className="text-xs text-red-700">{interest.error}</p> : null}
      <p className="text-xs text-[var(--muted)]">
        No sign-up required. Email is optional — just a signal of interest.
      </p>
    </div>
  );
}

function ActionPanel({ config, isAuthenticated }: { config: ActionConfig; isAuthenticated: boolean }) {
  return (
    <div className="landing-reveal landing-reveal-delay-1 max-w-xl space-y-5">
      <div className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">{config.badge}</p>
        <p className="text-[1.02rem] font-semibold tracking-[-0.03em] text-[var(--foreground)]">{config.title}</p>
        <p className="text-sm leading-6 text-[var(--muted)]">{config.note}</p>
      </div>
      {isAuthenticated ? (
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href={config.primaryHref}
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))] px-5 py-3 text-sm font-semibold text-white shadow-[0_18px_36px_-20px_rgba(31,111,255,0.56)] transition hover:-translate-y-0.5"
          >
            {config.primaryLabel}
          </Link>
          <Link
            href={config.secondaryHref}
            className="inline-flex min-h-11 items-center justify-center rounded-full border border-[var(--border)] bg-white px-5 py-3 text-sm font-semibold text-[var(--foreground)] transition hover:-translate-y-0.5 hover:bg-white"
          >
            {config.secondaryLabel}
          </Link>
        </div>
      ) : (
        <DemoEntry />
      )}
    </div>
  );
}

function HeroPreview() {
  return (
    <div className="landing-reveal landing-reveal-delay-2 relative mx-auto w-full max-w-[34rem]">
      <div className="absolute -right-8 top-[-3rem] h-56 w-56 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.12),transparent_72%)] blur-3xl" />
      <div className="relative overflow-hidden rounded-[2rem] border border-[rgba(23,32,51,0.09)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(252,253,255,0.94))] p-6 shadow-[0_30px_80px_-56px_rgba(19,31,57,0.34)] sm:p-7">
        <div className="absolute inset-x-0 top-0 h-20 bg-[linear-gradient(90deg,rgba(37,99,235,0.05),rgba(255,255,255,0),rgba(255,138,91,0.05))]" />
        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--muted)]">Example run</p>
              <h2 className="mt-2 text-[1.72rem] font-semibold tracking-[-0.05em] text-[var(--foreground)]">AAPL vs MSFT</h2>
            </div>
            <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
              Run 014
            </span>
          </div>

          <div className="mt-6 space-y-6 rounded-[1.55rem] border border-[var(--border)] bg-white p-5">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Question</p>
                <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--accent-strong)]">
                  Last 8 quarters
                </span>
              </div>
              <p className="text-[1rem] leading-8 text-[var(--foreground)]">
                Compare AAPL and MSFT to peers on margin durability and free cash flow conversion.
              </p>
            </div>

            <div className="border-t border-[rgba(23,32,51,0.08)] pt-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Answer</p>
              <p className="mt-3 text-[1.12rem] font-medium leading-8 tracking-[-0.02em] text-[var(--foreground)]">
                Both companies remain above peer margins, but Apple shows the sharper recent softening in cash
                conversion.
              </p>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                The run links each conclusion to the answer page, panel data, and trace context from the same
                conversation.
              </p>
            </div>

            <div className="border-t border-[rgba(23,32,51,0.08)] pt-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Evidence</p>
                <span className="text-[11px] font-medium text-[var(--accent-strong)]">3 files</span>
              </div>
              <div className="mt-3 space-y-3">
                {[
                  ["Answer page", "peer_margin_report.md"],
                  ["Panel data", "cash_flow_panel.csv"],
                  ["Trace view", "trace.json"],
                ].map(([kind, name]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between gap-4 rounded-[1rem] bg-[rgba(248,250,252,0.9)] px-3 py-3 text-sm"
                  >
                    <span className="font-medium text-[var(--foreground)]">{name}</span>
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">{kind}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4 border-t border-[rgba(23,32,51,0.08)] pt-5 sm:grid-cols-3">
              {[
                ["Chat", "Primary"],
                ["Lease", "Heartbeat"],
                ["Payloads", "Privileged"],
              ].map(([label, value]) => (
                <div key={label} className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">{label}</p>
                  <p className="text-sm font-semibold text-[var(--foreground)]">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LandingHero({ config, isAuthenticated }: { config: ActionConfig; isAuthenticated: boolean }) {
  return (
    <section className="relative overflow-hidden px-2 py-6 sm:px-4 sm:py-10 lg:px-6 lg:py-14">
      <div className="absolute left-[-8%] top-[10%] h-56 w-56 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.1),transparent_68%)] blur-3xl" />
      <div className="absolute right-[-8%] top-[-2rem] h-[24rem] w-[24rem] rounded-full bg-[radial-gradient(circle,rgba(255,138,91,0.08),transparent_66%)] blur-3xl" />
      <div className="relative grid gap-12 lg:grid-cols-[minmax(0,1fr)_35rem] lg:items-center">
        <div className="max-w-[44rem] pt-2">
          <p className="landing-reveal text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
            Evidence-first SEC analysis
          </p>

          <h1 className="landing-reveal landing-reveal-delay-1 mt-6 max-w-[11ch] text-[clamp(3.1rem,6.2vw,5.2rem)] font-semibold leading-[0.95] tracking-[-0.075em] text-[var(--foreground)]">
            Ask a company question.
            <span className="mt-2 block text-[rgba(23,32,51,0.58)]">Inspect the answer.</span>
          </h1>

          <p className="landing-reveal landing-reveal-delay-1 mt-8 max-w-[34rem] text-[1.05rem] leading-8 text-[var(--muted)]">
            Run deterministic SEC analysis from one chat, then open the answer, files, and trace context
            that support it.
          </p>

          <div className="mt-10">
            <ActionPanel config={config} isAuthenticated={isAuthenticated} />
          </div>

          <div className="landing-reveal landing-reveal-delay-2 mt-12 grid gap-5 border-t border-[rgba(23,32,51,0.08)] pt-6 sm:grid-cols-3">
            {PROOF_STRIP.map((item) => (
              <div key={item.value} className="space-y-2 sm:border-l sm:border-[rgba(23,32,51,0.08)] sm:pl-4 sm:first:border-l-0 sm:first:pl-0">
                <p className="text-[1rem] font-semibold tracking-[-0.03em] text-[var(--foreground)]">{item.value}</p>
                <p className="max-w-[18rem] text-sm leading-6 text-[var(--muted)]">{item.label}</p>
              </div>
            ))}
          </div>
        </div>

        <HeroPreview />
      </div>
    </section>
  );
}

function PlatformPillars() {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {PLATFORM_PILLARS.map((pillar, index) => (
        <div
          key={pillar.title}
          className="glass-panel rounded-[1.85rem] border border-white/75 p-5 transition hover:-translate-y-1 hover:shadow-[0_34px_80px_-54px_rgba(19,31,57,0.72)]"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              0{index + 1}
            </span>
            <span className="h-10 w-10 rounded-2xl bg-[linear-gradient(135deg,rgba(31,111,255,0.12),rgba(255,138,91,0.16))]" />
          </div>
          <h2 className="mt-8 text-xl font-semibold tracking-[-0.03em] text-[var(--foreground)]">{pillar.title}</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{pillar.body}</p>
        </div>
      ))}
    </section>
  );
}

function WorkflowSection() {
  return (
    <section id="workflow" className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">How it works</p>
        <h2 className="font-display max-w-xl text-4xl leading-tight text-[var(--foreground)] sm:text-5xl">
          A layered workflow, not a thin wrapper around a chat box.
        </h2>
        <p className="max-w-xl text-base leading-7 text-[var(--muted)]">
          The landing page should set the expectation correctly: this product scopes the question, runs deterministic
          analysis, and preserves the proof. That is the story the interface needs to tell immediately.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {WORKFLOW_STEPS.map((step, index) => (
          <div key={step.label} className="glass-panel rounded-[1.9rem] border border-white/75 p-5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Step 0{index + 1}
            </span>
            <h3 className="mt-6 text-xl font-semibold tracking-[-0.03em] text-[var(--foreground)]">{step.label}</h3>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{step.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ExampleShowcase() {
  return (
    <section id="examples" className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Prompt examples</p>
          <h2 className="font-display text-4xl leading-tight text-[var(--foreground)] sm:text-5xl">
            Phrase the business question, not the syntax.
          </h2>
        </div>
        <p className="max-w-xl text-sm leading-6 text-[var(--muted)]">
          These examples frame the kinds of analyses the planner already supports. The page should make them feel like
          launch points, not documentation leftovers.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {ANALYSIS_EXAMPLES.map((example, index) => (
          <div
            key={example.label}
            className="group glass-panel rounded-[1.9rem] border border-white/75 p-5 transition hover:-translate-y-1 hover:shadow-[0_30px_80px_-56px_rgba(19,31,57,0.76)]"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
                Example 0{index + 1}
              </span>
              <div className="flex flex-wrap justify-end gap-2">
                {example.tickers.split(",").map((ticker) => (
                  <span
                    key={`${example.label}-${ticker}`}
                    className="rounded-full border border-[var(--border)] bg-white/90 px-3 py-1 text-[11px] font-semibold text-[var(--foreground)]"
                  >
                    {ticker.trim()}
                  </span>
                ))}
              </div>
            </div>
            <h3 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-[var(--foreground)]">{example.label}</h3>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{example.goal}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ClosingStrip({ config, isAuthenticated }: { config: ActionConfig; isAuthenticated: boolean }) {
  return (
    <section className="relative overflow-hidden rounded-[2.2rem] border border-white/75 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(255,255,255,0.62))] px-6 py-7 shadow-[0_34px_90px_-56px_rgba(19,31,57,0.72)] sm:px-8 sm:py-8">
      <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top,rgba(31,111,255,0.15),transparent_58%)] lg:block" />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">Why this page matters</p>
          <h2 className="font-display mt-3 text-3xl leading-tight text-[var(--foreground)] sm:text-4xl">
            The product is stronger than the current landing page suggests.
          </h2>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)] sm:text-base">
            This redesign frames the system as a premium, evidence-led analysis platform instead of a generic internal
            tool. The landing experience now sells trust, workflow depth, and product maturity in the first screen.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {isAuthenticated ? (
            <>
              <Link
                href={config.primaryHref}
                className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))] px-5 py-3 text-sm font-semibold text-white shadow-[0_18px_40px_-18px_rgba(31,111,255,0.8)] transition hover:-translate-y-0.5"
              >
                {config.primaryLabel}
              </Link>
              <Link
                href={config.secondaryHref}
                className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-white/85 px-5 py-3 text-sm font-semibold text-[var(--foreground)] transition hover:-translate-y-0.5 hover:bg-white"
              >
                {config.secondaryLabel}
              </Link>
            </>
          ) : (
            <form action={enterDemoAction}>
              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))] px-5 py-3 text-sm font-semibold text-white shadow-[0_18px_40px_-18px_rgba(31,111,255,0.8)] transition hover:-translate-y-0.5"
              >
                Enter the live demo →
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

type Props = {
  isAuthenticated: boolean;
  projectId: string | null;
};

export function LandingPageClient({ isAuthenticated, projectId }: Props) {
  const config = getActionConfig(isAuthenticated, projectId);

  return (
    <div className="mx-auto w-full max-w-[96rem] px-3 sm:px-5 lg:px-6 space-y-8 sm:space-y-10">
      <LandingHero config={config} isAuthenticated={isAuthenticated} />
      <PlatformPillars />
      <WorkflowSection />
      <ExampleShowcase />
      <ClosingStrip config={config} isAuthenticated={isAuthenticated} />
    </div>
  );
}
