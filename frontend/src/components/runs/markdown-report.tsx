"use client";

import ReactMarkdown from "react-markdown";

type Props = {
  source: string;
};

/**
 * Renders pipeline / report-agent markdown. Minimal element styling (no typography plugin).
 */
export function MarkdownReport({ source }: Props) {
  return (
    <div className="markdown-report text-sm leading-relaxed text-[var(--foreground)] [&_code]:rounded [&_code]:bg-neutral-100 [&_code]:px-1 [&_code]:text-xs dark:[&_code]:bg-neutral-900 [&_h1]:mb-2 [&_h1]:mt-4 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_li]:ml-4 [&_li]:list-disc [&_p]:my-2 [&_pre]:my-2 [&_pre]:max-h-64 [&_pre]:overflow-auto [&_pre]:rounded [&_pre]:border [&_pre]:border-[var(--border)] [&_pre]:bg-neutral-50 [&_pre]:p-2 [&_pre]:text-xs dark:[&_pre]:bg-neutral-950">
      <ReactMarkdown>{source}</ReactMarkdown>
    </div>
  );
}
