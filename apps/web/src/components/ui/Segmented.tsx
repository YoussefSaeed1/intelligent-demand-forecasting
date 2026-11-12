"use client";

import { useRef, type KeyboardEvent } from "react";

export interface SegmentOption<V extends string> {
  value: V;
  label: string;
  disabled?: boolean;
}

/** Single-choice toggle group (radio semantics, roving tab index, arrow-key navigation). */
export function Segmented<V extends string>({ label, options, value, onChange, size = "md" }: {
  label: string;
  options: SegmentOption<V>[];
  value: V;
  onChange: (value: V) => void;
  size?: "sm" | "md";
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.filter((o) => !o.disabled);

  function onKey(event: KeyboardEvent<HTMLButtonElement>) {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const index = enabled.findIndex((o) => o.value === value);
    const step = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
    const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? enabled.length - 1
      : (index + step + enabled.length) % enabled.length;
    const next = enabled[nextIndex];
    onChange(next.value);
    refs.current[options.indexOf(next)]?.focus();
  }

  return (
    <div role="radiogroup" aria-label={label} className="inline-flex max-w-full flex-wrap rounded-md border border-line bg-subtle p-0.5">
      {options.map((option, i) => {
        const selected = option.value === value;
        return (
          <button key={option.value} ref={(el) => { refs.current[i] = el; }} type="button" role="radio"
                  aria-checked={selected} disabled={option.disabled} tabIndex={selected ? 0 : -1}
                  onClick={() => onChange(option.value)} onKeyDown={onKey}
                  className={`rounded px-3 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    size === "sm" ? "py-1 text-xs" : "py-1.5 text-sm"} ${
                    selected ? "bg-surface text-ink shadow-sm ring-1 ring-line" : "text-ink-2 hover:text-ink"}`}>
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
