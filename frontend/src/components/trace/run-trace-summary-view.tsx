import Link from "next/link";

import { RunTraceCollectionPanel, type RunTraceCollectionPanelProps } from "@/components/trace/run-trace-collection-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { RunTraceShell, TraceCollectionKey } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

type Props = {
  projectId: string;
  runId: string;
  shell: RunTraceShell;
  activeCollection: TraceCollectionKey;
  collectionPanel: RunTraceCollectionPanelProps;
  runAnswerHref: string;
  errorMessage?: string | null;
};

function collectionHref(projectId: string, runId: string, collection: TraceCollectionKey) {
  return `/projects/${projectId}/runs/${runId}/trace?collection=${collection}#trace-collection`;
}

export function RunTraceSummaryView({
  projectId,
  runId,
  shell,
  activeCollection,
  collectionPanel,
  runAnswerHref,
  errorMessage,
}: Props) {
  const hasAnyTrace =
    shell.steps.total > 0 || shell.artifacts.total > 0 || shell.model_calls.total > 0;

  return (
    <div className="space-y-6">
      <section id="trace-overview" className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(18rem,1fr)]">
        <Card className="overflow-hidden rounded-[32px]">
          <CardHeader className="gap-4">
            <Badge variant="secondary">Summary-first trace</Badge>
            <div className="space-y-3">
              <CardTitle className="text-[clamp(2rem,4vw,3.4rem)] leading-[1.04]">
                Audit the run without loading every raw blob first.
              </CardTitle>
              <CardDescription className="max-w-2xl text-[15px] leading-7">
                Open on the timeline, move through one collection at a time, and fetch privileged payloads only when you intentionally inspect a single item.
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="muted">{shell.run.status}</Badge>
              <Badge variant="muted">{shell.steps.total} steps</Badge>
              <Badge variant="muted">{shell.artifacts.total} artifacts</Badge>
              <Badge variant="muted">{shell.model_calls.total} model calls</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="max-w-2xl text-base leading-8 text-[var(--muted)]">
              {shell.run.orchestration_goal_text ??
                "This run has no stored orchestration goal text. Use the run answer for the conclusion, then work down the execution spine here."}
            </p>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-[20px] border border-[var(--border)] bg-white/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Status</p>
                <p className="mt-2 text-lg font-semibold text-[var(--foreground)]">{shell.run.status}</p>
              </div>
              <div className="rounded-[20px] border border-[var(--border)] bg-white/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Created</p>
                <p className="mt-2 text-lg font-semibold text-[var(--foreground)]">{formatDate(shell.run.created_at)}</p>
              </div>
              <div className="rounded-[20px] border border-[var(--border)] bg-white/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Current phase</p>
                <p className="mt-2 text-lg font-semibold text-[var(--foreground)]">{shell.run.current_phase}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href={collectionHref(projectId, runId, "steps")}>Inspect step details</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={runAnswerHref}>Run answer</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card id="trace-timeline" className="rounded-[32px]">
          <CardHeader>
            <Badge variant="muted">Timeline preview</Badge>
            <CardTitle className="text-[22px]">The step spine stays primary</CardTitle>
            <CardDescription>
              Artifacts and model calls link back to these steps instead of flattening the whole run into one mixed stream.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {shell.timeline_preview.map((step) => (
              <div key={step.id} className="rounded-[18px] border border-[var(--border)] bg-white/70 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="muted">Step {step.step_index + 1}</Badge>
                  <Badge variant={step.status === "success" ? "success" : "default"}>{step.status}</Badge>
                  {step.transparency?.trace ? <Badge variant="muted">{step.transparency.trace}</Badge> : null}
                </div>
                <p className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                  {step.label ?? step.planned_tool_name ?? "Unnamed step"}
                </p>
                {step.detail ? <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{step.detail}</p> : null}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section id="trace-collections" className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className={activeCollection === "steps" ? "border-[rgba(31,111,255,0.35)]" : ""}>
            <CardHeader className="gap-2">
              <Badge variant={activeCollection === "steps" ? "secondary" : "muted"}>Steps</Badge>
              <CardTitle className="text-[20px]">{shell.steps.total}</CardTitle>
              <CardDescription>Search labels and trace lanes, then page through persisted steps in order.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant={activeCollection === "steps" ? "default" : "outline"} size="sm">
                <Link href={collectionHref(projectId, runId, "steps")}>View all steps</Link>
              </Button>
            </CardContent>
          </Card>
          <Card className={activeCollection === "artifacts" ? "border-[rgba(31,111,255,0.35)]" : ""}>
            <CardHeader className="gap-2">
              <Badge variant={activeCollection === "artifacts" ? "secondary" : "muted"}>Artifacts</Badge>
              <CardTitle className="text-[20px]">{shell.artifacts.total}</CardTitle>
              <CardDescription>Keep evidence separate from execution state, with one preview path per artifact.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant={activeCollection === "artifacts" ? "default" : "outline"} size="sm">
                <Link href={collectionHref(projectId, runId, "artifacts")}>Open artifact preview</Link>
              </Button>
            </CardContent>
          </Card>
          <Card className={activeCollection === "model-calls" ? "border-[rgba(31,111,255,0.35)]" : ""}>
            <CardHeader className="gap-2">
              <Badge variant={activeCollection === "model-calls" ? "secondary" : "muted"}>Model calls</Badge>
              <CardTitle className="text-[20px]">{shell.model_calls.total}</CardTitle>
              <CardDescription>Audit prompt versions, provider, tokens, and latency without full request/response payloads.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant={activeCollection === "model-calls" ? "default" : "outline"} size="sm">
                <Link href={collectionHref(projectId, runId, "model-calls")}>Inspect model call</Link>
              </Button>
            </CardContent>
          </Card>
        </div>

        {errorMessage ? (
          <Card className="border-red-200 bg-red-50/80">
            <CardHeader className="gap-2">
              <Badge variant="default">Collection error</Badge>
              <CardTitle className="text-[20px]">Trace details couldn&apos;t load.</CardTitle>
              <CardDescription>
                Reload this page. If the issue persists, open the run answer or return to the runs list while the backend finishes processing.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {!hasAnyTrace && !errorMessage ? (
          <Card>
            <CardHeader className="gap-2">
              <Badge variant="muted">Empty state</Badge>
              <CardTitle className="text-[20px]">No trace details yet</CardTitle>
              <CardDescription>
                This run has not produced trace records yet. Wait for execution to finish, reopen the run answer, or retry the run if it is stuck.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        <RunTraceCollectionPanel {...collectionPanel} />
      </section>

      <section id="trace-inspector" className="space-y-4">
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Technical inspector
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              The denser audit surfaces still live below the summary-first view. Use them after you narrow the question.
            </p>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link href="#legacy-audit-stack">Jump to legacy stack</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
