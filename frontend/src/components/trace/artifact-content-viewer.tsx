"use client";

import { useCallback, useEffect, useState } from "react";

import { MarkdownReport } from "@/components/runs/markdown-report";
import type { ArtifactKind, ArtifactPreviewResponse } from "@/lib/api/types";

type Props = {
  artifactId: string;
  kind: ArtifactKind;
};

function parseDetailMessage(raw: string): string {
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map((x) =>
          typeof x === "object" && x && "msg" in x ? String((x as { msg: unknown }).msg) : String(x),
        )
        .join("; ");
    }
  } catch {
    /* ignore */
  }
  return raw.trim().slice(0, 400) || "Request failed";
}

function mimeLooksMarkdown(mt: string | null): boolean {
  if (!mt) return false;
  const m = mt.toLowerCase();
  return m === "text/markdown" || m === "text/x-markdown";
}

function mimeLooksCsv(mt: string | null, kind: ArtifactKind): boolean {
  if (!mt) return kind === "tabular";
  const m = mt.toLowerCase();
  return m === "text/csv" || m === "application/csv" || m.endsWith("+csv");
}

function previewModeLabel(preview: ArtifactPreviewResponse, kind: ArtifactKind): string {
  if (mimeLooksMarkdown(preview.mime_type)) return "Markdown (rendered)";
  if (preview.json_valid === false) return "Text (JSON parse failed)";
  if (preview.format === "json") return "JSON (pretty-printed)";
  if (mimeLooksCsv(preview.mime_type, kind)) return "CSV / tabular (monospace)";
  return "Plain text";
}

export function ArtifactContentViewer({ artifactId, kind }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewUnavailable, setPreviewUnavailable] = useState(false);
  const [preview, setPreview] = useState<ArtifactPreviewResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPreviewUnavailable(false);
    setPreview(null);
    try {
      const res = await fetch(`/api/artifacts/${artifactId}/preview`, {
        cache: "no-store",
      });
      const text = await res.text();
      if (res.status === 415) {
        setPreviewUnavailable(true);
        setError(parseDetailMessage(text));
        return;
      }
      if (!res.ok) {
        setError(parseDetailMessage(text));
        return;
      }
      const data = JSON.parse(text) as ArtifactPreviewResponse;
      setPreview(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load preview");
    } finally {
      setLoading(false);
    }
  }, [artifactId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openHref = `/api/artifacts/${artifactId}/content?disposition=inline`;
  const downloadHref = `/api/artifacts/${artifactId}/content?disposition=attachment`;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <a
          href={openHref}
          target="_blank"
          rel="noopener noreferrer"
          title="Same as GET …/content?disposition=inline — opens in a new tab when the browser can display the type"
          className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-1 font-mono hover:bg-[var(--chat-hover)]"
        >
          Open in browser
        </a>
        <a
          href={downloadHref}
          title="Same as GET …/content?disposition=attachment — suggests download via Content-Disposition"
          className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-1 font-mono hover:bg-[var(--chat-hover)]"
        >
          Download
        </a>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded border border-[var(--border)] px-2 py-1 font-mono text-[var(--muted)] hover:bg-[var(--chat-hover)]"
        >
          Reload preview
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-[var(--muted)]">Loading preview…</p>
      ) : null}

      {error && !preview ? (
        <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          {previewUnavailable ? (
            <>
              <p className="font-medium">No text preview for this type.</p>
              <p className="mt-1 text-[var(--muted)]">
                Use <span className="font-mono text-[var(--foreground)]">Open in browser</span> or{" "}
                <span className="font-mono text-[var(--foreground)]">Download</span> for the full object (
                <span className="font-mono">GET /v1/artifacts/…/content</span> via the app proxy).
              </p>
              {error ? (
                <p className="mt-2 font-mono text-[10px] leading-snug text-[var(--muted)]">{error}</p>
              ) : null}
            </>
          ) : (
            <>
              <p className="font-medium">Could not load preview.</p>
              <p className="mt-1 font-mono text-[11px] text-[var(--foreground)]">{error}</p>
            </>
          )}
        </div>
      ) : null}

      {preview ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
            <span className="font-medium text-[var(--foreground)]">{previewModeLabel(preview, kind)}</span>
            {preview.mime_type ? (
              <span className="font-mono text-[10px]">MIME: {preview.mime_type}</span>
            ) : (
              <span className="font-mono text-[10px]">MIME: (unset)</span>
            )}
            {preview.truncated ? (
              <span className="text-amber-800 dark:text-amber-200">Preview truncated at server cap</span>
            ) : null}
            {preview.total_bytes === 0 ? (
              <span className="text-[var(--muted)]">Declared size: 0 B</span>
            ) : null}
          </div>
          <div className="max-h-[32rem] overflow-auto rounded border border-[var(--border)] bg-[var(--surface)] p-3">
            {preview.text.length === 0 ? (
              <p className="text-xs italic text-[var(--muted)]">
                Empty preview (zero-byte object or empty decoded text).
              </p>
            ) : mimeLooksMarkdown(preview.mime_type) ? (
              <MarkdownReport source={preview.text} />
            ) : preview.format === "json" ? (
              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-[var(--foreground)]">
                {preview.text}
              </pre>
            ) : mimeLooksCsv(preview.mime_type, kind) ? (
              <pre className="overflow-x-auto whitespace-pre font-mono text-[13px] leading-relaxed text-[var(--foreground)]">
                {preview.text}
              </pre>
            ) : (
              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-[var(--foreground)]">
                {preview.text}
              </pre>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
