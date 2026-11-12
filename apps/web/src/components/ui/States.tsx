import type { ReactNode } from "react";
import type { ApiError } from "@/lib/api/client";
import { Icon } from "./Icon";

export function LoadingSkeleton({ label = "Loading", rows = 3, height = 16, chart = false }: {
  label?: string;
  rows?: number;
  height?: number;
  chart?: boolean;
}) {
  return (
    <div role="status" aria-live="polite" aria-busy="true" className="space-y-2.5">
      <span className="sr-only">{label}…</span>
      {chart && <div className="skeleton h-56 w-full sm:h-64" />}
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ height, width: `${92 - i * 13}%` }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-line px-4 py-10 text-center">
      <Icon name="search" size={22} className="text-muted" />
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
      {action}
    </div>
  );
}

/** Generic, safe error message: code-specific copy, request id for support, optional retry. No internals. */
export function ErrorState({ error, onRetry, title }: { error: ApiError; onRetry?: () => void; title?: string }) {
  const copy: Record<string, string> = {
    rate_limited: "Too many requests in a short time. Please wait a minute and retry.",
    not_found: "The requested series or origin is not in the curated demo data.",
    invalid_request: "The request was rejected by validation.",
    timeout: "The request timed out.",
    network_error: "The service could not be reached.",
    not_configured: "The service is not configured in this environment.",
  };
  return (
    <div role="alert" className="rounded-md border border-danger/25 bg-danger-soft px-4 py-3 text-sm">
      <p className="flex items-center gap-2 font-semibold text-danger">
        <Icon name="alert" size={16} /> {title ?? "This data could not be loaded"}
      </p>
      <p className="mt-1 text-ink-2">{copy[error.code] ?? error.message}</p>
      {error.fields.length > 0 && (
        <ul className="mt-1 list-disc pl-5 text-ink-2">
          {error.fields.map((f) => <li key={f.field + f.message}><code>{f.field || "request"}</code>: {f.message}</li>)}
        </ul>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-3">
        {onRetry && error.retryable && (
          <button type="button" onClick={onRetry}
                  className="inline-flex items-center gap-1.5 rounded border border-line bg-surface px-2.5 py-1 font-medium text-ink hover:bg-subtle">
            <Icon name="refresh" size={14} /> Retry
          </button>
        )}
        {error.requestId && <span className="text-xs text-muted">Request ID <code>{error.requestId}</code></span>}
      </div>
    </div>
  );
}
