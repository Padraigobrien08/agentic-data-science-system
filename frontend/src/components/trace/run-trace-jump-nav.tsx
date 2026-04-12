/** Order matches section order on the run trace page (overview first, debug last). */
const BASE_LINKS: { href: string; label: string }[] = [
  { href: "#run-overview", label: "Overview" },
  { href: "#run-goal", label: "Goal" },
  { href: "#run-plan-decision", label: "Plan" },
  { href: "#run-pipeline", label: "Pipeline" },
  { href: "#run-critic", label: "Critic & report" },
  { href: "#run-conclusions", label: "Conclusions" },
  { href: "#run-evidence", label: "Evidence" },
  { href: "#run-model-calls", label: "Model calls" },
];

const LLM_USAGE_LINK = { href: "#run-llm-usage", label: "LLM usage" } as const;

/**
 * Sticky, horizontal jump links — long trace pages stay navigable without losing context.
 *
 * @param includeLlmUsageAnchor When true, insert the LLM usage anchor after Overview (requires matching ``id="run-llm-usage"`` on the page).
 */
export function RunTraceJumpNav({ includeLlmUsageAnchor = false }: { includeLlmUsageAnchor?: boolean }) {
  const links = includeLlmUsageAnchor
    ? [BASE_LINKS[0], LLM_USAGE_LINK, ...BASE_LINKS.slice(1)]
    : BASE_LINKS;

  return (
    <nav
      aria-label="Run page sections"
      className="sticky top-0 z-10 -mx-1 flex flex-wrap gap-1 border-b border-[var(--border)] bg-[var(--background)]/95 px-1 py-2 backdrop-blur-sm"
    >
      {links.map(({ href, label }) => (
        <a
          key={href}
          href={href}
          className="rounded border border-transparent px-2.5 py-1 font-mono text-[11px] text-[var(--muted)] transition-colors hover:border-[var(--border)] hover:text-[var(--foreground)]"
        >
          {label}
        </a>
      ))}
    </nav>
  );
}
