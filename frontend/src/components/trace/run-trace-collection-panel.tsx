import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { TraceRawDetailSheet } from "@/components/trace/trace-raw-detail-sheet";
import type {
  ArtifactKind,
  ArtifactMetadata,
  ModelCallApiItem,
  ModelCallStatus,
  RunTraceRawDetail,
  RunStepDetail,
  RunStepStatus,
  TraceCollectionKey,
} from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";

type BaseCollectionProps = {
  projectId: string;
  runId: string;
  collection: TraceCollectionKey;
  limit: number;
  offset: number;
  hasMore: boolean;
  q?: string;
  selectedId?: string | null;
  rawDetail?: RunTraceRawDetail | null;
};

type StepPanelProps = BaseCollectionProps & {
  collection: "steps";
  items: RunStepDetail[];
  status?: RunStepStatus;
  trace?: string;
};

type ArtifactPanelProps = BaseCollectionProps & {
  collection: "artifacts";
  items: ArtifactMetadata[];
  roleKey?: string;
  kind?: ArtifactKind;
};

type ModelCallPanelProps = BaseCollectionProps & {
  collection: "model-calls";
  items: ModelCallApiItem[];
  status?: ModelCallStatus;
  promptId?: string;
};

export type RunTraceCollectionPanelProps =
  | StepPanelProps
  | ArtifactPanelProps
  | ModelCallPanelProps;

function buildTraceHref(
  projectId: string,
  runId: string,
  next: Record<string, string | number | boolean | null | undefined>,
) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(next)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const query = params.toString();
  return `/projects/${projectId}/runs/${runId}/trace${query ? `?${query}` : ""}#trace-collection`;
}

function rowClass(isSelected: boolean) {
  return [
    "rounded-[20px] border px-4 py-4 transition-colors",
    isSelected
      ? "border-[rgba(31,111,255,0.35)] bg-[rgba(31,111,255,0.05)]"
      : "border-[var(--border)] bg-white/70",
  ].join(" ");
}

export function RunTraceCollectionPanel(props: RunTraceCollectionPanelProps) {
  const baseHref = (overrides: Record<string, string | number | boolean | null | undefined>) =>
    buildTraceHref(props.projectId, props.runId, {
      collection: props.collection,
      limit: props.limit,
      offset: props.offset,
      q: props.q,
      ...("status" in props ? { status: props.status } : {}),
      ...("trace" in props ? { trace: props.trace } : {}),
      ...("roleKey" in props ? { role_key: props.roleKey } : {}),
      ...("kind" in props ? { kind: props.kind } : {}),
      ...("promptId" in props ? { prompt_id: props.promptId } : {}),
      ...overrides,
    });
  const prevOffset = Math.max(props.offset - props.limit, 0);
  const nextOffset = props.offset + props.limit;
  const hasDesktopRawDetail =
    props.rawDetail &&
    ((props.rawDetail.kind === "step" && props.collection === "steps") ||
      (props.rawDetail.kind === "model-call" && props.collection === "model-calls"));

  const renderMobileRawDetail = (selectedId: string) => {
    if (!props.rawDetail || props.rawDetail.selectedId !== selectedId) return null;
    if (
      (props.rawDetail.kind === "step" && props.collection !== "steps") ||
      (props.rawDetail.kind === "model-call" && props.collection !== "model-calls")
    ) {
      return null;
    }

    return (
      <div className="mt-4 lg:hidden">
        <TraceRawDetailSheet {...props.rawDetail} />
      </div>
    );
  };

  return (
    <Card id="trace-collection" className="rounded-[28px]">
      <CardHeader className="gap-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Badge variant="secondary">
              {props.collection === "model-calls" ? "Model calls" : props.collection}
            </Badge>
            <div>
              <CardTitle className="text-[22px]">
                {props.collection === "steps" && "Inspect step details"}
                {props.collection === "artifacts" && "Inspect artifact evidence"}
                {props.collection === "model-calls" && "Inspect model call"}
              </CardTitle>
              <CardDescription>
                {props.collection === "steps" &&
                  "The timeline stays primary, but this collection lets you search and page through persisted steps without loading raw step blobs."}
                {props.collection === "artifacts" &&
                  "Artifacts stay separate from execution steps so evidence browsing remains bounded and linked back to the run spine."}
                {props.collection === "model-calls" &&
                  "Model calls stay in their own lane with compact audit metadata instead of default request/response payload dumps."}
              </CardDescription>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant={props.collection === "steps" ? "default" : "outline"} size="sm">
              <Link href={buildTraceHref(props.projectId, props.runId, { collection: "steps", offset: 0 })}>
                Steps
              </Link>
            </Button>
            <Button
              asChild
              variant={props.collection === "artifacts" ? "default" : "outline"}
              size="sm"
            >
              <Link
                href={buildTraceHref(props.projectId, props.runId, {
                  collection: "artifacts",
                  offset: 0,
                })}
              >
                Artifacts
              </Link>
            </Button>
            <Button
              asChild
              variant={props.collection === "model-calls" ? "default" : "outline"}
              size="sm"
            >
              <Link
                href={buildTraceHref(props.projectId, props.runId, {
                  collection: "model-calls",
                  offset: 0,
                })}
              >
                Model calls
              </Link>
            </Button>
          </div>
        </div>

        <form action={buildTraceHref(props.projectId, props.runId, { collection: props.collection, offset: 0 })} className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <Input
            name="q"
            defaultValue={props.q}
            placeholder={
              props.collection === "artifacts"
                ? "Search is reserved for steps and model calls"
                : props.collection === "steps"
                  ? "Search labels, details, and trace lanes"
                  : "Search model, provider, prompt, or error detail"
            }
            disabled={props.collection === "artifacts"}
            className="lg:max-w-sm"
          />
          <input type="hidden" name="collection" value={props.collection} />
          <input type="hidden" name="limit" value={String(props.limit)} />
          {"status" in props && props.status ? <input type="hidden" name="status" value={props.status} /> : null}
          {"trace" in props && props.trace ? <input type="hidden" name="trace" value={props.trace} /> : null}
          {"roleKey" in props && props.roleKey ? (
            <input type="hidden" name="role_key" value={props.roleKey} />
          ) : null}
          {"kind" in props && props.kind ? <input type="hidden" name="kind" value={props.kind} /> : null}
          {"promptId" in props && props.promptId ? (
            <input type="hidden" name="prompt_id" value={props.promptId} />
          ) : null}
          <Button type="submit" size="sm">
            Refresh view
          </Button>
        </form>

        <div className="flex flex-wrap gap-2 text-xs">
          {props.collection === "steps" ? (
            <>
              <Badge variant={!props.trace ? "secondary" : "muted"}>All traces</Badge>
              <Link href={baseHref({ trace: "mcp_executor", offset: 0 })} className="underline underline-offset-4">
                MCP only
              </Link>
              <Link href={baseHref({ trace: "critic_agent", offset: 0 })} className="underline underline-offset-4">
                Critic
              </Link>
              <Link href={baseHref({ trace: "report_agent", offset: 0 })} className="underline underline-offset-4">
                Report
              </Link>
            </>
          ) : null}
          {props.collection === "artifacts" ? (
            <>
              <Badge variant={!props.roleKey ? "secondary" : "muted"}>All artifact roles</Badge>
              <Link href={baseHref({ role_key: "panel_csv", offset: 0 })} className="underline underline-offset-4">
                panel_csv
              </Link>
              <Link href={baseHref({ role_key: "report_md", offset: 0 })} className="underline underline-offset-4">
                report_md
              </Link>
            </>
          ) : null}
          {props.collection === "model-calls" ? (
            <>
              <Badge variant={!props.status ? "secondary" : "muted"}>All statuses</Badge>
              <Link href={baseHref({ status: "success", offset: 0 })} className="underline underline-offset-4">
                success
              </Link>
              <Link href={baseHref({ status: "error", offset: 0 })} className="underline underline-offset-4">
                error
              </Link>
            </>
          ) : null}
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="pt-6">
        <div
          className={
            hasDesktopRawDetail
              ? "space-y-4 lg:grid lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-6 lg:space-y-0"
              : "space-y-4"
          }
        >
          <div className="space-y-4">
            {props.items.length === 0 ? (
              <div className="rounded-[20px] border border-dashed border-[var(--border)] bg-white/55 px-5 py-8">
                <p className="text-base font-semibold text-[var(--foreground)]">No trace details yet</p>
                <p className="mt-2 max-w-prose text-sm leading-6 text-[var(--muted)]">
                  This run has not produced trace records yet. Wait for execution to finish, reopen the run inspection, or retry the run if it is stuck.
                </p>
              </div>
            ) : null}

            {props.collection === "steps"
              ? props.items.map((step) => {
                  const isSelected = props.selectedId === step.id;
                  return (
                    <div key={step.id} className={rowClass(isSelected)}>
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="muted">Step {step.step_index + 1}</Badge>
                            <Badge variant={step.status === "success" ? "success" : "default"}>
                              {step.status}
                            </Badge>
                            {step.transparency?.trace ? <Badge variant="muted">{step.transparency.trace}</Badge> : null}
                          </div>
                          <p className="text-base font-semibold text-[var(--foreground)]">
                            {step.label ?? step.planned_tool_name ?? "Unnamed step"}
                          </p>
                          {step.detail ? (
                            <p className="max-w-prose text-sm leading-6 text-[var(--muted)]">{step.detail}</p>
                          ) : null}
                          <p className="font-mono text-[11px] text-[var(--muted)]">
                            {formatDate(step.started_at)} → {formatDate(step.finished_at)}
                          </p>
                        </div>
                        <Button asChild variant={isSelected ? "default" : "outline"} size="sm">
                          <Link href={baseHref({ focus: step.id })}>Inspect step details</Link>
                        </Button>
                      </div>
                      {renderMobileRawDetail(step.id)}
                    </div>
                  );
                })
              : null}

            {props.collection === "artifacts"
              ? props.items.map((artifact) => {
                  const isSelected = props.selectedId === artifact.id;
                  return (
                    <div key={artifact.id} className={rowClass(isSelected)}>
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="muted">{artifact.role_key}</Badge>
                            <Badge variant="default">{artifact.kind}</Badge>
                            {artifact.run_step_id ? <Badge variant="muted">Linked step</Badge> : null}
                          </div>
                          <p className="text-base font-semibold text-[var(--foreground)]">{artifact.mime_type ?? artifact.role_key}</p>
                          <p className="font-mono text-[11px] text-[var(--muted)]">
                            {formatBytes(artifact.byte_size)} · {formatDate(artifact.created_at)}
                          </p>
                        </div>
                        <Button asChild variant="outline" size="sm">
                          <Link href={`/artifacts/${artifact.id}`}>Open artifact preview</Link>
                        </Button>
                      </div>
                    </div>
                  );
                })
              : null}

            {props.collection === "model-calls"
              ? props.items.map((call) => {
                  const isSelected = props.selectedId === call.id;
                  return (
                    <div key={call.id} className={rowClass(isSelected)}>
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={call.status === "success" ? "success" : "default"}>
                              {call.status}
                            </Badge>
                            {call.prompt_version ? <Badge variant="muted">{call.prompt_version}</Badge> : null}
                          </div>
                          <p className="text-base font-semibold text-[var(--foreground)]">{call.model_name}</p>
                          <p className="text-sm text-[var(--muted)]">
                            {call.provider}
                            {call.prompt_id ? ` · ${call.prompt_id}` : ""}
                            {call.latency_ms != null ? ` · ${call.latency_ms}ms` : ""}
                          </p>
                        </div>
                        <Button asChild variant={isSelected ? "default" : "outline"} size="sm">
                          <Link href={baseHref({ focus: call.id })}>Inspect model call</Link>
                        </Button>
                      </div>
                      {renderMobileRawDetail(call.id)}
                    </div>
                  );
                })
              : null}

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <p className="text-sm text-[var(--muted)]">
                Showing {props.offset + 1}-{props.offset + props.items.length} for {props.collection}.
              </p>
              <div className="flex gap-2">
                <Button asChild variant="outline" size="sm">
                  <Link aria-disabled={props.offset === 0} href={baseHref({ offset: prevOffset })}>
                    Previous
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link aria-disabled={!props.hasMore} href={baseHref({ offset: nextOffset })}>
                    Next
                  </Link>
                </Button>
              </div>
            </div>
          </div>

          {hasDesktopRawDetail && props.rawDetail ? (
            <div className="hidden lg:block">
              <TraceRawDetailSheet {...props.rawDetail} />
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
