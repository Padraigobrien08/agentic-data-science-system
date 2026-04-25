import type { AnalysisRunStatus } from "@/lib/api/types";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";

export type GoalArchetype = "peer_compare" | "time_series" | "risk_signal" | "document_deep" | "general";

export type OutcomeSuggestionAction = {
  title: string;
  detail: string;
  href: string;
};

const PEER_RE = /\b(peer|peers|competitor|competitors|comp set|benchmark|benchmarking|vs\.?|versus|relative to|industry median|cohort)\b/i;
const TIME_RE =
  /\b(fy\d{2,4}|fiscal\s*year|quarter|q[1-4]\b|ttm|trailing|yoy|year[-\s]?over[-\s]?year|annual(ized)?|five\s*year|10[- ]?k|10[- ]?q|8[- ]?k|filing\s*period|time\s*horizon|historical)\b/i;
const RISK_RE =
  /\b(risk|risks|red flag|anomal(y|ies)|unusual|outlier|material weakness|covenant|litigation|fraud|going concern)\b/i;
const DOC_RE = /\b(footnote|md&a|segment|exhibit|schedule|10[- ]?k|10[- ]?q|8[- ]?k|proxy|def\s*14a)\b/i;

/** Deterministic goal “type” from free-text goal + tickers (no ML). */
export function classifyGoalArchetype(goalText: string, tickers: string[]): GoalArchetype {
  const hay = `${goalText}\n${tickers.join(" ")}`.toLowerCase();
  if (RISK_RE.test(hay)) return "risk_signal";
  if (PEER_RE.test(hay)) return "peer_compare";
  if (TIME_RE.test(hay)) return "time_series";
  if (DOC_RE.test(hay)) return "document_deep";
  return "general";
}

export function hasContextBudgetSignal(signals: PrimaryContextSignal[]): boolean {
  return signals.some((c) => c.id === "llm_context_budget" || /trim|clip|limits/i.test(c.label));
}

function archetypePartialLine(arch: GoalArchetype): { title: string; detail: string } {
  switch (arch) {
    case "peer_compare":
      return {
        title: "Broaden or refocus the peer set",
        detail: "Add tickers, name explicit peers, or relax the comparison so filings and panels have more overlap.",
      };
    case "time_series":
      return {
        title: "Clarify the time window",
        detail: "State fiscal years or quarters explicitly (for example FY22–FY24) so tools pull the right periods.",
      };
    case "risk_signal":
      return {
        title: "Tighten or widen risk criteria",
        detail: "Make triggers concrete (metric + threshold) or add narrative context the critic can verify.",
      };
    case "document_deep":
      return {
        title: "Point to a narrower document slice",
        detail: "Name filing type, section, or exhibit so retrieval targets text the pipeline can ground on.",
      };
    default:
      return {
        title: "Split into one measurable question",
        detail: "One objective per run (ratio, change, or yes/no) reduces partial coverage and weak evidence.",
      };
  }
}

function archetypeNoDataLine(arch: GoalArchetype, multiTicker: boolean): { title: string; detail: string } {
  if (multiTicker) {
    return {
      title: "Isolate with a single ticker first",
      detail: "Run one symbol to see which names lack usable panels, then expand the set once data shows up.",
    };
  }
  switch (arch) {
    case "peer_compare":
      return {
        title: "Expand peers or simplify the comparison",
        detail: "No-data often means no overlapping filings—try fewer peers or a broader industry benchmark.",
      };
    case "time_series":
      return {
        title: "Widen dates or refresh filings",
        detail: "Try a longer window, explicit FY labels, or a new run with “Refresh SEC cache” if panels were stale.",
      };
    case "risk_signal":
      return {
        title: "Relax filters or change indicators",
        detail: "Strict anomaly rules can return empty sets—loosen thresholds or name alternative risk lenses.",
      };
    case "document_deep":
      return {
        title: "Match filing type to what exists",
        detail: "Confirm the company files the form you asked for (10-K vs 20-F) and cite a reachable section.",
      };
    default:
      return {
        title: "Verify tickers and goal scope",
        detail: "Confirm symbols are SEC filers for this analysis type; shorten the ask so tools can return rows.",
      };
  }
}

export function buildOutcomeSuggestions(
  status: AnalysisRunStatus,
  goalText: string,
  tickers: string[],
  signals: PrimaryContextSignal[],
  weakEvidenceCount: number,
  projectId: string,
  traceHref: string,
): OutcomeSuggestionAction[] | null {
  if (status !== "partial_success" && status !== "no_data") {
    return null;
  }

  const arch = classifyGoalArchetype(goalText, tickers);
  const multiTicker = tickers.length > 1;
  const budget = hasContextBudgetSignal(signals);
  const weak = weakEvidenceCount > 0;

  const chatHref = `/projects/${projectId}/chat`;

  if (status === "partial_success") {
    const middle =
      budget
        ? {
            title: "Reduce scope for the next run",
            detail: "Context was trimmed—shorten the question, drop side topics, or split into two runs, then re-execute.",
            href: `${traceHref}#run-context-transparency`,
          }
        : weak
          ? {
              title: "Ground claims in linked artifacts",
              detail: "Open evidence roles in deep dive and attach stronger sources before treating takeaways as final.",
              href: `${traceHref}#run-artifacts`,
            }
          : { ...archetypePartialLine(arch), href: `${traceHref}#run-goal-plan` };

    return [
      {
        title: "Inspect critic & report phases",
        detail: "See which steps degraded, skipped, or disagreed with the plan before you change the goal.",
        href: `${traceHref}#run-agents`,
      },
      middle,
      {
        title: "Edit inputs and re-run",
        detail: "Adjust tickers or goal text in chat, or re-execute this run if only the pipeline needs another pass.",
        href: chatHref,
      },
    ];
  }

  const middleNoData = archetypeNoDataLine(arch, multiTicker);
  const middleHref = multiTicker ? `${traceHref}#run-artifacts` : `${traceHref}#run-goal-plan`;

  return [
    {
      title: "See which tools returned empty",
      detail: "Execution steps show MCP outcomes—use them to decide whether to change tickers, tools, or time range.",
      href: `${traceHref}#run-execution`,
    },
    { ...middleNoData, href: middleHref },
    {
      title: "Rephrase in chat, then submit a new run",
      detail: "Ask for a tighter SEC-scoped question, then create a fresh run from the composer with clearer constraints.",
      href: chatHref,
    },
  ];
}
