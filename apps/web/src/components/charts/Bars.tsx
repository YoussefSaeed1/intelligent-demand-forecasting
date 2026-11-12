"use client";

import { useState } from "react";
import { ChartFrame, linear, niceTicks, Tooltip, TooltipRow, useWidth, YAxis } from "./core";

export interface BarSeries {
  id: string;
  label: string;
  color: string;
  dash?: string;
  /** One value per category; null when undefined (no bar, shown as "—"). */
  values: (number | null)[];
}

/** Grouped columns: categories on x (e.g. validation origins), one bar per series, zero baseline. */
export function GroupedColumns({ categories, series, description, format, height = 260, testId }: {
  categories: string[];
  series: BarSeries[];
  description: string;
  format: (v: number | null) => string;
  height?: number;
  testId?: string;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<{ c: number; s: number } | null>(null);
  const margin = { top: 12, right: 10, bottom: 30, left: 46 };
  const innerW = Math.max(80, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const values = series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  const ticks = niceTicks(Math.min(0, ...values), Math.max(0, ...values), 4);
  const y = linear([ticks[0], ticks[ticks.length - 1]], [margin.top + innerH, margin.top]);
  const band = innerW / Math.max(1, categories.length);
  const barW = Math.min(24, (band * 0.72) / Math.max(1, series.length));
  const groupW = barW * series.length + 2 * (series.length - 1);
  const bx = (c: number, s: number) => margin.left + band * c + (band - groupW) / 2 + s * (barW + 2);

  return (
    <ChartFrame description={description}>
      <div ref={ref} className="relative w-full" data-testid={testId}>
        <svg role="img" aria-label={description} width={width} height={height} className="block" onPointerLeave={() => setHover(null)}>
          <YAxis ticks={ticks} y={y} x0={margin.left} x1={margin.left + innerW} />
          {categories.map((c, ci) => (
            <text key={c} x={margin.left + band * ci + band / 2} y={height - 10} textAnchor="middle" fontSize={11}
                  fill="var(--color-muted)" aria-hidden="true">{c}</text>
          ))}
          {series.map((s, si) => s.values.map((v, ci) => {
            if (v === null) return null;
            const top = y(Math.max(0, v));
            const h = Math.max(1, Math.abs(y(v) - y(0)));
            return (
              <g key={`${s.id}-${ci}`} onPointerEnter={() => setHover({ c: ci, s: si })}>
                <rect x={bx(ci, si) - 2} y={margin.top} width={barW + 4} height={innerH} fill="transparent" />
                <rect x={bx(ci, si)} y={top} width={barW} height={h} rx={3} fill={s.color}
                      opacity={hover && (hover.c !== ci || hover.s !== si) ? 0.45 : 1} />
              </g>
            );
          }))}
        </svg>
        {hover && (
          <Tooltip x={bx(hover.c, hover.s) + barW / 2} y={margin.top} width={width}>
            <p className="mb-1 font-semibold text-ink">{categories[hover.c]}</p>
            {series.map((s) => (
              <TooltipRow key={s.id} color={s.color} dash={s.dash} label={s.label} value={format(s.values[hover.c])} />
            ))}
          </Tooltip>
        )}
      </div>
    </ChartFrame>
  );
}

/** Horizontal bars around a zero line (signed differences), one row per category, up to a few series. */
export function DivergingBars({ categories, series, description, format, testId }: {
  categories: string[];
  series: BarSeries[];
  description: string;
  format: (v: number | null) => string;
  testId?: string;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const labelW = Math.min(150, Math.max(96, width * 0.28));
  const margin = { top: 8, right: 16, bottom: 26, left: labelW };
  const rowH = 10 * series.length + 12;
  const height = margin.top + margin.bottom + rowH * categories.length;
  const innerW = Math.max(60, width - margin.left - margin.right);
  const values = series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  const extent = Math.max(1e-9, ...values.map(Math.abs));
  const ticks = niceTicks(-extent, extent, 4);
  const x = linear([ticks[0], ticks[ticks.length - 1]], [margin.left, margin.left + innerW]);

  return (
    <ChartFrame description={description}>
      <div ref={ref} className="relative w-full" data-testid={testId}>
        <svg role="img" aria-label={description} width={width} height={height} className="block" onPointerLeave={() => setHover(null)}>
          {ticks.map((t) => (
            <g key={t} aria-hidden="true">
              <line x1={x(t)} x2={x(t)} y1={margin.top} y2={height - margin.bottom}
                    stroke={t === 0 ? "var(--color-ink-2)" : "var(--color-grid)"} strokeWidth={1} />
              <text x={x(t)} y={height - 8} textAnchor="middle" fontSize={11} fill="var(--color-muted)">{format(t)}</text>
            </g>
          ))}
          {categories.map((c, ci) => {
            const top = margin.top + ci * rowH;
            return (
              <g key={c} onPointerEnter={() => setHover(ci)}>
                <rect x={0} y={top} width={width} height={rowH} fill={hover === ci ? "var(--color-subtle)" : "transparent"} />
                <text x={margin.left - 8} y={top + rowH / 2} dy="0.32em" textAnchor="end" fontSize={11.5} fill="var(--color-ink-2)">{c}</text>
                {series.map((s, si) => {
                  const v = s.values[ci];
                  if (v === null) return null;
                  const x0 = x(Math.min(0, v));
                  return <rect key={s.id} x={x0} y={top + 6 + si * 10} width={Math.max(1, Math.abs(x(v) - x(0)))} height={8}
                               rx={2} fill={s.color} />;
                })}
              </g>
            );
          })}
        </svg>
        {hover !== null && (
          <Tooltip x={width * 0.9} y={margin.top + hover * rowH + rowH} width={width}>
            <p className="mb-1 font-semibold text-ink">{categories[hover]}</p>
            {series.map((s) => <TooltipRow key={s.id} color={s.color} label={s.label} value={format(s.values[hover])} />)}
          </Tooltip>
        )}
      </div>
    </ChartFrame>
  );
}

/** Stacked horizontal bars (cost components) with a 2px surface gap between segments. */
export function StackedBars({ rows, parts, description, format, testId }: {
  rows: { id: string; label: string; values: number[] }[];
  parts: { id: string; label: string; color: string }[];
  description: string;
  format: (v: number) => string;
  testId?: string;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const labelW = Math.min(170, Math.max(100, width * 0.3));
  const rowH = 30;
  const margin = { top: 6, right: 86, bottom: 6, left: labelW };
  const height = margin.top + margin.bottom + rows.length * rowH;
  const max = Math.max(1e-9, ...rows.map((r) => r.values.reduce((a, b) => a + Math.max(0, b), 0)));
  const scale = (v: number) => (v / max) * Math.max(40, width - margin.left - margin.right);
  return (
    <ChartFrame description={description}>
      <div ref={ref} className="relative w-full" data-testid={testId}>
        <svg role="img" aria-label={description} width={width} height={height} className="block" onPointerLeave={() => setHover(null)}>
          {rows.map((r, ri) => {
            let cursor = margin.left;
            const top = margin.top + ri * rowH;
            const total = r.values.reduce((a, b) => a + b, 0);
            return (
              <g key={r.id} onPointerEnter={() => setHover(ri)}>
                <rect x={0} y={top} width={width} height={rowH} fill={hover === ri ? "var(--color-subtle)" : "transparent"} />
                <text x={margin.left - 8} y={top + rowH / 2} dy="0.32em" textAnchor="end" fontSize={12} fill="var(--color-ink-2)">{r.label}</text>
                {r.values.map((v, pi) => {
                  const w = scale(Math.max(0, v));
                  const seg = w > 0 ? <rect key={pi} x={cursor} y={top + 7} width={Math.max(0, w - (w > 3 ? 2 : 0))} height={16}
                                            rx={2} fill={parts[pi].color} /> : null;
                  cursor += w;
                  return seg;
                })}
                <text x={cursor + 6} y={top + rowH / 2} dy="0.32em" fontSize={11.5} fill="var(--color-ink)" className="tabular">{format(total)}</text>
              </g>
            );
          })}
        </svg>
        {hover !== null && (
          <Tooltip x={margin.left + 20} y={margin.top + (hover + 1) * rowH} width={width}>
            <p className="mb-1 font-semibold text-ink">{rows[hover].label}</p>
            {parts.map((p, pi) => <TooltipRow key={p.id} color={p.color} label={p.label} value={format(rows[hover].values[pi])} />)}
          </Tooltip>
        )}
      </div>
    </ChartFrame>
  );
}
