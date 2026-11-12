"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { compact } from "@/lib/format";
import { exportChartPng } from "./exportPng";

/** Container width via ResizeObserver; falls back to a fixed width where layout is unavailable. */
export function useWidth<T extends HTMLElement>(fallback = 720) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => {
      const w = element.getBoundingClientRect().width;
      if (w > 0) setWidth(Math.round(w));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

/** "Nice" tick values covering [min, max] (1-2-5 steps). */
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) {
    const pad = Math.abs(min) * 0.1 || 1;
    min -= pad;
    max += pad;
  }
  const raw = (max - min) / Math.max(1, count);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? 10 * magnitude;
  const start = Math.floor(min / step) * step;
  const ticks: number[] = [];
  const end = Math.ceil(max / step) * step;
  for (let v = start; v <= end + step * 0.01; v += step) ticks.push(Number(v.toPrecision(12)));
  return ticks;
}

export function linear(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

export function ChartFrame({ title, description, legend, children, footer }: {
  title?: string;
  description: string;
  legend?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const frame = useRef<HTMLElement>(null);
  const [exportError, setExportError] = useState(false);
  return (
    <figure ref={frame} className="min-w-0">
      {title && <figcaption className="mb-1 text-sm font-semibold text-ink">{title}</figcaption>}
      {legend && <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1">{legend}</div>}
      <div data-description={description}>{children}</div>
      {footer && <div className="mt-2 text-xs text-muted">{footer}</div>}
      <button type="button" aria-label={`Export PNG: ${description}`} className="mt-2 rounded border border-line px-2 py-1 text-xs text-ink-2" onClick={() => {
        const svg = frame.current?.querySelector("svg");
        if (svg) { setExportError(false); void exportChartPng(svg, description).catch(() => setExportError(true)); }
      }}>Export PNG</button>
      {exportError && <p role="alert" className="text-sm text-danger">The chart image could not be exported. Please retry.</p>}
    </figure>
  );
}

export function YAxis({ ticks, y, x0, x1, format = compact }: {
  ticks: number[];
  y: (v: number) => number;
  x0: number;
  x1: number;
  format?: (v: number) => string;
}) {
  return (
    <g aria-hidden="true">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x0} x2={x1} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--color-line)" : "var(--color-grid)"} strokeWidth={1} />
          <text x={x0 - 6} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--color-muted)">{format(t)}</text>
        </g>
      ))}
    </g>
  );
}

/** Tooltip box positioned in container coordinates; flips to stay inside the chart. */
export function Tooltip({ x, y, width, children }: { x: number; y: number; width: number; children: ReactNode }) {
  const left = x > width * 0.6 ? undefined : x + 12;
  const right = x > width * 0.6 ? width - x + 12 : undefined;
  return (
    <div role="presentation" className="pointer-events-none absolute z-10 min-w-40 max-w-64 rounded-md border border-line bg-surface px-2.5 py-2 text-xs shadow-md"
         style={{ left, right, top: Math.max(0, y) }}>
      {children}
    </div>
  );
}

export function TooltipRow({ color, dash, label, value }: { color: string; dash?: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-0.5">
      <span className="flex items-center gap-1.5 text-ink-2">
        <svg width="14" height="6" aria-hidden="true"><line x1="1" y1="3" x2="13" y2="3" stroke={color} strokeWidth={2.5} strokeDasharray={dash} /></svg>
        {label}
      </span>
      <span className="tabular font-medium text-ink">{value}</span>
    </div>
  );
}
