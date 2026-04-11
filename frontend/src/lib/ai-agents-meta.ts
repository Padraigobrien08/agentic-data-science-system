/**
 * Parse `analysis_run.meta_json.ai_agents` for transparent agent UI.
 */

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export type PlanningStepWire = {
  order: number;
  tool_name: string;
  label?: string;
  tool_input?: Record<string, unknown>;
};

export type AgentPhaseMeta = {
  skipped?: boolean;
  reason?: string;
  error?: string;
  model_call_id?: string;
  phase_status?: string;
  phase_output?: unknown;
  result?: unknown;
  [key: string]: unknown;
};

/** Typed deterministic plan–goal alignment (critic phase; matches ``compute_plan_alignment_findings``). */
export type PlanAlignmentFindingWire = {
  code?: string;
  severity?: string;
  detail?: string;
};

/** Rule-derived planning transparency (matches backend ``build_planning_transparency``). */
export type PlanningTransparencyWire = {
  contract_version?: string;
  present?: boolean;
  planning_rationale_summary?: string;
  plan_template_id?: string | null;
  goal_code?: string;
  /** Coarse intent from ``intent.py`` (before template-specific ``goal_code``). */
  orchestration_intent?: string | null;
  intent_rules_matched?: string[];
  selected_signal_preferences?: {
    primary_analysis_mode?: string;
    preferred_signal_style?: string;
    directional_focus?: string;
    time_focus?: string;
    peer_requirement?: string;
    priority_metrics?: string[];
    preference_rules_matched?: string[];
  } | null;
  priority_metrics?: string[];
  directional_focus?: string | null;
  preferred_signal_style?: string | null;
  peer_requirement?: string | null;
  time_focus?: string | null;
  primary_analysis_mode?: string | null;
  what_we_understood?: string;
  user_goal_echo_excerpt?: string;
  emphasized?: string[];
  deemphasized?: string[];
};

/** ``meta_json.ai_agents.traceability`` — cross-phase summaries (no prompts). */
export type TraceabilityWire = {
  contract_version?: string;
  intent?: {
    decision_summary?: string;
    planning_transparency?: PlanningTransparencyWire;
  };
  planning?: {
    decision_summary?: string;
    selected_tools?: Array<Record<string, unknown>>;
    rationale_summary?: string;
    planning_transparency?: PlanningTransparencyWire;
  };
  execution?: {
    decision_summary?: string;
    orchestration_message?: string;
  };
  critic?: {
    phase_status?: string;
    decision_summary?: string;
    blocking_caveats?: string[];
    overall_confidence?: string | null;
    ran?: boolean;
    artifact_summary_roles_used?: string[];
    /** @deprecated Old persisted runs; prefer artifact_summary_roles_used */
    excerpt_roles_used?: string[];
    plan_alignment_findings?: PlanAlignmentFindingWire[];
    plan_alignment_codes?: string[];
  };
  report?: {
    phase_status?: string;
    rationale_summary?: string;
    key_takeaways_preview?: string[];
    ran?: boolean;
  };
  step_indices?: Record<string, number | null>;
  evidence_artifact_refs?: Array<{ role?: string; basename?: string }>;
  evidence_artifact_ids?: string[];
  evidence_artifacts_by_role?: Record<string, string>;
};

export type ParsedAiAgents = {
  intent?: AgentPhaseMeta & { interpreted_goal?: unknown };
  planning?: AgentPhaseMeta & { steps?: PlanningStepWire[] };
  critic?: AgentPhaseMeta;
  report?: AgentPhaseMeta;
  prompt_versions?: Record<string, string>;
  traceability?: TraceabilityWire;
  traceable_pipeline?: unknown;
  mcp_trace?: unknown;
};

function parsePlanningSteps(raw: unknown): PlanningStepWire[] | undefined {
  if (!Array.isArray(raw)) return undefined;
  const out: PlanningStepWire[] = [];
  for (const row of raw) {
    if (!isRecord(row)) continue;
    const order = typeof row.order === "number" ? row.order : Number(row.order);
    const tool_name = typeof row.tool_name === "string" ? row.tool_name : "";
    if (!Number.isFinite(order) || !tool_name) continue;
    const label = typeof row.label === "string" ? row.label : undefined;
    const tool_input = isRecord(row.tool_input) ? row.tool_input : undefined;
    out.push({ order, tool_name, label, tool_input });
  }
  return out.length ? out.sort((a, b) => a.order - b.order) : undefined;
}

export function parseAiAgents(meta: unknown): ParsedAiAgents | null {
  if (!isRecord(meta)) return null;
  const ai = meta.ai_agents;
  if (!isRecord(ai)) return null;

  const intent = isRecord(ai.intent) ? (ai.intent as ParsedAiAgents["intent"]) : undefined;
  const planningRaw = isRecord(ai.planning) ? ai.planning : undefined;
  let planning: ParsedAiAgents["planning"];
  if (planningRaw) {
    const steps = parsePlanningSteps(planningRaw.steps);
    planning = { ...planningRaw, steps } as ParsedAiAgents["planning"];
  }
  const critic = isRecord(ai.critic) ? (ai.critic as AgentPhaseMeta) : undefined;
  const report = isRecord(ai.report) ? (ai.report as AgentPhaseMeta) : undefined;
  const prompt_versions = isRecord(ai.prompt_versions)
    ? (ai.prompt_versions as Record<string, string>)
    : undefined;
  const traceability = isRecord(ai.traceability)
    ? (ai.traceability as TraceabilityWire)
    : undefined;

  if (
    !intent &&
    !planning &&
    !critic &&
    !report &&
    !prompt_versions &&
    !traceability
  ) {
    return {
      traceable_pipeline: ai.traceable_pipeline,
      mcp_trace: ai.mcp_trace,
    };
  }

  return {
    intent,
    planning,
    critic,
    report,
    prompt_versions,
    traceability,
    traceable_pipeline: ai.traceable_pipeline,
    mcp_trace: ai.mcp_trace,
  };
}
