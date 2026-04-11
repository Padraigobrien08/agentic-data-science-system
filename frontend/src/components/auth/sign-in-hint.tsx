import Link from "next/link";

type Props = {
  /** Path to return to after login (e.g. current page). */
  nextPath: string;
  message?: string;
};

/**
 * Shown when the API returns 401 (expired cookie, cleared storage, etc.).
 */
export function SignInHint({ nextPath, message }: Props) {
  const q = new URLSearchParams({ next: nextPath });
  return (
    <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
      <p className="font-medium">{message ?? "Sign in required"}</p>
      <p className="mt-2 font-mono text-xs text-[var(--muted)]">
        Session missing or expired — the API returned 401.
      </p>
      <Link
        href={`/login?${q.toString()}`}
        className="mt-2 inline-block font-mono text-xs underline"
      >
        Sign in →
      </Link>
    </div>
  );
}
