/**
 * Parse persisted ``llm_context_audit`` / nested ``llm_context_budget`` shapes from
 * ``meta_json.ai_agents.{critic,report}`` (see ``backend/agents/llm_context.audit_compact_context``).
 */

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Human-readable rows for UI (short label + tooltip). */
export type ContextBudgetRow = {
  key: string;
  shortLabel: string;
  /** Longer explanation for tables / title attributes. */
  tooltip: string;
};

/** Keys mirrored from ``llm_context._BUDGET_SIGNAL_KEYS`` + ``critic_truncated``. */
const BUDGET_KEY_COPY: Record<string, { short: string; tooltip: string }> = {
  resolved_companies_truncated: {
    short: "Companies sampled",
    tooltip: "Resolved company list was truncated for the model context budget.",
  },
  artifact_paths_roles_truncated: {
    short: "Artifact paths trimmed",
    tooltip: "Fewer artifact path roles were sent to the model than exist on the run.",
  },
  artifact_summary_roles_truncated: {
    short: "Artifact text trimmed",
    tooltip: "Artifact summary excerpts were shortened or fewer roles were included.",
  },
  user_request_truncated: {
    short: "Goal text trimmed",
    tooltip: "The analysis goal string was shortened before being sent to the model.",
  },
  plan_alignment_findings_truncated: {
    short: "Alignment list trimmed",
    tooltip: "Plan–goal alignment findings were truncated for the context budget.",
  },
  interpreted_goal_intent_rules_truncated: {
    short: "Intent rules trimmed",
    tooltip: "Interpreted goal intent rules were shortened for the model.",
  },
  interpreted_goal_template_rules_truncated: {
    short: "Template rules trimmed",
    tooltip: "Interpreted goal template rules were shortened for the model.",
  },
  interpreted_goal_user_goal_excerpt_truncated: {
    short: "Goal excerpt trimmed",
    tooltip: "The user goal excerpt in interpreted goal was shortened.",
  },
  errors_sample_truncated: {
    short: "Errors sampled",
    tooltip: "Only a subset of orchestration errors was included in model context.",
  },
  warnings_sample_truncated: {
    short: "Warnings sampled",
    tooltip: "Only a subset of orchestration warnings was included in model context.",
  },
  critic_truncated: {
    short: "Critic payload trimmed",
    tooltip: "Critic phase text fields were clipped for the context budget.",
  },
};

export function parseLlmContextBudgetDict(lcb: unknown): ContextBudgetRow[] {
  if (!isRecord(lcb)) return [];
  const out: ContextBudgetRow[] = [];
  for (const [k, v] of Object.entries(lcb)) {
    if (v !== true && v !== 1) continue;
    const meta = BUDGET_KEY_COPY[k];
    if (meta) {
      out.push({ key: k, shortLabel: meta.short, tooltip: meta.tooltip });
    }
  }
  return out;
}

/**
 * Rows to show for one phase's ``llm_context_audit`` object.
 * Prefers granular ``llm_context_budget`` booleans when present; otherwise umbrella flags.
 */
export function parseLlmContextAuditRows(audit: unknown): ContextBudgetRow[] {
  if (!isRecord(audit)) return [];
  const fromDict = parseLlmContextBudgetDict(audit.llm_context_budget);
  if (fromDict.length > 0) return fromDict;

  const rows: ContextBudgetRow[] = [];
  if (audit.llm_context_budget_applied === true) {
    rows.push({
      key: "llm_context_budget_applied",
      shortLabel: "Compact model context",
      tooltip:
        "At least one context-budget trim applied before this model call (see backend llm_context_budget).",
    });
  }
  if (audit.context_budget_truncated === true) {
    rows.push({
      key: "context_budget_truncated",
      shortLabel: "Summaries clipped",
      tooltip: "Artifact summary bundle was clipped by the context budget.",
    });
  }
  return rows;
}

export function parsePhaseAudits(ai: {
  critic?: unknown;
  report?: unknown;
} | null): { phase: "critic" | "report"; rows: ContextBudgetRow[] }[] {
  if (!ai) return [];
  const out: { phase: "critic" | "report"; rows: ContextBudgetRow[] }[] = [];
  for (const phase of ["critic", "report"] as const) {
    const meta = ai[phase];
    const raw = meta && isRecord(meta) ? (meta as Record<string, unknown>).llm_context_audit : undefined;
    const rows = parseLlmContextAuditRows(raw);
    if (rows.length > 0) out.push({ phase, rows });
  }
  return out;
}
