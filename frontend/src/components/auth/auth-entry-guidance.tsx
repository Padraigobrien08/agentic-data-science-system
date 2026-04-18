"use client";

import Link from "next/link";

import type { AuthCapabilitiesResponse } from "@/lib/api/types";

type Props = {
  capabilities: AuthCapabilitiesResponse;
  nextPath: string;
};

function withNext(path: string, nextPath: string): string {
  if (!nextPath || nextPath === "/projects") {
    return path;
  }
  const params = new URLSearchParams({ next: nextPath });
  return `${path}?${params.toString()}`;
}

export function AuthEntryGuidance({ capabilities, nextPath }: Props) {
  const loginHref = withNext("/login", nextPath);
  const registerHref = withNext("/register", nextPath);

  if (capabilities.allow_open_registration) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--surface)] p-4 text-sm">
        <p className="font-medium text-[var(--foreground)]">Create account</p>
        <p className="mt-2 text-[var(--muted)]">
          Open registration is enabled for this environment, so you can create an account and
          start using chat immediately.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          <Link href={registerHref} className="font-mono underline">
            Create account
          </Link>
          <Link href={loginHref} className="font-mono underline">
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  if (capabilities.bootstrap_required) {
    return (
      <div className="rounded border border-amber-300 bg-amber-50/80 p-4 text-sm text-amber-950">
        <p className="font-medium">Bootstrap required</p>
        <p className="mt-2">
          This environment is locked down until an operator completes bootstrap for the first admin
          account. Ordinary self-registration is not available yet.
        </p>
        <p className="mt-2 text-xs text-amber-900/80">
          Ask an operator to use <code>POST /v1/auth/bootstrap</code> with the configured bootstrap
          token, then come back to Sign in.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          <Link href={loginHref} className="font-mono underline">
            Sign in
          </Link>
          <Link href="/" className="font-mono underline">
            Back home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] p-4 text-sm">
      <p className="font-medium text-[var(--foreground)]">Sign in</p>
      <p className="mt-2 text-[var(--muted)]">
        bootstrap is already complete for this environment and self-registration is disabled. Use
        an existing account to continue.
      </p>
      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        <Link href={loginHref} className="font-mono underline">
          Sign in
        </Link>
      </div>
    </div>
  );
}
