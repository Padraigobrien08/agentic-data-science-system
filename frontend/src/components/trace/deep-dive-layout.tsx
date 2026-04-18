import type { ReactNode } from "react";

import type { DeepDiveNavItem } from "@/components/trace/deep-dive-nav-config";
import { RunTraceJumpNav } from "@/components/trace/run-trace-jump-nav";

type Props = {
  includeLlmUsageAnchor: boolean;
  children: ReactNode;
  navItems?: DeepDiveNavItem[];
};

/**
 * Inspection workspace: sticky section rail on wide screens, compact horizontal jump bar on small viewports.
 */
export function DeepDiveLayout({ includeLlmUsageAnchor, children, navItems }: Props) {
  return (
    <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_12.5rem] xl:items-start xl:gap-8">
      <div className="min-w-0 space-y-4">
        <div className="xl:hidden">
          <RunTraceJumpNav
            variant="bar"
            includeLlmUsageAnchor={includeLlmUsageAnchor}
            items={navItems}
          />
        </div>
        {children}
      </div>
      <aside className="mt-2 hidden min-w-0 xl:sticky xl:top-4 xl:mt-0 xl:block">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Sections</p>
        <RunTraceJumpNav
          variant="rail"
          includeLlmUsageAnchor={includeLlmUsageAnchor}
          items={navItems}
        />
      </aside>
    </div>
  );
}
