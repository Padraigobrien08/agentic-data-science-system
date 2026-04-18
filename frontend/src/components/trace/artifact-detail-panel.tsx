import Link from "next/link";

import { ArtifactContentViewer } from "@/components/trace/artifact-content-viewer";
import { JsonPanel, MetaRow, Section } from "@/components/ui/technical";
import type { ArtifactDetail } from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";

type Props = {
  row: ArtifactDetail;
  runHref: string | null;
};

/**
 * Artifact record with **provenance** and technical metadata (hash, MIME). Content bytes are not
 * listed here; use the Content section to preview or download via the API proxy.
 */
export function ArtifactDetailPanel({ row, runHref }: Props) {
  const traceHref = runHref ? `${runHref}/trace?collection=artifacts&focus=${row.id}#trace-collection` : null;

  return (
    <div className="space-y-6">
      <Section
        title="Identity"
        description="Registered artifact row (GET /v1/artifacts/{id})."
      >
        <div className="border-t border-[var(--border)]">
          <MetaRow label="id">{row.id}</MetaRow>
          <MetaRow label="role_key">{row.role_key}</MetaRow>
          <MetaRow label="kind">{row.kind}</MetaRow>
          <MetaRow label="mime_type">{row.mime_type ?? "—"}</MetaRow>
          <MetaRow label="byte_size">{formatBytes(row.byte_size)}</MetaRow>
          <MetaRow label="content_sha256">{row.content_sha256 ?? "—"}</MetaRow>
          <MetaRow label="Byte delivery">
            <span className="text-[var(--muted)]">
              Raw bytes and text preview use{" "}
              <code className="text-[var(--foreground)]">GET /v1/artifacts/{"{id}"}/content</code> and{" "}
              <code className="text-[var(--foreground)]">…/preview</code>. In this app, the browser hits{" "}
              <code className="text-[var(--foreground)]">/api/artifacts/{"{id}"}/…</code> (server proxy).
              Storage locators are not shown in the UI. See{" "}
              <code className="text-[var(--foreground)]">docs/artifact-delivery.md</code>.
            </span>
          </MetaRow>
          <MetaRow label="created_at">{formatDate(row.created_at)}</MetaRow>
          <MetaRow label="updated_at">{formatDate(row.updated_at)}</MetaRow>
        </div>
      </Section>

      <Section
        title="Lineage"
        description="Links back to analysis run and optional run_step_id when the API stores it."
      >
        <div className="border-t border-[var(--border)]">
          <MetaRow label="analysis_run_id">
            {row.analysis_run_id ? (
              runHref ? (
                <Link href={runHref} className="underline">
                  {row.analysis_run_id}
                </Link>
              ) : (
                row.analysis_run_id
              )
            ) : (
              "—"
            )}
          </MetaRow>
          <MetaRow label="run_step_id">{row.run_step_id ?? "—"}</MetaRow>
          <MetaRow label="evaluation_run_id">{row.evaluation_run_id ?? "—"}</MetaRow>
          <MetaRow label="trace_link">
            {traceHref ? (
              <Link href={traceHref} className="underline">
                Open artifact preview in run trace
              </Link>
            ) : (
              "—"
            )}
          </MetaRow>
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          <code>meta_json</code> often includes <code>orchestration_run_id</code> and{" "}
          <code>source</code> from pipeline ingest for audit.
        </p>
      </Section>

      <Section
        title="Content"
        description="Text preview (size-capped JSON response) plus inline or download of full bytes. Binary types get no preview (415); use download."
      >
        <ArtifactContentViewer artifactId={row.id} kind={row.kind} />
      </Section>

      <Section title="meta_json" description="Opaque JSON from the object store / ingest layer.">
        <JsonPanel value={row.meta_json} />
      </Section>
    </div>
  );
}
