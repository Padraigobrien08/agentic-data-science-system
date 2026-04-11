import Link from "next/link";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { getCurrentUser } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<{ next?: string }>;
}>) {
  const { next } = await searchParams;
  const user = await getCurrentUser();
  if (user) {
    redirect(next?.startsWith("/") && !next.startsWith("//") ? next : "/projects");
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Sign in</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Uses <code className="text-[var(--foreground)]">POST /v1/auth/login</code> — JWT stored in an
          HttpOnly cookie for server-side API calls.
        </p>
      </div>
      <LoginForm nextPath={next?.startsWith("/") && !next.startsWith("//") ? next : "/projects"} />
      <p className="text-xs text-[var(--muted)]">
        No account?{" "}
        <Link href="/register" className="font-mono underline">
          Create one
        </Link>{" "}
        (or <code className="text-[var(--foreground)]">POST /v1/auth/register</code>).
      </p>
      <Link href="/" className="block font-mono text-xs underline">
        ← Home
      </Link>
    </div>
  );
}
