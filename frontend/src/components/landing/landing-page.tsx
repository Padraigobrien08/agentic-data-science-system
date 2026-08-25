import Link from "next/link";

import { enterDemoAction } from "@/actions/auth";
import { InterestForm } from "@/components/landing/interest-form";
import { DEMO_DETAILS } from "@/lib/demo-static/generated";
import { PRODUCT_NAME } from "@/lib/brand";
import { buildLandingCounts, buildLandingTrace, type TraceLine } from "@/lib/landing-trace";

const REPO_URL = "https://github.com/Padraigobrien08/agentic-data-science-system";

/** The run the hero shows. Live SEC filings, and the one that overturns its own premise. */
const FLAGSHIP_SLUG = "edgar-margin-vs-growth";

/**
 * Loop properties, in the order the README states them. Each is a claim the repository can
 * be held to, so the wording tracks the README rather than paraphrasing it upward.
 *
 * The README also lists **Self-checking** (the loop refusing to conclude while two of its own
 * claims disagree). It is omitted here because this strip is a five-column rule grid by
 * design; a sixth cell would leave an orphan. Worth revisiting — it is arguably a stronger
 * claim than Comparable.
 */
const PILLARS = [
  {
    label: "Bounded",
    body: "Budgets on experiments, iterations, wall time and estimated spend, with deterministic safety caps above them.",
  },
  {
    label: "Reproducible",
    body: "Deterministic IDs and per-iteration checkpoints: a resumed run reaches the same state as an uninterrupted one.",
  },
  {
    label: "Comparable",
    body: "Replay a run under a different model, prompt or budget, then diff it. Did the answer change, or only the route to it?",
  },
  {
    label: "Measured",
    body: "An agency suite scores reasoning quality: conclude, revise, or decline. On the hard tier the baseline scores 0% and gpt-5.4-mini 60%.",
  },
  {
    label: "Observable",
    body: "Every decision emits a span, a structured log and metrics through one observer seam.",
  },
] as const;

/**
 * All ten components, in loop order, with the four that actually call a model
 * marked. The model-backed set is the `AgentPolicy` contract — interpretation,
 * hypothesis generation, experiment *selection* and critique. `revise_claims`
 * is thresholded arithmetic over recorded evidence, not a model call.
 */
const COMPONENTS = [
  { name: "interpret_goal", kind: "model-backed" },
  { name: "generate_hypotheses", kind: "model-backed" },
  { name: "plan_experiments", kind: "deterministic" },
  { name: "select_experiment", kind: "model-backed" },
  { name: "run_experiment", kind: "deterministic" },
  { name: "record_evidence", kind: "deterministic" },
  { name: "revise_claims", kind: "deterministic" },
  { name: "critique", kind: "model-backed" },
  { name: "terminate", kind: "typed reason" },
  { name: "synthesize_conclusion", kind: "deterministic" },
] as const;

const SURFACES = [
  {
    name: "platform-mcp",
    body: "stdio or streamable HTTP · per-caller bearer auth on tool calls · rate limited",
  },
  { name: "edgar-mcp", body: "the deterministic analysis tools themselves" },
  { name: "openapi.json", body: "committed contract, enforced in CI" },
] as const;

/**
 * Verbatim from the README's "Known limits". A page whose thesis is honest
 * uncertainty cannot soften these without undermining itself.
 */
const LIMITS = [
  "Declining an unanswerable question is still a model judgement. What follows is deterministic — the loop stops, claims nothing, runs nothing — but a broken premise it does not notice is not caught.",
  "Two of the loop's four model-backed decisions are covered by the agency suite. A fair case for select_experiment is not constructible, and that is documented.",
  "Mutual exclusivity is read from the goal's phrasing, not its meaning. Claims that are incompatible but not posed as alternatives still fall to the critic, which is best-effort.",
  "Single replica. Auth rate limiting is in-process, so a second API replica would enforce it independently.",
] as const;

type Cta = {
  primaryHref: string;
  primaryLabel: string;
  /** True when the primary action posts a server action instead of navigating. */
  primaryIsForm: boolean;
  /**
   * Whether to offer the email capture. It posts to `/v1/interest`, so it is
   * offered only where a live backend exists and the visitor is not already
   * signed in — never in the static export, which has no backend to receive it.
   */
  showInterest: boolean;
  navLabel: string;
  navHref: string;
  closingNote: string;
};

const NUMBER_WORDS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

/**
 * "five recorded investigations", counted from the published set rather than written down.
 *
 * The count was hardcoded as "two" in four places and went stale the moment a third demo was
 * published — on a page whose whole claim is that its numbers are not made up. A count of 0
 * means it could not be determined (no backend), so the phrasing drops the number rather
 * than asserting there are none.
 */
function recordedRuns(count: number): string {
  if (count < 1) return "recorded investigations";
  const word = NUMBER_WORDS[count] ?? String(count);
  return `${word} recorded investigation${count === 1 ? "" : "s"}`;
}

function sentenceCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function getCta(
  isAuthenticated: boolean,
  projectId: string | null,
  staticShowcase: boolean,
  demoCount: number,
  demoHref: string,
): Cta {
  const runs = recordedRuns(demoCount);
  if (staticShowcase && !isAuthenticated) {
    return {
      primaryHref: demoHref,
      primaryLabel: "Explore recorded runs",
      primaryIsForm: false,
      showInterest: false,
      navLabel: "recorded runs →",
      navHref: demoHref,
      closingNote:
        `${sentenceCase(runs)}, published exactly as they ended. Not all of them reached an answer.`,
    };
  }
  if (!isAuthenticated) {
    return {
      primaryHref: demoHref,
      primaryLabel: "Enter the live demo",
      primaryIsForm: true,
      showInterest: true,
      navLabel: "live demo →",
      navHref: demoHref,
      closingNote:
        `Run it yourself, or read the ${runs} published exactly as they ended. Not all of them reached an answer.`,
    };
  }
  if (!projectId) {
    return {
      primaryHref: "/projects",
      primaryLabel: "Open chats",
      primaryIsForm: false,
      showInterest: false,
      navLabel: "chats →",
      navHref: "/projects",
      closingNote: `Start a chat to commission a run, or read the ${runs}.`,
    };
  }
  return {
    primaryHref: `/projects/${projectId}/chat`,
    primaryLabel: "Open chat",
    primaryIsForm: false,
    showInterest: false,
    navLabel: "open chat →",
    navHref: `/projects/${projectId}/chat`,
    closingNote: `Pick up where you left off, or read the ${runs}.`,
  };
}

const SOLID_BTN =
  "inline-flex h-10 items-center whitespace-nowrap rounded-lg bg-[var(--ld-ink)] px-[18px] text-sm font-semibold text-[#0b0e13] transition hover:bg-white";
const GHOST_BTN =
  "inline-flex h-10 items-center whitespace-nowrap rounded-lg border border-white/20 px-[18px] text-sm text-[var(--ld-ink)] transition hover:border-white/40 hover:bg-white/5";

function PrimaryCta({ cta }: { cta: Cta }) {
  if (cta.primaryIsForm) {
    return (
      <form action={enterDemoAction}>
        <button type="submit" className={SOLID_BTN}>
          {cta.primaryLabel}
        </button>
      </form>
    );
  }
  return (
    <Link href={cta.primaryHref} className={SOLID_BTN}>
      {cta.primaryLabel}
    </Link>
  );
}

function Header({ cta, userEmail }: { cta: Cta; userEmail: string | null }) {
  return (
    <div className="sticky top-0 z-20 border-b border-[var(--ld-line)] bg-[rgba(11,14,19,0.72)] backdrop-blur-[18px]">
      <div className="mx-auto flex h-14 max-w-[1240px] items-center justify-between gap-4 px-5 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="h-4 w-4 rounded bg-[linear-gradient(135deg,#7dd3fc,#818cf8)]" />
          <span className="whitespace-nowrap text-[13.5px] font-semibold tracking-[-0.02em]">
            {PRODUCT_NAME}
          </span>
          <span className="font-mono rounded border border-[var(--ld-line)] px-[7px] py-0.5 text-[10.5px] text-[var(--ld-muted)]">
            v1
          </span>
        </Link>
        <div className="font-mono flex items-center gap-[22px] text-[11.5px] text-[var(--ld-muted)]">
          <a href="#loop" className="hidden transition hover:text-[var(--ld-ink)] md:inline">
            /loop
          </a>
          <a href="#mcp" className="hidden transition hover:text-[var(--ld-ink)] md:inline">
            /mcp
          </a>
          <a href="#evals" className="hidden transition hover:text-[var(--ld-ink)] md:inline">
            /evals
          </a>
          <a href="#limits" className="hidden transition hover:text-[var(--ld-ink)] md:inline">
            /limits
          </a>
          {userEmail ? (
            <span className="hidden max-w-[14rem] truncate text-[var(--ld-dim)] lg:inline" title={userEmail}>
              {userEmail}
            </span>
          ) : null}
          <Link
            href={cta.navHref}
            className="whitespace-nowrap rounded-md bg-[var(--ld-ink)] px-[11px] py-[5px] font-semibold text-[#0b0e13] transition hover:bg-white"
          >
            {cta.navLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}

const TONE_CLASS: Record<TraceLine["tone"], string> = {
  muted: "text-[var(--ld-dim)]",
  tool: "text-[var(--ld-indigo)]",
  supported: "text-[var(--ld-green)]",
  rejected: "text-[var(--ld-red)]",
  terminal: "text-[var(--ld-blue)]",
};

/**
 * The real `edgar-margin-vs-growth` run, read out of the published export at build time.
 *
 * This panel used to be hand-typed, with a comment asserting that every figure in it matched
 * the export. The counts did; the iteration stamps had drifted by four, and one line
 * advertised evidence as "artifact · linked" when the export's evidence carried no such link
 * at all. Deriving it is not a refactor for tidiness — it is the difference between a page
 * that claims its numbers are checkable and a page whose numbers are checked.
 */
function TracePanel() {
  const detail = DEMO_DETAILS[FLAGSHIP_SLUG];
  if (!detail) return null;
  const lines = buildLandingTrace(detail);

  return (
    <div className="font-mono w-full overflow-hidden rounded-xl border border-[var(--ld-line-strong)] bg-[var(--ld-cell)] text-xs text-[#d3d7de] shadow-[var(--ld-shadow)]">
      <div className="flex justify-between border-b border-[var(--ld-line)] bg-[var(--ld-cell-raised)] px-6 py-3.5">
        <span>investigation.trace</span>
        <span className="text-[var(--ld-dim)]">{FLAGSHIP_SLUG}</span>
      </div>
      <div className="overflow-x-auto px-6 py-5 leading-[2.1]">
        {lines.map((line, i) => (
          <p key={`${line.event}-${i}`} className="whitespace-nowrap">
            <span className="text-[var(--ld-dim)]">{line.stamp}</span> {line.event}{" "}
            <span className={TONE_CLASS[line.tone]}>{line.detail}</span>
          </p>
        ))}
      </div>
      <div className="border-t border-[var(--ld-line)] bg-[var(--ld-cell-raised)] px-6 py-3.5 text-[var(--ld-muted)]">
        {buildLandingCounts(detail)}
      </div>
    </div>
  );
}

function Hero({ cta }: { cta: Cta }) {
  return (
    <div className="border-b border-[var(--ld-line)]">
      <div className="mx-auto grid max-w-[1240px] lg:grid-cols-2">
        <div className="border-b border-[var(--ld-line)] px-5 pb-11 pt-14 lg:border-b-0 lg:border-r lg:px-8 lg:pt-[72px]">
          <p className="font-mono m-0 text-[11px] uppercase tracking-[0.1em] text-[var(--ld-blue)]">
            The LLM plans. Deterministic code computes.
          </p>
          <h1 className="mt-5 text-balance text-[clamp(2.5rem,7vw,60px)] font-semibold leading-[1.02] tracking-[-0.045em]">
            No number here was written by a model.
          </h1>
          <p className="mt-6 max-w-[460px] text-pretty text-base leading-[1.65] text-[var(--ld-muted)]">
            A production-grade agentic loop, with budgets it respects, IDs you can rerun against, a
            checkpoint on every iteration, and a stated reason for stopping. The trace walks from
            the conclusion all the way down to the rows, and it never skips a step.
          </p>
          <div className="mt-[30px] flex flex-wrap gap-2.5">
            <PrimaryCta cta={cta} />
            <a href={REPO_URL} target="_blank" rel="noreferrer" className={GHOST_BTN}>
              Read the code
            </a>
          </div>
          {/* The design reserves a 44px meta row here under the CTAs. */}
          {cta.showInterest ? (
            <div className="mt-11 max-w-[460px]">
              <InterestForm />
            </div>
          ) : null}
        </div>
        <div className="flex items-center px-5 pb-11 pt-11 lg:px-8 lg:pt-[72px]">
          <TracePanel />
        </div>
      </div>
    </div>
  );
}

function Pillars() {
  return (
    <div className="border-b border-[var(--ld-line)]">
      <div className="mx-auto max-w-[1240px] overflow-hidden">
        <div className="ld-rule-grid grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5">
          {/* Five cells into two columns leaves a hole; the last one takes the
              spare column back until the row is five wide. */}
          {PILLARS.map((pillar) => (
            <div
              key={pillar.label}
              className="px-6 py-[30px] sm:last:col-span-2 xl:last:col-span-1"
            >
              <p className="font-mono m-0 text-[10.5px] uppercase tracking-[0.1em] text-[var(--ld-blue)]">
                {pillar.label}
              </p>
              <p className="mt-3 text-[13.5px] leading-[1.55] text-[var(--ld-muted)]">{pillar.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LoopSection() {
  return (
    <div id="loop" className="border-b border-[var(--ld-line)]">
      <div className="mx-auto max-w-[1240px] px-5 py-16 lg:px-8">
        <div className="flex flex-wrap items-baseline justify-between gap-10">
          <h2 className="m-0 max-w-[16ch] text-[clamp(1.75rem,4vw,34px)] font-semibold leading-[1.12] tracking-[-0.035em]">
            Ten components, one typed contract each.
          </h2>
          <p className="m-0 max-w-[420px] text-sm leading-[1.6] text-[var(--ld-dim)]">
            The loop package imports nothing from the backend. No structlog, no OpenTelemetry, no
            ORM. That is why the same loop runs over filings and over a CSV upload without
            special-casing either.
          </p>
        </div>
        {/* 2 and 5 are the only column counts that divide ten evenly — anything
            between leaves an orphan row that reads as a rendering fault. */}
        <div className="mt-[34px] grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-[var(--ld-line)] bg-[var(--ld-line)] xl:grid-cols-5">
          {COMPONENTS.map((component) => {
            const isModel = component.kind === "model-backed";
            return (
              <div
                key={component.name}
                className={isModel ? "bg-[var(--ld-tint)] p-5" : "bg-[#0d1015] p-5"}
              >
                <p
                  className={`font-mono m-0 break-all text-[12.5px] ${
                    isModel ? "text-[var(--ld-indigo-ink)]" : "text-[var(--ld-ink)]"
                  }`}
                >
                  {component.name}
                </p>
                <p
                  className={`mt-[7px] text-[12.5px] ${
                    isModel
                      ? "text-[var(--ld-indigo)]"
                      : component.kind === "typed reason"
                        ? "text-[var(--ld-green)]"
                        : "text-[var(--ld-dim)]"
                  }`}
                >
                  {component.kind}
                </p>
              </div>
            );
          })}
        </div>
        <p className="mt-3.5 text-[12.5px] text-[var(--ld-dim)]">
          Tinted cells are the four model-backed decisions; the rest is code.
        </p>
      </div>
    </div>
  );
}

function McpSection() {
  return (
    <div
      id="mcp"
      className="border-b border-[var(--ld-line)] bg-[linear-gradient(180deg,rgba(129,140,248,0.05),transparent_60%)]"
    >
      <div className="mx-auto grid max-w-[1240px] items-stretch gap-14 px-5 py-20 lg:grid-cols-[0.92fr_1.08fr] lg:px-8">
        <div className="flex w-full flex-col">
          <p className="font-mono m-0 text-[11px] uppercase tracking-[0.1em] text-[var(--ld-blue)]">
            Integration surface
          </p>
          <h2 className="mt-4 text-[clamp(1.9rem,4.5vw,40px)] font-semibold leading-[1.1] tracking-[-0.038em]">
            A custom MCP server over an open API.
          </h2>
          <p className="mt-5 max-w-[480px] text-pretty text-base leading-[1.7] text-[var(--ld-muted)]">
            Everything goes through one versioned HTTP contract, and there is no privileged back
            door. That is what makes the MCP server safe to host. External agents commission
            investigations and read hypotheses, evidence and artifacts as MCP tools and resources.
          </p>
          <div className="mt-9 flex flex-col gap-px overflow-hidden rounded-[10px] border border-[var(--ld-line)] bg-[var(--ld-line)] lg:mt-auto">
            {SURFACES.map((surface) => (
              <div
                key={surface.name}
                className="grid gap-2 bg-[#0d1015] px-[18px] py-4 sm:grid-cols-[130px_1fr] sm:items-baseline sm:gap-[18px]"
              >
                <span className="font-mono whitespace-nowrap text-[12.5px] text-[var(--ld-ink)]">
                  {surface.name}
                </span>
                <span className="text-[12.5px] leading-[1.5] text-[var(--ld-dim)]">{surface.body}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-col overflow-hidden rounded-[14px] border border-[var(--ld-line-strong)] bg-white/[0.03] shadow-[var(--ld-shadow)]">
          <div className="flex items-center justify-between gap-4 border-b border-[var(--ld-line)] bg-[var(--ld-cell-raised)] px-5 py-[13px]">
            <div className="flex items-center gap-2.5">
              <span className="h-[7px] w-[7px] rounded-full bg-[var(--ld-green)]" />
              <span className="font-mono text-[11.5px] text-[var(--ld-muted)]">
                mcp · session established
              </span>
            </div>
            <span className="font-mono text-[11px] text-[var(--ld-dim)]">bearer ••••7f3a</span>
          </div>
          <div className="font-mono flex-1 overflow-x-auto px-6 pb-[26px] pt-6 text-[12.5px] leading-[1.95]">
            <p className="m-0 text-[var(--ld-dim)]"># commission a run as any MCP client</p>
            <p className="mt-1.5 whitespace-nowrap text-[var(--ld-ink)]">
              tools/call <span className="text-[var(--ld-blue)]">start_investigation</span>
            </p>
            <p className="m-0 whitespace-nowrap text-[var(--ld-muted)]">
              <span className="text-[var(--ld-dim)]">→</span> investigation_id, budget, adapter
            </p>
            {/*
              Tool and resource names below are the ones `backend/mcp/server.py` actually
              registers, and `landing-mcp.test.ts` checks them against it. They used to be
              neither: the panel showed `resources/read hypotheses` and `evidence/7`, and the
              server exposes no such resources — hypotheses and evidence are tools, and the
              only two resources are `artifact://` and `investigation://{id}/conclusion`. A
              reader who tried to follow this transcript would have got a method-not-found.
            */}
            <p className="mt-5 whitespace-nowrap text-[var(--ld-ink)]">
              tools/call <span className="text-[var(--ld-blue)]">list_hypotheses</span>
            </p>
            <p className="m-0 whitespace-nowrap text-[var(--ld-muted)]">
              <span className="text-[var(--ld-dim)]">→</span> 2 claims ·{" "}
              <span className="text-[var(--ld-green)]">supported</span>,{" "}
              <span className="text-[var(--ld-red)]">rejected</span>
            </p>
            <p className="mt-5 whitespace-nowrap text-[var(--ld-ink)]">
              resources/read{" "}
              <span className="text-[var(--ld-blue)]">investigation://{"{id}"}/conclusion</span>
            </p>
            <p className="m-0 whitespace-nowrap text-[var(--ld-muted)]">
              <span className="text-[var(--ld-dim)]">→</span> evidence → artifact ref → rows
            </p>
          </div>
          <div className="grid grid-cols-1 gap-px border-t border-[var(--ld-line)] bg-[var(--ld-line)] sm:grid-cols-3">
            {[
              ["tools", "commission · inspect"],
              ["resources", "hypotheses · evidence"],
              ["transport", "stdio · HTTP"],
            ].map(([label, value]) => (
              <div key={label} className="bg-[#0d1015] px-[18px] py-3.5">
                <p className="font-mono m-0 text-[11px] text-[var(--ld-dim)]">{label}</p>
                <p className="mt-[5px] text-[13px] text-[var(--ld-ink)]">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function EvalsAndLimits() {
  return (
    <div className="border-b border-[var(--ld-line)]">
      <div className="mx-auto grid max-w-[1240px] lg:grid-cols-2">
        <div
          id="evals"
          className="border-b border-[var(--ld-line)] px-5 py-14 lg:border-b-0 lg:border-r lg:px-8"
        >
          <p className="font-mono m-0 text-[10.5px] uppercase tracking-[0.1em] text-[var(--ld-blue)]">
            Observability
          </p>
          <h2 className="mt-3.5 text-[clamp(1.6rem,3.5vw,30px)] font-semibold leading-[1.15] tracking-[-0.035em]">
            Every decision emits a span.
          </h2>
          <p className="mt-4 text-[14.5px] leading-[1.65] text-[var(--ld-muted)]">
            Traces, structured logs and metrics flow through one observer seam, so the loop package
            itself imports no instrumentation and still runs standalone and offline.
          </p>
          <p className="font-mono mt-4 overflow-x-auto text-xs text-[var(--ld-dim)]">
            agent.investigation → agent.iteration.N → agent.component.{"{name}"}
          </p>
          <div className="mt-[22px] grid grid-cols-1 gap-px overflow-hidden rounded-[10px] border border-[var(--ld-line)] bg-[var(--ld-line)] sm:grid-cols-2">
            <div className="bg-[#0d1015] p-[18px]">
              <p className="m-0 text-2xl font-semibold tracking-[-0.03em]">1.4</p>
              <p className="mt-1.5 text-[12.5px] text-[var(--ld-dim)]">
                Median iterations, so it really does iterate rather than one-shot.
              </p>
            </div>
            <div className="bg-[#0d1015] p-[18px]">
              <p className="m-0 text-2xl font-semibold tracking-[-0.03em]">210</p>
              <p className="mt-1.5 text-[12.5px] text-[var(--ld-dim)]">
                Seeded local investigations over 30 minutes — not production traffic.
              </p>
            </div>
          </div>
        </div>
        <div id="limits" className="px-5 py-14 lg:px-8">
          <p className="font-mono m-0 text-[10.5px] uppercase tracking-[0.1em] text-[var(--ld-amber)]">
            Known limits
          </p>
          <h2 className="mt-3.5 text-[clamp(1.6rem,3.5vw,30px)] font-semibold leading-[1.15] tracking-[-0.035em]">
            Stated plainly, on the landing page.
          </h2>
          <div className="mt-[18px] flex flex-col gap-3 text-sm leading-[1.6] text-[var(--ld-muted)]">
            {LIMITS.map((limit) => (
              <p key={limit} className="m-0 border-l-2 border-[rgba(245,158,11,0.42)] pl-3.5">
                {limit}
              </p>
            ))}
          </div>
          <p className="mt-[18px] text-[13px] text-[var(--ld-dim)]">
            A system that reports uncertainty honestly should do the same about itself.
          </p>
        </div>
      </div>
    </div>
  );
}

function Closing({ cta }: { cta: Cta }) {
  return (
    <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-10 px-5 py-14 lg:px-8">
      <div>
        <h2 className="m-0 text-[clamp(1.6rem,3.5vw,30px)] font-semibold tracking-[-0.035em]">
          Read the trace before you believe the claim.
        </h2>
        <p className="mt-2.5 text-sm text-[var(--ld-dim)]">{cta.closingNote}</p>
      </div>
      <div className="flex flex-none flex-wrap gap-2.5">
        <PrimaryCta cta={cta} />
        <a href={REPO_URL} target="_blank" rel="noreferrer" className={GHOST_BTN}>
          GitHub
        </a>
      </div>
    </div>
  );
}

type Props = {
  isAuthenticated: boolean;
  projectId: string | null;
  /** True when serving the committed static export with no live backend (D9). */
  staticShowcase?: boolean;
  userEmail?: string | null;
  /** How many investigations are published, counted rather than written down. */
  demoCount?: number;
  /** Where "Explore recorded runs" goes — a conversation, not the index. */
  demoHref?: string;
};

export function LandingPage({
  isAuthenticated,
  projectId,
  staticShowcase = false,
  userEmail = null,
  demoCount = 0,
  demoHref = "/demos",
}: Props) {
  const cta = getCta(isAuthenticated, projectId, staticShowcase, demoCount, demoHref);

  return (
    <div className="landing-dark min-h-screen w-full">
      <Header cta={cta} userEmail={userEmail} />
      <Hero cta={cta} />
      <Pillars />
      <LoopSection />
      <McpSection />
      <EvalsAndLimits />
      <Closing cta={cta} />
    </div>
  );
}
