"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

type Props = {
  /** When true, periodically re-fetches server data so queued/running rows update. */
  active: boolean;
};

export function RunsListAutoRefresh({ active }: Props) {
  const router = useRouter();

  useEffect(() => {
    if (!active) {
      return;
    }
    const id = setInterval(() => {
      router.refresh();
    }, 5000);
    return () => clearInterval(id);
  }, [active, router]);

  return null;
}
