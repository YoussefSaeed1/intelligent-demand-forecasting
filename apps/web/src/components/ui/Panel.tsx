import type { ReactNode } from "react";

/** The standard surface: white card, 1px hairline border, 8px radius, optional header and footer note. */
export function Panel({ title, subtitle, actions, children, footer, className = "", id, as: Tag = "section" }: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  id?: string;
  as?: "section" | "div" | "article";
}) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <Tag id={id} aria-labelledby={title ? headingId : undefined}
         className={`min-w-0 rounded-lg border border-line bg-surface ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
          <div className="min-w-0">
            {title && <h2 id={headingId} className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="px-4 py-4 sm:px-5">{children}</div>
      {footer && <footer className="border-t border-line px-4 py-2.5 text-xs text-muted sm:px-5">{footer}</footer>}
    </Tag>
  );
}

export function Badge({ children, tone = "neutral" }: {
  children: ReactNode;
  tone?: "neutral" | "brand" | "teal" | "caution" | "danger";
}) {
  const tones = {
    neutral: "bg-subtle text-ink-2 border-line",
    brand: "bg-brand-soft text-brand border-brand/20",
    teal: "bg-teal-soft text-teal border-teal/20",
    caution: "bg-caution-soft text-caution border-caution/20",
    danger: "bg-danger-soft text-danger border-danger/20",
  };
  return (
    <span className={`inline-flex max-w-full items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

/** Colour swatch + line style sample beside a text label (identity is never colour alone). */
export function SeriesKey({ color, dash, label, marker = false }: { color: string; dash?: string; label: ReactNode; marker?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-ink-2">
      <svg width="22" height="10" aria-hidden="true">
        <line x1="1" y1="5" x2="21" y2="5" stroke={color} strokeWidth={2.5} strokeDasharray={dash} strokeLinecap="round" />
        {marker && <circle cx="11" cy="5" r="3.5" fill={color} stroke="var(--color-surface)" strokeWidth={1.5} />}
      </svg>
      {label}
    </span>
  );
}
