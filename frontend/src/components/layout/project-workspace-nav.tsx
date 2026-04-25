import Link from "next/link";

export type WorkspaceSurface = "chat" | "trace";

type Props = {
  projectId: string;
  /** When set, links to the technical deep-dive trace. */
  runId?: string;
  current: WorkspaceSurface;
};

const navBtn =
  "rounded-md border border-transparent px-2.5 py-1.5 text-xs font-medium text-[var(--muted)] transition-colors hover:border-[var(--border)] hover:text-[var(--foreground)]";

const activeBtn =
  "rounded-md border border-[var(--border)] bg-neutral-100 px-2.5 py-1.5 text-xs font-semibold text-[var(--foreground)] dark:bg-neutral-900";

/**
 * Cross-links the primary product surfaces for a project-backed conversation.
 * Chat stays primary; trace is the secondary technical surface.
 */
export function ProjectWorkspaceNav({ projectId, runId, current }: Props) {
  const base = `/projects/${projectId}`;
  const runBase = runId ? `${base}/runs/${runId}` : null;

  return (
    <nav
      className="flex flex-wrap items-center gap-1 border-b border-[var(--border)] pb-3"
      aria-label="Conversation surfaces"
    >
      <Link href="/" className={navBtn}>
        Home
      </Link>
      <span className="text-[var(--muted)]" aria-hidden>
        ·
      </span>
      <Link href={`${base}/chat`} className={current === "chat" ? activeBtn : navBtn}>
        Chat
      </Link>
      {runBase ? (
        <>
          <span className="text-[var(--muted)]" aria-hidden>
            ·
          </span>
          <Link href={`${runBase}/trace`} className={current === "trace" ? activeBtn : navBtn}>
            Deep dive
          </Link>
        </>
      ) : null}
    </nav>
  );
}
