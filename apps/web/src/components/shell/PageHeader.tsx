import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, badges, actions }: {
  eyebrow?: string;
  title: string;
  description: ReactNode;
  badges?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-teal">{eyebrow}</p>}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink sm:text-[28px]">{title}</h1>
        <div className="mt-2 text-[15px] leading-relaxed text-ink-2">{description}</div>
        {badges && <div className="mt-3 flex flex-wrap gap-2">{badges}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
