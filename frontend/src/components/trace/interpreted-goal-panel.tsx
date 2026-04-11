import type { ReactNode } from "react";

import { MetaRow } from "@/components/ui/technical";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function stringFrom(v: unknown): string | null {
  if (typeof v === "string" && v.trim()) return v;
  if (isRecord(v) && typeof v.value === "string" && v.value.trim()) return v.value;
  return null;
}

function readPlanTemplate(goal: Record<string, unknown>): Record<string, unknown> | null {
  const pt = goal.plan_template;
  return isRecord(pt) ? pt : null;
}

function readGoalPreferences(goal: Record<string, unknown>): Record<string, unknown> | null {
  const gp = goal.goal_preferences;
  return isRecord(gp) ? gp : null;
}

function formatEnumList(key: string, prefs: Record<string, unknown>): ReactNode {
  const v = prefs[key];
  if (Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === "string")) {
    return (v as string[]).join(", ");
  }
  if (typeof v === "string") return v;
  return null;
}

type Props = {
  /** orchestration interpreted_goal or ai.intent.interpreted_goal */
  orchestrationGoal: unknown;
  /** intent.phase_output when source is deterministic_rules */
  phaseIntent: Record<string, unknown> | null;
};

/**
 * Structured interpreted goal + plan template contract (no raw JSON surface).
 */
export function InterpretedGoalPanel({ orchestrationGoal, phaseIntent }: Props): ReactNode {
  const g = isRecord(orchestrationGoal) ? orchestrationGoal : null;
  const code = stringFrom(phaseIntent?.goal_code) ?? stringFrom(g?.code);
  const orchIntent = stringFrom(phaseIntent?.orchestration_intent) ?? stringFrom(g?.intent);
  const desc = stringFrom(phaseIntent?.description_excerpt) ?? stringFrom(g?.description);
  const userGoal = stringFrom(phaseIntent?.user_goal_excerpt) ?? stringFrom(g?.user_goal_text);
  const source = stringFrom(phaseIntent?.source);

  const pt = g ? readPlanTemplate(g) : null;
  const templateId = pt ? stringFrom(pt.template_id) : null;
  const mcpProfile = pt ? stringFrom(pt.mcp_execution_profile) : null;
  const peerMandatory = pt?.peer_analysis_mandatory === true;
  const persistence = pt?.persistence_filtering_required === true;

  const prefs = g ? readGoalPreferences(g) : null;

  if (!code && !desc && !userGoal && !orchIntent && !templateId && !prefs) {
    return <p className="text-sm text-[var(--muted)]">No interpreted goal fields on this run.</p>;
  }

  return (
    <div className="space-y-3">
      {source ? (
        <p className="font-mono text-[10px] text-[var(--muted)]">
          source: <span className="text-[var(--foreground)]">{source}</span>
        </p>
      ) : null}

      <div className="grid gap-0 rounded border border-[var(--border)] bg-[var(--background)]/40 sm:grid-cols-1">
        {userGoal ? (
          <div className="border-b border-[var(--border)] px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              User goal
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{userGoal}</p>
          </div>
        ) : null}
        {desc ? (
          <div className="border-b border-[var(--border)] px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Canonical label
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{desc}</p>
          </div>
        ) : null}
      </div>

      <div className="space-y-0">
        {code ? <MetaRow label="goal_code">{code}</MetaRow> : null}
        {orchIntent ? <MetaRow label="orchestration_intent">{orchIntent}</MetaRow> : null}
      </div>

      {templateId || mcpProfile ? (
        <div className="rounded border border-indigo-200/80 bg-indigo-50/40 px-3 py-2 dark:border-indigo-900 dark:bg-indigo-950/30">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-indigo-950 dark:text-indigo-200">
            Selected plan template
          </p>
          <dl className="mt-2 space-y-1 text-xs">
            {templateId ? (
              <div className="flex flex-wrap gap-x-2 gap-y-1">
                <dt className="font-mono text-[10px] text-[var(--muted)]">template_id</dt>
                <dd className="font-mono text-[var(--foreground)]">{templateId}</dd>
              </div>
            ) : null}
            {mcpProfile ? (
              <div className="flex flex-wrap gap-x-2 gap-y-1">
                <dt className="font-mono text-[10px] text-[var(--muted)]">mcp_execution_profile</dt>
                <dd className="font-mono text-[var(--foreground)]">{mcpProfile}</dd>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-[var(--foreground)]">
              <span>
                peer_analysis_mandatory:{" "}
                <strong>{peerMandatory ? "yes" : "no"}</strong>
              </span>
              <span>
                persistence_filtering_required:{" "}
                <strong>{persistence ? "yes" : "no"}</strong>
              </span>
            </div>
          </dl>
        </div>
      ) : null}

      {prefs ? (
        <div className="rounded border border-[var(--border)] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Parsed preferences (structured)
          </p>
          <div className="mt-2 space-y-1 text-xs">
            {formatEnumList("primary_analysis_mode", prefs) ? (
              <MetaRow label="primary_analysis_mode">{formatEnumList("primary_analysis_mode", prefs)}</MetaRow>
            ) : null}
            {formatEnumList("preferred_signal_style", prefs) ? (
              <MetaRow label="signal_style">{formatEnumList("preferred_signal_style", prefs)}</MetaRow>
            ) : null}
            {formatEnumList("directional_focus", prefs) ? (
              <MetaRow label="directional_focus">{formatEnumList("directional_focus", prefs)}</MetaRow>
            ) : null}
            {formatEnumList("peer_requirement", prefs) ? (
              <MetaRow label="peer_requirement">{formatEnumList("peer_requirement", prefs)}</MetaRow>
            ) : null}
            {formatEnumList("time_focus", prefs) ? (
              <MetaRow label="time_focus">{formatEnumList("time_focus", prefs)}</MetaRow>
            ) : null}
            {formatEnumList("priority_metrics", prefs) ? (
              <MetaRow label="priority_metrics">{formatEnumList("priority_metrics", prefs)}</MetaRow>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
