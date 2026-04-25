import Link from "next/link";

type Props = {
  projectId: string;
};

export function ProjectNav({ projectId }: Props) {
  const base = `/projects/${projectId}`;
  return (
    <nav className="flex flex-wrap gap-4 border-b border-[var(--border)] px-4 py-2 text-sm">
      <Link href={base} className="text-[var(--muted)] hover:text-[var(--foreground)]">
        Overview
      </Link>
      <Link href={`${base}/chat`} className="text-[var(--muted)] hover:text-[var(--foreground)]">
        Chat
      </Link>
    </nav>
  );
}
