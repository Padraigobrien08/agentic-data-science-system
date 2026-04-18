import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-[16px] bg-[rgba(95,107,130,0.12)]", className)}
      {...props}
    />
  );
}

export { Skeleton };
