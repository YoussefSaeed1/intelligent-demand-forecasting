"use client";

import { useState, type KeyboardEvent, type PointerEvent } from "react";
import { date as formatDate, num } from "@/lib/format";
import { ChartFrame, linear, niceTicks, Tooltip, TooltipRow, useWidth, YAxis } from "./core";

export interface TimeSeries {
  id: string;
  label: string;
  color: string;
  dash?: string;
  /** One value per entry of `dates`; null where the series has no value (never drawn as zero). */
  values: (number | null)[];
  kind?: "line" | "step" | "bars" | "markers";
  markers?: boolean;
  width?: number;
}

const MARGIN = { top: 14, right: 14, bottom: 30, left: 46 };

function path(values: (number | null)[], x: (i: number) => number, y: (v: number) => number, step: boolean): string {
  let d = "";
  let open = false;
  values.forEach((v, i) => {
    if (v === null) {
      open = false;
      return;
    }
    if (!open) {
      d += `M${x(i)},${y(v)}`;
      open = true;
    } else if (step) {
      d += `H${x(i)}V${y(v)}`;
    } else {
      d += `L${x(i)},${y(v)}`;
    }
  });
  return d;
}

/**
 * Daily time-series chart on one value axis: lines, step lines, thin columns and event markers, an optional
 * shaded window (validation period) and a labelled vertical marker (forecast origin). Pointer crosshair and
 * arrow-key navigation reveal every series value for the focused day.
 */
export function TimeChart({ dates, series, description, height = 300, band, marker, valueDigits = 1, unit = "units", testId }: {
  dates: string[];
  series: TimeSeries[];
  description: string;
  height?: number;
  band?: { from: number; to: number; label: string };
  marker?: { index: number; label: string };
  valueDigits?: number;
  unit?: string;
  testId?: string;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  const innerW = Math.max(80, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const n = dates.length;
  const all = series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  const maxValue = all.length ? Math.max(...all) : 1;
  const minValue = Math.min(0, ...(all.length ? all : [0]));
  const ticks = niceTicks(minValue, maxValue, 5);
  const y = linear([ticks[0], ticks[ticks.length - 1]], [MARGIN.top + innerH, MARGIN.top]);
  const slot = innerW / Math.max(1, n);
  const x = (i: number) => MARGIN.left + slot * (i + 0.5);
  const labelEvery = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(innerW / 78))));

  const pick = (clientX: number, element: Element) => {
    const rect = element.getBoundingClientRect();
    const i = Math.floor((clientX - rect.left - MARGIN.left) / slot);
    setActive(i >= 0 && i < n ? i : null);
  };
  const onKey = (event: KeyboardEvent) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      setActive((i) => Math.min(n - 1, Math.max(0, (i ?? (event.key === "ArrowRight" ? -1 : n)) + (event.key === "ArrowRight" ? 1 : -1))));
    } else if (event.key === "Escape") setActive(null);
  };

  const barSeries = series.filter((s) => s.kind === "bars");
  const barWidth = Math.max(1.5, Math.min(10, (slot - 2) / Math.max(1, barSeries.length)));

  return (
    <ChartFrame description={description}>
      <div ref={ref} className="relative w-full select-none" data-testid={testId}>
        <svg role="img" width={width} height={height} className="block overflow-visible" tabIndex={0} onKeyDown={onKey}
             onBlur={() => setActive(null)} aria-label={`${description}. Use left and right arrow keys to read daily values.`}
             onPointerMove={(e: PointerEvent<SVGSVGElement>) => pick(e.clientX, e.currentTarget)}
             onPointerLeave={() => setActive(null)}>
          {band && (
            <g aria-hidden="true">
              <rect x={x(band.from) - slot / 2} y={MARGIN.top} width={slot * (band.to - band.from + 1)} height={innerH}
                    fill="var(--color-brand-soft)" opacity={0.55} />
              <text x={x(band.from) - slot / 2 + 6} y={MARGIN.top + 12} fontSize={11} fill="var(--color-ink-2)">{band.label}</text>
            </g>
          )}
          <YAxis ticks={ticks} y={y} x0={MARGIN.left} x1={MARGIN.left + innerW} />
          <g aria-hidden="true">
            {dates.map((d, i) => (i % labelEvery === 0 ? (
              <text key={d} x={x(i)} y={height - 10} textAnchor="middle" fontSize={11} fill="var(--color-muted)">{formatDate(d, false)}</text>
            ) : null))}
          </g>
          {marker && (
            <g aria-hidden="true">
              <line x1={x(marker.index) + slot / 2} x2={x(marker.index) + slot / 2} y1={MARGIN.top} y2={MARGIN.top + innerH}
                    stroke="var(--color-ink)" strokeWidth={1} strokeDasharray="3 3" />
              <text x={x(marker.index) + slot / 2 - 4} y={MARGIN.top + 12} textAnchor="end" fontSize={11} fill="var(--color-ink)">{marker.label}</text>
            </g>
          )}
          {barSeries.map((s, k) => (
            <g key={s.id} aria-hidden="true">
              {s.values.map((v, i) => (v === null || v === 0 ? null : (
                <rect key={i} x={x(i) - (barWidth * barSeries.length) / 2 + k * barWidth} y={y(Math.max(0, v))}
                      width={Math.max(1, barWidth - 1)} height={Math.abs(y(0) - y(v))} rx={1.5} fill={s.color} opacity={0.85} />
              )))}
            </g>
          ))}
          {series.filter((s) => s.kind !== "bars" && s.kind !== "markers").map((s) => (
            <g key={s.id} aria-hidden="true">
              <path d={path(s.values, x, y, s.kind === "step")} fill="none" stroke={s.color} strokeWidth={s.width ?? 2}
                    strokeDasharray={s.dash} strokeLinejoin="round" strokeLinecap="round" />
              {s.markers && s.values.map((v, i) => (v === null ? null : (
                <circle key={i} cx={x(i)} cy={y(v)} r={2.6} fill={s.color} stroke="var(--color-surface)" strokeWidth={1} />
              )))}
            </g>
          ))}
          {series.filter((s) => s.kind === "markers").map((s) => (
            <g key={s.id} aria-hidden="true">
              {s.values.map((v, i) => (v === null ? null : (
                <path key={i} d={`M${x(i)},${y(v) - 6}l5,8h-10z`} fill={s.color} stroke="var(--color-surface)" strokeWidth={1.5} />
              )))}
            </g>
          ))}
          {active !== null && (
            <g aria-hidden="true">
              <line x1={x(active)} x2={x(active)} y1={MARGIN.top} y2={MARGIN.top + innerH} stroke="var(--color-ink-2)" strokeWidth={1} />
              {series.filter((s) => s.kind !== "bars" && s.values[active] !== null).map((s) => (
                <circle key={s.id} cx={x(active)} cy={y(s.values[active] as number)} r={4} fill={s.color}
                        stroke="var(--color-surface)" strokeWidth={2} />
              ))}
            </g>
          )}
        </svg>
        {active !== null && (
          <Tooltip x={x(active)} y={MARGIN.top} width={width}>
            <p className="mb-1 font-semibold text-ink">{formatDate(dates[active])}{band && active >= band.from && active <= band.to ? ` · day ${active - band.from + 1}` : ""}</p>
            {series.map((s) => (
              <TooltipRow key={s.id} color={s.color} dash={s.dash} label={s.label}
                          value={s.values[active] === null ? "—" : `${num(s.values[active], valueDigits)} ${unit}`} />
            ))}
          </Tooltip>
        )}
      </div>
    </ChartFrame>
  );
}
