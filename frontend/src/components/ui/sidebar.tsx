"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { PanelLeftIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SidebarContextValue = {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  toggleSidebar: () => void;
  state: "expanded" | "collapsed";
};

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useControllableState({
  value,
  defaultValue,
  onChange,
}: {
  value?: boolean;
  defaultValue: boolean;
  onChange?: (value: boolean) => void;
}) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);
  const controlled = value !== undefined;
  const currentValue = controlled ? value : internalValue;

  const setValue = React.useCallback(
    (next: React.SetStateAction<boolean>) => {
      const resolved = typeof next === "function" ? next(currentValue) : next;
      if (!controlled) {
        setInternalValue(resolved);
      }
      onChange?.(resolved);
    },
    [controlled, currentValue, onChange],
  );

  return [currentValue, setValue] as const;
}

export function SidebarProvider({
  defaultOpen = true,
  open: openProp,
  onOpenChange,
  className,
  style,
  children,
}: React.PropsWithChildren<{
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
  style?: React.CSSProperties;
}>) {
  const [open, setOpen] = useControllableState({
    value: openProp,
    defaultValue: defaultOpen,
    onChange: onOpenChange,
  });
  const toggleSidebar = React.useCallback(() => setOpen((value) => !value), [setOpen]);

  return (
    <SidebarContext.Provider value={{ open, setOpen, toggleSidebar, state: open ? "expanded" : "collapsed" }}>
      <div
        style={
          {
            "--sidebar-width": "15rem",
            "--sidebar-width-mobile": "16rem",
            ...style,
          } as React.CSSProperties
        }
        className={cn("flex min-h-0 w-full", className)}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}

export const Sidebar = React.forwardRef<
  HTMLDivElement,
  React.ComponentPropsWithoutRef<"aside"> & {
    collapsible?: "none" | "icon";
  }
>(({ className, collapsible = "none", ...props }, ref) => {
  const { open } = useSidebar();

  return (
    <aside
      ref={ref}
      data-sidebar="sidebar"
      data-state={open ? "expanded" : "collapsed"}
      data-collapsible={collapsible}
      className={cn(
        "flex w-full flex-shrink-0 flex-col border-b border-[hsl(var(--sidebar-border)/0.72)] bg-[hsl(var(--sidebar-background)/0.92)] text-[hsl(var(--sidebar-foreground))] backdrop-blur md:w-[--sidebar-width] md:border-b-0 md:border-r",
        collapsible === "icon" && !open ? "md:w-[3.5rem]" : "",
        className,
      )}
      {...props}
    />
  );
});
Sidebar.displayName = "Sidebar";

export const SidebarHeader = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("border-b border-[hsl(var(--sidebar-border)/0.72)] p-3", className)}
      {...props}
    />
  ),
);
SidebarHeader.displayName = "SidebarHeader";

export const SidebarContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("scrollbar-hidden flex flex-1 flex-col overflow-y-auto", className)} {...props} />
  ),
);
SidebarContent.displayName = "SidebarContent";

export const SidebarFooter = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("border-t border-[hsl(var(--sidebar-border)/0.72)] p-3", className)}
      {...props}
    />
  ),
);
SidebarFooter.displayName = "SidebarFooter";

export const SidebarGroup = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("px-2 py-3", className)} {...props} />,
);
SidebarGroup.displayName = "SidebarGroup";

export const SidebarGroupLabel = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--sidebar-foreground)/0.55)] group-data-[state=collapsed]:hidden",
        className,
      )}
      {...props}
    />
  ),
);
SidebarGroupLabel.displayName = "SidebarGroupLabel";

export const SidebarGroupContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("space-y-2", className)} {...props} />,
);
SidebarGroupContent.displayName = "SidebarGroupContent";

export const SidebarMenu = React.forwardRef<HTMLUListElement, React.ComponentPropsWithoutRef<"ul">>(
  ({ className, ...props }, ref) => <ul ref={ref} className={cn("space-y-2", className)} {...props} />,
);
SidebarMenu.displayName = "SidebarMenu";

export const SidebarMenuItem = React.forwardRef<HTMLLIElement, React.ComponentPropsWithoutRef<"li">>(
  ({ className, ...props }, ref) => <li ref={ref} className={cn("list-none", className)} {...props} />,
);
SidebarMenuItem.displayName = "SidebarMenuItem";

export const SidebarMenuButton = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean;
    isActive?: boolean;
  }
>(({ className, asChild = false, isActive = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      ref={ref}
      data-active={isActive}
      className={cn(
        "flex w-full items-start gap-3 rounded-2xl border border-transparent px-3 py-3 text-left transition-colors",
        "hover:bg-[hsl(var(--sidebar-accent))] hover:text-[hsl(var(--sidebar-accent-foreground))]",
        "data-[active=true]:bg-[hsl(var(--sidebar-accent))] data-[active=true]:font-medium data-[active=true]:text-[hsl(var(--sidebar-accent-foreground))]",
        className,
      )}
      {...props}
    />
  );
});
SidebarMenuButton.displayName = "SidebarMenuButton";

export const SidebarInset = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("flex min-h-0 min-w-0 flex-1 flex-col", className)} {...props} />,
);
SidebarInset.displayName = "SidebarInset";

export function SidebarTrigger({
  className,
  ...props
}: Omit<React.ComponentPropsWithoutRef<typeof Button>, "size" | "variant" | "onClick">) {
  const { toggleSidebar } = useSidebar();

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={cn("rounded-full", className)}
      onClick={toggleSidebar}
      {...props}
    >
      <PanelLeftIcon className="rtl:rotate-180" />
      <span className="sr-only">Toggle sidebar</span>
    </Button>
  );
}

export function SidebarRail({ className, ...props }: React.ComponentPropsWithoutRef<"button">) {
  const { toggleSidebar } = useSidebar();

  return (
    <button
      type="button"
      aria-label="Toggle sidebar"
      onClick={toggleSidebar}
      className={cn(
        "absolute inset-y-0 -right-3 z-20 hidden w-6 rounded-full md:flex md:items-center md:justify-center",
        "after:h-14 after:w-[2px] after:rounded-full after:bg-[hsl(var(--sidebar-border))] after:transition-colors hover:after:bg-[hsl(var(--sidebar-ring))]",
        className,
      )}
      {...props}
    />
  );
}
