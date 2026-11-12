"use client";

import { useState } from "react";
import { ChartFrame, linear, niceTicks, Tooltip, useWidth, YAxis } from "./core";

export interface ScatterPoint {
  id: string;
  group: string;
  label: string;
  x: number;
  y: number;
  color: string;
  shape: "circle" | "square" | "diamond" | "triangle";
  detail?: string;
}

function Mark({ shape, cx, cy, color, size }: { shape: ScatterPoint["shape"]; cx: number; cy: number; color: string; size: number }) {
  const ring = { stroke: "var(--color-surface)", strokeWidth: 2, fill: color };
  if (shape === "square") return <rect x={cx - size} y={cy - size} width={size * 2} height={size * 2} rx={1.5} {...ring} />;
  if (shape === "diamond") return <path d={`M${cx},${cy - size - 1}l${size + 1},${size + 1}l${-size - 1},${size + 1}l${-size - 1},${-size - 1}z`} {...ring} />;
  if (shape === "triangle") return <path d={`M${cx},${cy - size - 1}l${size + 1},${size * 1.8}h${-(size + 1) * 2}z`} {...ring} />;
  return <circle cx={cx} cy={cy} r={size} {...ring} />;
}

/** Trade-off scatter (e.g. fill rate vs mean cost); shape and colour both encode the group. */
export function ScatterChart({ points, description, xLabel, yLabel, formatX, formatY, height = 320, testId }: {
  points: ScatterPoint[];
  description: string;
  xLabel: string;
  yLabel: string;
  formatX: (v: number) => string;
  formatY: (v: number) => string;
  height?: number;
  testId?: string;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<string | null>(null);
  const margin = { top: 14, right: 16, bottom: 42, left: 58 };
  const innerW = Math.max(80, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xTicks = niceTicks(Math.min(...xs), Math.max(...xs), 5);
  const yTicks = niceTicks(Math.min(...ys), Math.max(...ys), 5);
  const x = linear([xTicks[0], xTicks[xTicks.length - 1]], [margin.left, margin.left + innerW]);
  const y = linear([yTicks[0], yTicks[yTicks.length - 1]], [margin.top + innerH, margin.top]);
  const active = points.find((p) => p.id === hover);
  return (
    <ChartFrame description={description}>
      <div ref={ref} className="relative w-full" data-testid={testId}>
        <svg role="img" aria-label={description} width={width} height={height} className="block" onPointerLeave={() => setHover(null)}>
          <YAxis ticks={yTicks} y={y} x0={margin.left} x1={margin.left + innerW} format={formatY} />
          {xTicks.map((t) => (
            <g key={t} aria-hidden="true">
              <line x1={x(t)} x2={x(t)} y1={margin.top} y2={margin.top + innerH} stroke="var(--color-grid)" />
              <text x={x(t)} y={margin.top + innerH + 16} textAnchor="middle" fontSize={11} fill="var(--color-muted)">{formatX(t)}</text>
            </g>
          ))}
          <text x={margin.left + innerW / 2} y={height - 4} textAnchor="middle" fontSize={11.5} fill="var(--color-ink-2)">{xLabel}</text>
          <text transform={`translate(12,${margin.top + innerH / 2}) rotate(-90)`} textAnchor="middle" fontSize={11.5} fill="var(--color-ink-2)">{yLabel}</text>
          {points.map((p) => (
            <g key={p.id} onPointerEnter={() => setHover(p.id)} opacity={hover && hover !== p.id ? 0.4 : 1}>
              <circle cx={x(p.x)} cy={y(p.y)} r={11} fill="transparent" />
              <Mark shape={p.shape} cx={x(p.x)} cy={y(p.y)} color={p.color} size={hover === p.id ? 6 : 4.5} />
            </g>
          ))}
        </svg>
        {active && (
          <Tooltip x={x(active.x)} y={Math.max(0, y(active.y) - 10)} width={width}>
            <p className="font-semibold text-ink">{active.label}</p>
            <p className="text-ink-2">{active.group}</p>
            <p className="tabular mt-1 text-ink">{xLabel}: {formatX(active.x)}</p>
            <p className="tabular text-ink">{yLabel}: {formatY(active.y)}</p>
            {active.detail && <p className="mt-1 text-muted">{active.detail}</p>}
          </Tooltip>
        )}
      </div>
    </ChartFrame>
  );
}
