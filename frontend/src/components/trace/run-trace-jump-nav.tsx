import { deepDiveNavItems } from "@/components/trace/deep-dive-nav-config";

type Props = {
  /** Sticky horizontal bar (mobile / narrow) or vertical rail (aside). */
  variant?: "bar" | "rail";
  includeLlmUsageAnchor?: boolean;
};

export function RunTraceJumpNav({ variant = "bar", includeLlmUsageAnchor = false }: Props) {
  const links = deepDiveNavItems(includeLlmUsageAnchor);

  if (variant === "rail") {
    return (
      <nav aria-label="Deep dive sections" className="flex flex-col gap-0.5 border-l-2 border-[var(--border)] pl-3">
        {links.map(({ href, label }) => (
          <a
            key={href}
            href={href}
            className="block py-1 font-mono text-[10px] leading-snug text-[var(--muted)] transition-colors hover:text-[var(--foreground)]"
          >
            {label}
          </a>
        ))}
      </nav>
    );
  }

  return (
    <nav
      aria-label="Deep dive sections"
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
