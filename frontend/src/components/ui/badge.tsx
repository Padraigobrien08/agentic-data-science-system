import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-[0.12em] uppercase",
  {
    variants: {
      variant: {
        default: "border-[var(--border)] bg-white/70 text-[var(--foreground)]",
        secondary: "border-transparent bg-[rgba(31,111,255,0.09)] text-[var(--accent)]",
        muted: "border-transparent bg-[rgba(95,107,130,0.12)] text-[var(--muted)]",
        success: "border-transparent bg-emerald-100 text-emerald-800",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
