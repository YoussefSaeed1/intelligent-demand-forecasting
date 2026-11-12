"use client";

import { useEffect, useId, useState } from "react";
import { apiPath } from "@/lib/api/client";
import type { DatasetKey, ModelRole, Origin, SeriesListResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { date } from "@/lib/format";
import { DATASET_LABEL, MODEL_STYLE, PATTERNS, patternLabel, seriesLabel } from "@/lib/labels";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { ErrorState, LoadingSkeleton } from "../ui/States";

export function FieldLabel({ children, htmlFor, hint }: { children: string; htmlFor?: string; hint?: string }) {
  return (
    <div className="mb-1.5 flex items-baseline justify-between gap-2">
      <label htmlFor={htmlFor} className="text-xs font-semibold uppercase tracking-wide text-ink-2">{children}</label>
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

export function DatasetSelector({ value, onChange }: { value: DatasetKey; onChange: (value: DatasetKey) => void }) {
  return (
    <Segmented label="Dataset" value={value} onChange={onChange}
               options={[{ value: "store_item", label: DATASET_LABEL.store_item }, { value: "m5", label: DATASET_LABEL.m5 }]} />
  );
}

export function OriginSelector({ origins, value, onChange, allowAll = false }: {
  origins: Origin[];
  value: string;
  onChange: (value: string) => void;
  allowAll?: boolean;
}) {
  const options = [
    ...(allowAll ? [{ value: "all", label: "All origins" }] : []),
    ...origins.map((o) => ({ value: o.originKey, label: `Origin ${o.fold}` })),
  ];
  const current = origins.find((o) => o.originKey === value);
  return (
    <div>
      <Segmented label="Validation origin" value={value} onChange={onChange} options={options} size="sm" />
      {current && (
        <p className="mt-1 text-xs text-muted">
          Forecast made at end of {date(current.originDate)}; validation window {date(current.validationStart, false)} –{" "}
          {date(current.validationEnd)} (28 days)
        </p>
      )}
    </div>
  );
}

export function PatternSelect({ value, onChange, id }: { value: string | null; onChange: (value: string | null) => void; id?: string }) {
  return (
    <select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value || null)}
            className="h-9 w-full rounded-md border border-line bg-surface px-2.5 text-sm text-ink">
      <option value="">All demand patterns</option>
      {PATTERNS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
    </select>
  );
}

/** Model toggles; at least one model stays selected. */
export function ModelSelector({ value, onChange }: { value: ModelRole[]; onChange: (value: ModelRole[]) => void }) {
  const toggle = (role: ModelRole) => {
    const next = value.includes(role) ? value.filter((r) => r !== role) : [...value, role];
    if (next.length > 0) onChange((Object.keys(MODEL_STYLE) as ModelRole[]).filter((r) => next.includes(r)));
  };
  return (
    <fieldset>
      <legend className="sr-only">Forecast models shown</legend>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(MODEL_STYLE) as ModelRole[]).map((role) => {
          const on = value.includes(role);
          return (
            <label key={role}
                   className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm ${
                     on ? "border-ink/25 bg-surface text-ink" : "border-line bg-subtle text-muted"}`}>
              <input type="checkbox" className="h-3.5 w-3.5 accent-[var(--color-brand)]" checked={on}
                     disabled={on && value.length === 1} onChange={() => toggle(role)} />
              <svg width="18" height="8" aria-hidden="true">
                <line x1="1" y1="4" x2="17" y2="4" stroke={MODEL_STYLE[role].color} strokeWidth={2.5}
                      strokeDasharray={MODEL_STYLE[role].dash} />
              </svg>
              {MODEL_STYLE[role].short}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

const SEARCH_PATTERN = /^[A-Za-z0-9_:-]*$/;

/**
 * Searchable curated-series picker backed by `/api/v1/series` (prefix search on the series ID, 25 per page,
 * cursor pagination). Only curated demo series can ever be listed.
 */
export function SeriesSelector({ dataset, pattern, value, onChange }: {
  dataset: DatasetKey;
  pattern: string | null;
  value: string | null;
  onChange: (seriesKey: string) => void;
}) {
  const inputId = useId();
  const [text, setText] = useState("");
  const [cursors, setCursors] = useState<string[]>([]);
  const query = useDebounced(text.trim(), 250);
  const valid = query.length <= 32 && SEARCH_PATTERN.test(query);
  const cursor = cursors[cursors.length - 1];
  const path = valid ? apiPath("/series", { dataset, pattern, q: query || undefined, limit: 25, cursor }) : null;
  const { data, error, loading, reload } = useApi<SeriesListResponse>(path);

  // Reset paging whenever the result set changes.
  const resetKey = `${dataset}|${pattern}|${query}`;
  const [lastKey, setLastKey] = useState(resetKey);
  if (lastKey !== resetKey) {
    setLastKey(resetKey);
    setCursors([]);
  }

  const example = dataset === "store_item" ? "1:1 = store 1" : "4:CA_1 = store CA_1";
  return (
    <div>
      <FieldLabel htmlFor={inputId} hint={data ? `${data.total} match${data.total === 1 ? "" : "es"}` : undefined}>Series</FieldLabel>
      <div className="relative">
        <Icon name="search" size={16} className="pointer-events-none absolute left-2.5 top-2.5 text-muted" />
        <input id={inputId} type="search" value={text} maxLength={32} autoComplete="off" spellCheck={false}
               onChange={(e) => setText(e.target.value)} placeholder={`Series ID prefix (${example})`}
               aria-invalid={!valid} aria-describedby={`${inputId}-help`}
               className="h-9 w-full rounded-md border border-line bg-surface pl-8 pr-2.5 text-sm text-ink placeholder:text-muted" />
      </div>
      <p id={`${inputId}-help`} className={`mt-1 text-xs ${valid ? "text-muted" : "text-danger"}`}>
        {valid ? "Prefix match on the series ID; letters, digits, _ : - only." : "Use letters, digits, _ : or - (max 32)."}
      </p>
      <div className="mt-2 max-h-72 overflow-y-auto rounded-md border border-line">
        {loading && <div className="p-3"><LoadingSkeleton label="Loading series" rows={4} /></div>}
        {error && <div className="p-2"><ErrorState error={error} onRetry={reload} title="Series list unavailable" /></div>}
        {data && data.items.length === 0 && (
          <p className="p-3 text-sm text-muted">No curated series match these filters. Clear the search or pattern filter.</p>
        )}
        {data && data.items.length > 0 && (
          <ul aria-label="Matching series" className="divide-y divide-grid">
            {data.items.map((item) => {
              const selected = item.seriesKey === value;
              return (
                <li key={item.seriesKey}>
                  <button type="button" onClick={() => onChange(item.seriesKey)} aria-pressed={selected}
                          className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm ${
                            selected ? "bg-brand-soft text-ink" : "text-ink-2 hover:bg-subtle"}`}>
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{seriesLabel(item, dataset)}</span>
                      <span className="block truncate text-xs text-muted">ID {item.seriesId}</span>
                    </span>
                    <span className="shrink-0 text-xs text-muted">{patternLabel(item.patternKey)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {data && (cursors.length > 0 || data.nextCursor) && (
        <div className="mt-2 flex items-center justify-between text-xs">
          <button type="button" disabled={cursors.length === 0} onClick={() => setCursors((c) => c.slice(0, -1))}
                  className="rounded border border-line px-2 py-1 text-ink-2 disabled:opacity-40">Previous</button>
          <span className="text-muted">Page {cursors.length + 1}</span>
          <button type="button" disabled={!data.nextCursor}
                  onClick={() => data.nextCursor && setCursors((c) => [...c, data.nextCursor as string])}
                  className="rounded border border-line px-2 py-1 text-ink-2 disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  );
}
