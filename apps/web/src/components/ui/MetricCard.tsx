import type { ReactNode } from "react";

/**
 * KPI tile. `value` is pre-formatted (see lib/format). `context` names the evidence type so a number is
 * never shown without saying what it is (validation, reported final holdout or hypothetical NCU).
 */
export function MetricCard({ label, value, detail, context, accent, testId }: {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  context?: ReactNode;
  accent?: string;
  testId?: string;
}) {
  return (
    <div data-testid={testId} className="relative min-w-0 overflow-hidden rounded-lg border border-line bg-surface px-4 py-3.5">
      {accent && <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1" style={{ background: accent }} />}
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="tabular mt-1 text-2xl font-semibold leading-tight text-ink">{value}</p>
      {detail && <div className="tabular mt-1 text-sm text-ink-2">{detail}</div>}
      {context && <p className="mt-2 text-xs text-muted">{context}</p>}
    </div>
  );
}
