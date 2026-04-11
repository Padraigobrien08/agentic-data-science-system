import Link from "next/link";

import type { ArtifactMetadata } from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";
import { JsonPanel, Section } from "@/components/ui/technical";

type Props = {
  projectId: string;
  runId: string;
  artifacts: ArtifactMetadata[];
  /** Merged orchestration artifact_paths (role → path on disk). */
  orchestrationPaths?: Record<string, string> | null;
};

/**
 * Registered **Artifact** rows plus alignment with **orchestration** `artifact_paths` when keys
 * overlap (transparency: DB object vs pipeline-reported path).
 */
export function ArtifactsMetadataPanel({
  projectId,
  runId,
  artifacts,
  orchestrationPaths,
}: Props) {
  const pathByRole = orchestrationPaths ?? {};

  return (
    <Section
      title="Artifacts"
      description="Rows from GET /v1/runs/{id}/artifacts (ingested blobs). Orchestration may list additional paths before ingest."
    >
      {artifacts.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          No artifacts registered. After a successful run, CSV/report files appear here with role_key
          and checksums.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-2 pr-2 font-medium">role_key</th>
                <th className="py-2 pr-2 font-medium">kind</th>
                <th className="py-2 pr-2 font-medium">size</th>
                <th className="py-2 pr-2 font-medium">SHA-256</th>
                <th className="py-2 pr-2 font-medium">orchestration path</th>
                <th className="py-2 font-medium">created</th>
              </tr>
            </thead>
            <tbody>
              {artifacts.map((a) => {
                const orchPath = pathByRole[a.role_key];
                return (
                  <tr key={a.id} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-2 align-top font-mono">
                      <Link href={`/artifacts/${a.id}`} className="underline">
                        {a.role_key}
                      </Link>
                    </td>
                    <td className="py-2 pr-2 align-top font-mono">{a.kind}</td>
                    <td className="py-2 pr-2 align-top font-mono">{formatBytes(a.byte_size)}</td>
                    <td className="max-w-[10rem] py-2 pr-2 align-top font-mono text-[10px] text-[var(--muted)] break-all">
                      {a.content_sha256 ?? "—"}
                    </td>
                    <td className="max-w-xs py-2 pr-2 align-top font-mono text-[10px] text-[var(--muted)] break-all">
                      {orchPath ?? "—"}
                    </td>
                    <td className="whitespace-nowrap py-2 align-top font-mono text-[10px] text-[var(--muted)]">
                      {formatDate(a.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {orchestrationPaths && Object.keys(orchestrationPaths).length > 0 ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-[var(--muted)]">
            Full orchestration artifact_paths merge (JSON)
          </summary>
          <JsonPanel value={orchestrationPaths} />
        </details>
      ) : null}

      <p className="mt-2 text-[10px] text-[var(--muted)]">
        Run:{" "}
        <Link href={`/projects/${projectId}/runs/${runId}`} className="font-mono underline">
          {runId}
        </Link>
      </p>
    </Section>
  );
}
