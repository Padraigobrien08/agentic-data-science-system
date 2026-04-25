"use client";

import * as React from "react";
import * as RechartsPrimitive from "recharts";

import { cn } from "@/lib/utils";

const THEMES = {
  light: "",
  dark: ".dark",
} as const;

export type ChartConfig = {
  [key: string]: {
    label?: React.ReactNode;
    icon?: React.ComponentType<{ className?: string }>;
  } & (
    | {
        color?: string;
        theme?: never;
      }
    | {
        color?: never;
        theme: Record<keyof typeof THEMES, string>;
      }
  );
};

type ChartContextValue = {
  config: ChartConfig;
};

const ChartContext = React.createContext<ChartContextValue | null>(null);

function useChart() {
  const context = React.useContext(ChartContext);

  if (!context) {
    throw new Error("useChart must be used inside a <ChartContainer />.");
  }

  return context;
}

function ChartStyle({
  id,
  config,
}: {
  id: string;
  config: ChartConfig;
}) {
  const colorEntries = Object.entries(config).filter(([, item]) => item.color || item.theme);

  if (!colorEntries.length) {
    return null;
  }

  const css = Object.entries(THEMES)
    .map(([theme, prefix]) => {
      const declarations = colorEntries
        .map(([key, item]) => {
          const color = item.theme?.[theme as keyof typeof THEMES] ?? item.color;
          return color ? `  --color-${key}: ${color};` : null;
        })
        .filter(Boolean)
        .join("\n");

      if (!declarations) {
        return null;
      }

      return `${prefix} [data-chart="${id}"] {\n${declarations}\n}`;
    })
    .filter(Boolean)
    .join("\n");

  if (!css) {
    return null;
  }

  return <style dangerouslySetInnerHTML={{ __html: css }} />;
}

const ChartContainer = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & {
    config: ChartConfig;
    children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
  }
>(({ id, className, children, config, ...props }, ref) => {
  const uniqueId = React.useId();
  const chartId = `chart-${id ?? uniqueId.replace(/:/g, "")}`;
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const [containerReady, setContainerReady] = React.useState(false);

  React.useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }

    const updateReady = () => {
      const { width, height } = node.getBoundingClientRect();
      setContainerReady(width > 0 && height > 0);
    };

    updateReady();
    if (typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(updateReady);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        ref={(node) => {
          containerRef.current = node;
          if (typeof ref === "function") {
            ref(node);
          } else if (ref) {
            ref.current = node;
          }
        }}
        data-chart={chartId}
        className={cn(
          "flex w-full items-center justify-center text-xs",
          "[&_.recharts-cartesian-axis-tick_text]:fill-[hsl(var(--ui-muted-foreground))]",
          "[&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-[hsl(var(--ui-border))]/70",
          "[&_.recharts-curve.recharts-tooltip-cursor]:stroke-[hsl(var(--ui-border))]/70",
          "[&_.recharts-layer]:outline-none",
          "[&_.recharts-reference-line-line]:stroke-[hsl(var(--ui-border))]",
          "[&_.recharts-sector]:outline-none",
          "[&_.recharts-surface]:outline-none",
          className,
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        {containerReady ? (
          <RechartsPrimitive.ResponsiveContainer width="100%" height="100%">
            {children}
          </RechartsPrimitive.ResponsiveContainer>
        ) : null}
      </div>
    </ChartContext.Provider>
  );
});
ChartContainer.displayName = "ChartContainer";

type TooltipPayloadItem = {
  color?: string;
  dataKey?: string | number;
  fill?: string;
  name?: string;
  payload?: Record<string, unknown>;
  value?: number | string | null;
};

type ChartTooltipContentProps = React.ComponentProps<"div"> & {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
  hideLabel?: boolean;
  formatter?: (
    value: number | string | null | undefined,
    name: string,
    item: TooltipPayloadItem,
    index: number,
    payload: TooltipPayloadItem[],
  ) => React.ReactNode;
  labelFormatter?: (
    label: string | number | undefined,
    payload: TooltipPayloadItem[],
  ) => React.ReactNode;
};

const ChartTooltip = RechartsPrimitive.Tooltip;

const ChartTooltipContent = React.forwardRef<HTMLDivElement, ChartTooltipContentProps>(
  ({ active, className, formatter, hideLabel = false, label, labelFormatter, payload }, ref) => {
    const { config } = useChart();

    if (!active || !payload?.length) {
      return null;
    }

    const rows = payload.filter((item) => item.value !== null && item.value !== undefined);

    if (!rows.length) {
      return null;
    }

    const renderedLabel = labelFormatter ? labelFormatter(label, rows) : label;

    return (
      <div
        ref={ref}
        className={cn(
          "min-w-[11rem] rounded-[1rem] border border-[hsl(var(--ui-border))]/80",
          "bg-[hsl(var(--ui-card))]/95 px-3 py-2.5 text-[13px] text-[hsl(var(--ui-card-foreground))]",
          "shadow-[0_24px_60px_-40px_rgba(19,31,57,0.42)] backdrop-blur-sm",
          className,
        )}
      >
        {!hideLabel && renderedLabel !== undefined && renderedLabel !== null ? (
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[hsl(var(--ui-muted-foreground))]">
            {renderedLabel}
          </div>
        ) : null}
        <div className="space-y-1.5">
          {rows.map((item, index) => {
            const itemKey =
              typeof item.dataKey === "string"
                ? item.dataKey
                : typeof item.name === "string"
                  ? item.name
                  : `series-${index}`;
            const itemConfig =
              (typeof item.dataKey === "string" ? config[item.dataKey] : undefined) ?? config[itemKey];
            const labelText =
              (typeof itemConfig?.label === "string" ? itemConfig.label : item.name) ?? itemKey;
            const renderedValue = formatter
              ? formatter(item.value, labelText, item, index, rows)
              : item.value?.toString() ?? "—";
            const swatch = item.color ?? item.fill ?? `var(--color-${itemKey})`;

            return (
              <div key={`${itemKey}-${index}`} className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full border border-white/80"
                    style={{ backgroundColor: swatch }}
                  />
                  <span className="truncate text-[12px] text-[hsl(var(--ui-muted-foreground))]">{labelText}</span>
                </div>
                <span className="text-right font-medium text-[hsl(var(--ui-card-foreground))]">{renderedValue}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  },
);
ChartTooltipContent.displayName = "ChartTooltipContent";

export { ChartContainer, ChartTooltip, ChartTooltipContent };
