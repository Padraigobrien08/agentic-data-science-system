"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import type {
  InlineEvidenceChart,
  InlineEvidenceChartMarker,
  InlineEvidenceChartsProps,
} from "@/components/structured-answer/types";
import { cn } from "@/lib/utils";

function formatChartValue(
  value: number | null | undefined,
  valueFormat: InlineEvidenceChart["valueFormat"],
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }

  switch (valueFormat) {
    case "currency":
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2,
      }).format(value);
    case "percent":
      return new Intl.NumberFormat("en-US", {
        style: "percent",
        maximumFractionDigits: 1,
      }).format(value);
    case "count":
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value);
    case "ratio":
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2,
      }).format(value);
    case "number":
    default:
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2,
      }).format(value);
  }
}

function buildChartConfig(chart: InlineEvidenceChart): ChartConfig {
  return chart.series.reduce<ChartConfig>((config, series) => {
    config[series.key] = {
      label: series.label,
      color: `var(--${series.colorToken})`,
    };
    return config;
  }, {});
}

function referenceMarkers(markers: InlineEvidenceChartMarker[]) {
  // Subtle guide lines mark where the shifts occur; the caption says what they are,
  // so no per-line text label (repeated labels stacked and clipped the plot top).
  return markers.map((marker) => (
    <ReferenceLine
      key={`${marker.xValue}-${marker.label}`}
      x={marker.xValue}
      stroke="hsl(var(--ui-muted-foreground))"
      strokeOpacity={0.35}
      strokeDasharray="3 3"
      ifOverflow="extendDomain"
    />
  ));
}

function seriesKey(chart: InlineEvidenceChart) {
  if (chart.series.length <= 1) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-[11px] text-[var(--muted)]">
      {chart.series.map((series) => (
        <div key={series.key} className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full border border-[var(--border)]"
            style={{ backgroundColor: `var(--${series.colorToken})` }}
          />
          <span>{series.label}</span>
        </div>
      ))}
    </div>
  );
}

function chartData(chart: InlineEvidenceChart) {
  return chart.rows.map((row) => ({
    xValue: row.xValue,
    ...row.values,
  }));
}

function renderLineChart(chart: InlineEvidenceChart) {
  const data = chartData(chart);

  return (
    <ChartContainer
      config={buildChartConfig(chart)}
      className="h-[220px] w-full min-w-0 sm:h-[240px]"
      aria-label={`${chart.metricLabel}. ${chart.caption}`}
    >
      <LineChart data={data} margin={{ top: 18, right: 14, left: 0, bottom: 8 }}>
        <CartesianGrid vertical={false} stroke="hsl(var(--ui-border))" strokeOpacity={0.6} />
        <XAxis
          dataKey="xValue"
          axisLine={false}
          tickLine={false}
          minTickGap={18}
          tickMargin={10}
          interval="preserveStartEnd"
        />
        <YAxis axisLine={false} tickLine={false} tickMargin={8} width={56} />
        <ChartTooltip
          cursor={{ stroke: "hsl(var(--ui-border))", strokeDasharray: "4 4" }}
          content={
            <ChartTooltipContent
              formatter={(value) => formatChartValue(typeof value === "number" ? value : Number(value), chart.valueFormat)}
            />
          }
        />
        {chart.series.map((series) => (
          <Line
            key={series.key}
            dataKey={series.key}
            name={series.label}
            stroke={`var(--color-${series.key})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            type="linear"
          />
        ))}
        {referenceMarkers(chart.markers)}
      </LineChart>
    </ChartContainer>
  );
}

function renderGroupedBarChart(chart: InlineEvidenceChart) {
  const data = chartData(chart);

  return (
    <ChartContainer
      config={buildChartConfig(chart)}
      className="h-[220px] w-full min-w-0 sm:h-[240px]"
      aria-label={`${chart.metricLabel}. ${chart.caption}`}
    >
      <BarChart data={data} margin={{ top: 18, right: 14, left: 0, bottom: 8 }} barGap={10} barCategoryGap="18%">
        <CartesianGrid vertical={false} stroke="hsl(var(--ui-border))" strokeOpacity={0.6} />
        <XAxis
          dataKey="xValue"
          axisLine={false}
          tickLine={false}
          minTickGap={18}
          tickMargin={10}
          interval="preserveStartEnd"
        />
        <YAxis axisLine={false} tickLine={false} tickMargin={8} width={56} />
        <ChartTooltip
          cursor={{ fill: "hsl(var(--ui-muted-foreground))", fillOpacity: 0.06 }}
          content={
            <ChartTooltipContent
              formatter={(value) => formatChartValue(typeof value === "number" ? value : Number(value), chart.valueFormat)}
            />
          }
        />
        {chart.series.map((series) => (
          <Bar
            key={series.key}
            dataKey={series.key}
            name={series.label}
            fill={`var(--color-${series.key})`}
            radius={[6, 6, 2, 2]}
          />
        ))}
        {referenceMarkers(chart.markers)}
      </BarChart>
    </ChartContainer>
  );
}

function chartCard(chart: InlineEvidenceChart) {
  return (
    <article
      key={chart.chartId}
      className="space-y-4 rounded-card border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-6 sm:py-5"
    >
      {seriesKey(chart)}
      <div className="space-y-1">
        <p className="sr-only">{chart.metricLabel}</p>
        <p className="sr-only">
          X-axis: {chart.xAxisLabel}. Y-axis: {chart.yAxisLabel}.
        </p>
        {chart.kind === "grouped_bar" ? renderGroupedBarChart(chart) : renderLineChart(chart)}
      </div>
      <p className="max-w-[44rem] text-[12.5px] leading-6 text-[var(--muted)]">{chart.caption}</p>
    </article>
  );
}

export function InlineEvidenceCharts({ charts, notice, className }: InlineEvidenceChartsProps) {
  const visibleCharts = charts.filter((chart) => chart.series.length > 0 && chart.rows.length > 0).slice(0, 2);

  if (!visibleCharts.length && !notice) {
    return null;
  }

  return (
    <section className={cn("space-y-4", className)} aria-label="Visual evidence">
      <h3 className="text-base font-semibold leading-tight tracking-[-0.01em] text-[var(--foreground)]">Visual evidence</h3>
      {visibleCharts.length > 0 ? <div className="space-y-6">{visibleCharts.map((chart) => chartCard(chart))}</div> : null}
      {!visibleCharts.length && notice ? (
        <div className="rounded-card border border-dashed border-[var(--border)] bg-[var(--surface)] px-4 py-3">
          <p className="text-[13px] leading-6 text-[var(--muted)]">{notice}</p>
        </div>
      ) : null}
    </section>
  );
}
