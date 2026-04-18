import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonPanel } from "@/components/ui/technical";
import type { ModelCallApiItem, RunStepDetail } from "@/lib/api/types";

type Props =
  | {
      kind: "step";
      closeHref: string;
      item: RunStepDetail | null;
      errorMessage?: string | null;
    }
  | {
      kind: "model-call";
      closeHref: string;
      item: ModelCallApiItem | null;
      errorMessage?: string | null;
    };

export function TraceRawDetailSheet(props: Props) {
  return (
    <Card className="rounded-[28px] border-[rgba(31,111,255,0.28)] bg-white/92 lg:sticky lg:top-6">
      <CardHeader className="gap-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <Badge variant="secondary">Open raw payload</Badge>
            <div>
              <CardTitle className="text-[20px]">
                {props.kind === "step" ? "Inspect step details" : "Inspect model call"}
              </CardTitle>
              <CardDescription>
                This payload was fetched only for the selected item. Closing this sheet returns the page to the summary-first default.
              </CardDescription>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href={props.closeHref}>Close</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {props.errorMessage ? (
          <div className="rounded-[20px] border border-red-200 bg-red-50/80 px-4 py-4">
            <p className="text-sm font-semibold text-red-900">Trace details couldn&apos;t load.</p>
            <p className="mt-2 text-sm leading-6 text-red-800">{props.errorMessage}</p>
          </div>
        ) : null}

        {props.kind === "step" && props.item ? (
          <>
            <div className="rounded-[20px] border border-[var(--border)] bg-white/70 px-4 py-4">
              <p className="text-sm font-semibold text-[var(--foreground)]">
                {props.item.label ?? props.item.planned_tool_name ?? "Selected step"}
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">{props.item.detail ?? "No detail recorded."}</p>
            </div>
            {props.item.planner_tool_input_json != null ? (
              <JsonPanel title="planner_tool_input_json" value={props.item.planner_tool_input_json} />
            ) : null}
            {props.item.meta_json != null ? <JsonPanel title="meta_json" value={props.item.meta_json} /> : null}
          </>
        ) : null}

        {props.kind === "model-call" && props.item ? (
          <>
            <div className="rounded-[20px] border border-[var(--border)] bg-white/70 px-4 py-4">
              <p className="text-sm font-semibold text-[var(--foreground)]">{props.item.model_name}</p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {props.item.provider}
                {props.item.prompt_id ? ` · ${props.item.prompt_id}` : ""}
                {props.item.prompt_version ? ` · ${props.item.prompt_version}` : ""}
              </p>
            </div>
            {props.item.request_payload_json != null ? (
              <JsonPanel title="request_payload_json" value={props.item.request_payload_json} />
            ) : null}
            {props.item.response_payload_json != null ? (
              <JsonPanel title="response_payload_json" value={props.item.response_payload_json} />
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
