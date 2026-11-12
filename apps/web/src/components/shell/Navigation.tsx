"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon } from "../ui/Icon";
import { isActive, NAV_ITEMS } from "./nav";

function NavLinks({ onNavigate, compact = false }: { onNavigate?: () => void; compact?: boolean }) {
  const pathname = usePathname();
  return (
    <ul className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <li key={item.href}>
            <Link href={item.href} onClick={onNavigate} aria-current={active ? "page" : undefined}
                  className={`group flex items-start gap-3 rounded-md px-3 py-2 transition-colors ${
                    active ? "bg-nav-2 text-white" : "text-slate-300 hover:bg-nav-2/60 hover:text-white"}`}>
              <Icon name={item.icon} size={18} className={`mt-0.5 shrink-0 ${active ? "text-[#7fd6c2]" : ""}`} />
              <span className="min-w-0">
                <span className="block text-sm font-medium">{item.label}</span>
                {!compact && <span className="block text-xs text-slate-400 group-hover:text-slate-300">{item.description}</span>}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded px-1 text-white">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#1c5cab" />
        <path d="M7 21l5-6 4 3 7-9" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="23" cy="9" r="2.4" fill="#7fd6c2" />
      </svg>
      <span className="leading-tight">
        <span className="block text-[15px] font-semibold tracking-tight">DemandIQ</span>
        <span className="block text-[11px] text-slate-400">Demand &amp; inventory analytics</span>
      </span>
    </Link>
  );
}

const EVIDENCE_NOTE = "Validation origins only · costs in hypothetical NCU · final holdout sealed";

/** Persistent sidebar on large screens. */
export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-nav-2 bg-nav px-3 py-4 lg:flex">
      <div className="px-2 pb-5"><Brand /></div>
      <nav aria-label="Primary" className="flex-1 overflow-y-auto"><NavLinks /></nav>
      <p className="mt-4 border-t border-nav-2 px-2 pt-3 text-[11px] leading-relaxed text-slate-400">{EVIDENCE_NOTE}</p>
    </aside>
  );
}

/** Top bar with a collapsible drawer below the lg breakpoint. */
export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const button = useRef<HTMLButtonElement>(null);
  const current = NAV_ITEMS.find((i) => isActive(pathname, i.href));

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="sticky top-0 z-30 border-b border-nav-2 bg-nav lg:hidden">
      <div className="flex h-14 items-center justify-between px-4">
        <Brand />
        <button ref={button} type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
                aria-controls="mobile-nav" aria-label={open ? "Close navigation" : "Open navigation"}
                className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-200 hover:bg-nav-2">
          <Icon name={open ? "close" : "menu"} size={22} />
        </button>
      </div>
      {!open && current && (
        <p className="truncate border-t border-nav-2 px-4 py-1.5 text-xs text-slate-300">{current.label}</p>
      )}
      {open && (
        <nav id="mobile-nav" aria-label="Primary" className="border-t border-nav-2 px-3 pb-4 pt-2">
          <NavLinks onNavigate={() => setOpen(false)} compact />
          <p className="mt-3 px-3 text-[11px] text-slate-400">{EVIDENCE_NOTE}</p>
        </nav>
      )}
    </div>
  );
}
