"use client";

import { useActionState, useRef, useState } from "react";
import { useFormStatus } from "react-dom";

import {
  createInvestigationAction,
  type CreateInvestigationState,
} from "@/actions/investigations";

const SAMPLE_CSV = `store,week,sales
north,2023-01,120
north,2023-02,138
north,2023-03,151
south,2023-01,90
south,2023-02,84
south,2023-03,77`;

/** Guard against a browser reading a multi-hundred-MB file into memory before the API says no. */
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024;

type Source = "tabular" | "edgar";

function SubmitButton({ source }: Readonly<{ source: Source }>) {
  const { pending } = useFormStatus();
  const idle = source === "edgar" ? "Investigate filings" : "Run investigation";
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md border border-neutral-300 bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white"
    >
      {pending ? "Starting investigation…" : idle}
    </button>
  );
}

const initial: CreateInvestigationState = {};

export function NewInvestigationForm({
  projectId,
  projectTickers = [],
}: Readonly<{ projectId: string; projectTickers?: string[] }>) {
  const action = createInvestigationAction.bind(null, projectId);
  const [state, formAction] = useActionState(action, initial);
  const [source, setSource] = useState<Source>("tabular");
  const [uploadError, setUploadError] = useState<string | undefined>();
  const csvRef = useRef<HTMLTextAreaElement>(null);

  const field =
    "rounded-md border border-neutral-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700";
  const label = "text-xs font-medium text-neutral-600 dark:text-neutral-300";

  // The file is read into the existing csv textarea rather than posted as multipart: it keeps
  // one request shape, and it lets the user see and edit exactly what will be sent.
  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError(
        `${file.name} is ${(file.size / 1024 / 1024).toFixed(1)} MB — the limit is 2 MB.`,
      );
      event.target.value = "";
      return;
    }
    setUploadError(undefined);
    const text = await file.text();
    if (csvRef.current) csvRef.current.value = text;
  }

  const tabSelected =
    "border-neutral-900 bg-neutral-900 text-white dark:border-neutral-100 dark:bg-neutral-100 dark:text-neutral-900";
  const tabIdle =
    "border-neutral-300 text-neutral-600 hover:border-neutral-500 dark:border-neutral-700 dark:text-neutral-300";

  return (
    <form action={formAction} className="space-y-5">
      {state.error ? (
        <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          {state.error}
        </p>
      ) : null}

      <label className="flex flex-col gap-1.5">
        <span className={label}>Goal — what should the investigation answer?</span>
        <input
          name="goal"
          required
          placeholder={
            source === "edgar"
              ? "Has margin quality deteriorated, or is revenue growth the explanation?"
              : "Are sales trending up, or is it seasonal?"
          }
          className={field}
        />
        <span className="text-xs text-neutral-400">
          A question naming an alternative explanation gets tested as two competing claims.
        </span>
      </label>

      <input type="hidden" name="source" value={source} />

      <div className="space-y-2">
        <span className={label}>Where the data comes from</span>
        <div className="flex gap-2" role="group" aria-label="Dataset source">
          <button
            type="button"
            aria-pressed={source === "tabular"}
            onClick={() => setSource("tabular")}
            className={`rounded-md border px-3 py-1.5 text-sm transition ${source === "tabular" ? tabSelected : tabIdle}`}
          >
            Your data (CSV)
          </button>
          <button
            type="button"
            aria-pressed={source === "edgar"}
            onClick={() => setSource("edgar")}
            className={`rounded-md border px-3 py-1.5 text-sm transition ${source === "edgar" ? tabSelected : tabIdle}`}
          >
            SEC EDGAR filings
          </button>
        </div>
        <p className="text-xs text-neutral-400">
          The same loop, evidence model and trace either way — EDGAR is one adapter, not a
          separate product.
        </p>
      </div>

      {source === "edgar" ? (
        <div className="space-y-4">
          <label className="flex flex-col gap-1.5">
            <span className={label}>Tickers</span>
            <input
              name="entities"
              defaultValue={projectTickers.join(", ")}
              placeholder="AAPL, MSFT, NVDA"
              className={field}
            />
            <span className="text-xs text-neutral-400">
              Up to 10. Each one is a separate SEC fetch, so the panel build scales with the
              list.
            </span>
          </label>

          <label className="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-300">
            <input type="checkbox" name="refresh" className="mt-0.5" />
            <span>
              Re-fetch from the SEC
              <span className="block text-xs text-neutral-400">
                Otherwise cached filings are reused, which is faster and kinder to the SEC.
              </span>
            </span>
          </label>

          <p className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900/40 dark:text-neutral-400">
            EDGAR investigations always run in the background: the panel is built from live SEC
            filings before the loop starts. You will land on a progress page.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <label className="flex flex-col gap-1.5">
            <span className={label}>Dataset (CSV — a header row plus data rows)</span>
            <textarea
              ref={csvRef}
              name="csv"
              required
              rows={10}
              defaultValue={SAMPLE_CSV}
              spellCheck={false}
              className={`${field} resize-y font-mono text-xs`}
            />
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer text-xs text-neutral-500 underline dark:text-neutral-400">
              Upload a .csv file
              <input type="file" accept=".csv,text/csv" onChange={handleFile} className="sr-only" />
            </label>
            <span className="text-xs text-neutral-400">
              Loads into the box above so you can check it before running. Max 2 MB.
            </span>
          </div>
          {uploadError ? (
            <p className="text-xs text-red-600 dark:text-red-400">{uploadError}</p>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <label className="flex flex-col gap-1.5">
              <span className={label}>Dataset name</span>
              <input name="name" placeholder="dataset" className={field} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className={label}>Time column (optional)</span>
              <input name="time_field" placeholder="week" className={field} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className={label}>Entity columns (optional)</span>
              <input name="entity_id_fields" placeholder="store" className={field} />
            </label>
          </div>

          <label className="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-300">
            <input type="checkbox" name="background" className="mt-0.5" />
            <span>
              Run in the background
              <span className="block text-xs text-neutral-400">
                Recommended for larger datasets. Requires a running worker; you can watch
                progress and land on the results when it finishes.
              </span>
            </span>
          </label>
        </div>
      )}

      <div className="flex items-center gap-3">
        <SubmitButton source={source} />
      </div>
    </form>
  );
}
