import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  /** Rendered as the row header (<th scope="row">) for screen readers. */
  rowHeader?: boolean;
  className?: string;
}

/** Accessible, horizontally scrollable table; numbers right-aligned with tabular figures. */
export function DataTable<T>({ columns, rows, rowKey, caption, dense = false, testId, highlight }: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption: string;
  dense?: boolean;
  testId?: string;
  highlight?: (row: T) => boolean;
}) {
  const pad = dense ? "px-2.5 py-1.5" : "px-3 py-2";
  return (
    <div className="-mx-1 min-w-0 max-w-full overflow-x-auto px-1" tabIndex={0} role="region" aria-label={caption}>
      <table data-testid={testId} className="tabular w-full border-collapse text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            {columns.map((c) => (
              <th key={c.key} scope="col"
                  className={`${pad} whitespace-nowrap font-medium ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className={`border-b border-grid last:border-0 ${highlight?.(row) ? "bg-brand-soft/60" : ""}`}>
              {columns.map((c) => {
                const className = `${pad} ${c.align === "right" ? "text-right whitespace-nowrap" : "text-left"} ${c.className ?? ""}`;
                return c.rowHeader
                  ? <th key={c.key} scope="row" className={`${className} font-medium text-ink`}>{c.cell(row)}</th>
                  : <td key={c.key} className={`${className} text-ink-2`}>{c.cell(row)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
