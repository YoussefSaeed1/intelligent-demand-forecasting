"use client";

import type { ReactNode } from "react";
import type { ApiState } from "@/lib/api/useApi";
import { ErrorState, LoadingSkeleton } from "@/components/ui/States";

/** Renders loading, error or content for one API state; keeps every data view's states consistent. */
export function DataSection<T>({ state, children, loadingLabel = "Loading", chart = false, rows = 3 }: {
  state: ApiState<T>;
  children: (data: T) => ReactNode;
  loadingLabel?: string;
  chart?: boolean;
  rows?: number;
}) {
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  if (state.loading || state.data === undefined) return <LoadingSkeleton label={loadingLabel} chart={chart} rows={rows} />;
  return <>{children(state.data)}</>;
}

/** Combines several API states; the first error wins. */
export function combine<T extends unknown[]>(states: { [K in keyof T]: ApiState<T[K]> }): ApiState<T> {
  const error = states.find((s) => s.error)?.error;
  const ready = states.every((s) => s.data !== undefined);
  return {
    data: ready && !error ? (states.map((s) => s.data) as T) : undefined,
    error,
    loading: !ready && !error,
    reload: () => states.forEach((s) => s.error && s.reload()),
  };
}
