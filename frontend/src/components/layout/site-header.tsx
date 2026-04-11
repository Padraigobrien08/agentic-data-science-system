import Link from "next/link";

import { logoutAction } from "@/actions/auth";
import type { CurrentUser } from "@/lib/api/types";

type Props = {
  user: CurrentUser | null;
};

export function SiteHeader({ user }: Props) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--background)]">
      <div className="mx-auto flex h-12 max-w-5xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-semibold text-[var(--foreground)]">
            EDGAR Analysis
          </Link>
          <span className="hidden text-xs text-[var(--muted)] sm:inline">
            Server-side API · JWT cookie
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-xs">
          {user ? (
            <>
              <span className="max-w-[14rem] truncate text-[var(--muted)]" title={user.email}>
                {user.email}
              </span>
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="rounded border border-[var(--border)] px-2 py-1 text-[var(--foreground)] hover:bg-neutral-100 dark:hover:bg-neutral-900"
                >
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded border border-[var(--border)] px-2 py-1 text-[var(--foreground)] hover:bg-neutral-100 dark:hover:bg-neutral-900"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
