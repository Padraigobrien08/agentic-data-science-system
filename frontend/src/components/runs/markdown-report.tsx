"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";

type Props = {
  source: string;
  /**
   * Repeated under each # / ## / ### heading so section conclusions stay tied to artifact links.
   */
  headingEvidenceFooter?: ReactNode;
};

function EvidenceUnderHeading({ children }: { children: ReactNode }) {
  return (
    <p className="not-prose mb-3 mt-1 flex flex-wrap items-baseline gap-x-1 border-l-2 border-sky-800/25 pl-2 text-[10px] leading-snug text-[var(--muted)] dark:border-sky-300/30">
      <span className="shrink-0 font-semibold uppercase tracking-wide text-[var(--foreground)]">
        Supporting files
      </span>
      <span className="min-w-0">{children}</span>
    </p>
  );
}

/**
 * Renders pipeline / report-agent markdown. Minimal element styling (no typography plugin).
 */
export function MarkdownReport({ source, headingEvidenceFooter }: Props) {
  const withFooter = headingEvidenceFooter != null;
  const hasSectionHeadings = /^#{1,3}\s/m.test(source);

  return (
    <div className="markdown-report text-sm leading-relaxed text-[var(--foreground)] [&_code]:rounded [&_code]:bg-[var(--surface)] [&_code]:px-1 [&_code]:text-xs [&_h1]:mb-2 [&_h1]:mt-4 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mb-2 [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-semibold [&_li]:ml-4 [&_li]:list-disc [&_p]:my-2 [&_pre]:my-2 [&_pre]:max-h-64 [&_pre]:overflow-auto [&_pre]:rounded [&_pre]:border [&_pre]:border-[var(--border)] [&_pre]:bg-[var(--surface)] [&_pre]:p-2 [&_pre]:text-xs">
      {withFooter && !hasSectionHeadings ? (
        <EvidenceUnderHeading>{headingEvidenceFooter}</EvidenceUnderHeading>
      ) : null}
      <ReactMarkdown
        components={
          withFooter
            ? {
                h1: ({ children, ...props }) => (
                  <>
                    <h1 {...props}>{children}</h1>
                    <EvidenceUnderHeading>{headingEvidenceFooter}</EvidenceUnderHeading>
                  </>
                ),
                h2: ({ children, ...props }) => (
                  <>
                    <h2 {...props}>{children}</h2>
                    <EvidenceUnderHeading>{headingEvidenceFooter}</EvidenceUnderHeading>
                  </>
                ),
                h3: ({ children, ...props }) => (
                  <>
                    <h3 {...props}>{children}</h3>
                    <EvidenceUnderHeading>{headingEvidenceFooter}</EvidenceUnderHeading>
                  </>
                ),
              }
            : undefined
        }
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
