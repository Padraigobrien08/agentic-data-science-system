import Link from "next/link";

import type { ArtifactMetadata } from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";

type Props = {
  artifacts: ArtifactMetadata[];
};

export function ArtifactsTable({ artifacts }: Props) {
  if (artifacts.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No artifacts registered for this run. They appear after a successful pipeline execution
        and backend ingest.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] text-[var(--muted)]">
            <th className="py-2 pr-3 font-medium">Role</th>
            <th className="py-2 pr-3 font-medium">Kind</th>
            <th className="py-2 pr-3 font-medium">Size</th>
            <th className="py-2 pr-3 font-medium">SHA-256</th>
            <th className="py-2 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {artifacts.map((a) => (
            <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
              <td className="py-2 pr-3 font-mono">
                <Link href={`/artifacts/${a.id}`} className="underline">
                  {a.role_key}
                </Link>
              </td>
              <td className="py-2 pr-3 font-mono">{a.kind}</td>
              <td className="py-2 pr-3 font-mono">{formatBytes(a.byte_size)}</td>
              <td className="max-w-[8rem] truncate py-2 pr-3 font-mono text-[10px] text-[var(--muted)]">
                {a.content_sha256 ?? "—"}
              </td>
              <td className="py-2 font-mono text-[10px] text-[var(--muted)]">
                {formatDate(a.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
