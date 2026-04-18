import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-full border border-[var(--border)] bg-white/85 px-4 py-2 text-sm text-[var(--foreground)] shadow-sm outline-none placeholder:text-[var(--muted)] focus:border-[rgba(31,111,255,0.4)] focus:bg-white",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
