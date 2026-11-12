import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export type NoticeKind = "hypothetical" | "validation" | "curated" | "reported" | "caution" | "fallback";

const KIND: Record<NoticeKind, { icon: IconName; label: string; tone: string }> = {
  hypothetical: { icon: "flask", label: "Hypothetical simulation", tone: "border-caution/30 bg-caution-soft text-caution" },
  validation: { icon: "check", label: "Validation evidence", tone: "border-teal/25 bg-teal-soft text-teal" },
  curated: { icon: "database", label: "Demo coverage", tone: "border-brand/20 bg-brand-soft text-brand" },
  reported: { icon: "shield", label: "Reported final-holdout result", tone: "border-line bg-subtle text-ink-2" },
  caution: { icon: "alert", label: "Interpretation caveat", tone: "border-caution/30 bg-caution-soft text-caution" },
  fallback: { icon: "alert", label: "Precomputed fallback", tone: "border-danger/25 bg-danger-soft text-danger" },
};

/** Contextual scientific caveat: always an icon, a text label and the message (never colour alone). */
export function ScientificNotice({ kind, title, children, compact = false }: {
  kind: NoticeKind;
  title?: ReactNode;
  children: ReactNode;
  compact?: boolean;
}) {
  const spec = KIND[kind];
  return (
    <aside role="note" aria-label={spec.label} data-notice={kind}
           className={`flex gap-2.5 rounded-md border ${spec.tone} ${compact ? "px-3 py-2 text-xs" : "px-3.5 py-2.5 text-sm"}`}>
      <Icon name={spec.icon} size={compact ? 15 : 17} className="mt-0.5 shrink-0" />
      <div className="min-w-0 text-ink-2">
        <span className="font-semibold text-current">{title ?? spec.label}. </span>
        {children}
      </div>
    </aside>
  );
}
