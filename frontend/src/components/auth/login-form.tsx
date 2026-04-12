"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { loginAction, type LoginState } from "@/actions/auth";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded border border-[var(--border)] bg-[var(--foreground)] px-3 py-2 font-mono text-sm text-[var(--background)] disabled:opacity-50"
    >
      {pending ? "Signing in…" : "Sign in"}
    </button>
  );
}

type Props = {
  nextPath: string;
};

const initial: LoginState = {};

export function LoginForm({ nextPath }: Props) {
  const [state, formAction] = useActionState(loginAction, initial);

  return (
    <form action={formAction} className="space-y-4 rounded border border-[var(--border)] p-4">
      <input type="hidden" name="next" value={nextPath} />
      {state.error ? (
        <p className="rounded border border-red-300 bg-red-50 px-2 py-1 font-mono text-xs text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
          {state.error}
        </p>
      ) : null}
      <label className="block space-y-1">
        <span className="text-xs font-medium text-[var(--muted)]">Email</span>
        <input
          name="email"
          type="email"
          autoComplete="username"
          required
          className="w-full rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-[var(--muted)]">Password</span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="w-full rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
        />
      </label>
      <SubmitButton />
    </form>
  );
}
