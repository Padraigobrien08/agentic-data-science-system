"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Re-runs the parent server component on an interval so a pending investigation
 * page resolves itself (and redirects) once the worker finishes — no client data
 * fetching, just a periodic router refresh.
 */
export function AutoRefresh({ intervalMs = 2500 }: Readonly<{ intervalMs?: number }>) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);
  return null;
}
