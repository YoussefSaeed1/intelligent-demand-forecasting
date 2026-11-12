"use client";

import Link from "next/link";
import { useState } from "react";
import { DatasetSelector, FieldLabel, ModelSelector, OriginSelector, PatternSelect, SeriesSelector } from "@/components/selectors/Selectors";
import { TimeChart, type TimeSeries } from "@/components/charts/TimeChart";
import { DataTable } from "@/components/ui/DataTable";
import { Icon } from "@/components/ui/Icon";
import { Badge, Panel, SeriesKey } from "@/components/ui/Panel";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import { Segmented } from "@/components/ui/Segmented";
import { EmptyState } from "@/components/ui/States";
import { apiPath } from "@/lib/api/client";
import type { AggregateResponse, DatasetKey, DatasetsResponse, ForecastModelBundle, ForecastsResponse, ModelRole, SeriesDetailResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { date, int, num, pct, units4 } from "@/lib/format";
import { ACTUAL_STYLE, DATASET_LABEL, HISTORY_STYLE, MODEL_ORDER, MODEL_STYLE, patternLabel, seriesLabel } from "@/lib/labels";
import { DEFAULT_SERIES, resolveSelection } from "@/lib/selection";
import { useQueryState } from "@/lib/useQueryState";
import { DataSection } from "../common/DataSection";
import { downloadText, toCsv } from "../common/download";

const METRIC_HELP: { key: keyof ForecastModelBundle["metrics"]; label: string; help: string; format: (v: number | null) => string }[] = [
  { key: "mae", label: "MAE", help: "Mean absolute error over the 28 days (units).", format: units4 },
  { key: "rmse", label: "RMSE", help: "Root mean squared error (units); penalises large misses.", format: units4 },
  { key: "wape", label: "WAPE", help: "Sum of absolute errors divided by sum of actual demand; undefined when actual demand is zero.", format: (v) => pct(v) },
  { key: "bias", label: "Bias", help: "Mean (forecast − actual); positive means over-forecasting.", format: units4 },
  { key: "mase", label: "MASE", help: "MAE divided by the training-period weekly absolute-difference scale; undefined when that scale is zero.", format: (v) => num(v, 3) },
  { key: "rmsse", label: "RMSSE", help: "Square root of mean squared error divided by the training weekly squared-difference scale; undefined when that scale is zero.", format: (v) => num(v, 3) },
];

function ForecastChartPanel({ bundle, models }: { bundle: ForecastsResponse; models: ModelRole[] }) {
  const [historyDays, setHistoryDays] = useState<"28" | "84">("28");
  const history = bundle.history.slice(-Number(historyDays));
  const dates = [...history.map((x) => x.date), ...bundle.actuals.map((a) => a.date)];
  const h = history.length;
  const pad = (values: (number | null)[], before: number) => [...Array<null>(before).fill(null), ...values];
  const series: TimeSeries[] = [
    { id: "history", label: HISTORY_STYLE.short, color: HISTORY_STYLE.color, values: [...history.map((x) => x.units), ...Array<null>(bundle.actuals.length).fill(null)], width: 1.5 },
    { id: "actual", label: ACTUAL_STYLE.short, color: ACTUAL_STYLE.color, values: pad(bundle.actuals.map((x) => x.units), h), markers: true },
    ...MODEL_ORDER.filter((r) => models.includes(r)).map((role) => {
      const model = bundle.models.find((m) => m.role === role);
      const byDate = new Map(model?.forecast.map((f) => [f.date, f.value]));
      return { id: role, label: MODEL_STYLE[role].short, color: MODEL_STYLE[role].color, dash: MODEL_STYLE[role].dash,
               values: dates.map((d, i) => (i < h ? null : byDate.get(d) ?? null)) };
    }),
  ];
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-x-4 gap-y-1">
        <SeriesKey color={HISTORY_STYLE.color} label={`Pre-origin history (${h} days)`} />
        <SeriesKey color={ACTUAL_STYLE.color} label="Actual demand (validation window)" marker />
        {MODEL_ORDER.filter((r) => models.includes(r)).map((r) => (
          <SeriesKey key={r} color={MODEL_STYLE[r].color} dash={MODEL_STYLE[r].dash} label={`${MODEL_STYLE[r].short} forecast`} />
        ))}
        </div>
        <Segmented label="History shown" size="sm" value={historyDays} onChange={setHistoryDays}
                   options={[{ value: "28", label: "28-day history" }, { value: "84", label: "84-day history" }]} />
      </div>
      <TimeChart testId="forecast-chart" dates={dates} series={series} height={320}
                 description={`Daily demand and saved 28-day forecasts for ${bundle.series.seriesId}, ${bundle.origin.foldLabel}`}
                 band={{ from: h, to: dates.length - 1, label: "Validation window (28 days)" }}
                 marker={{ index: h - 1, label: `Origin ${date(bundle.origin.originDate, false)}` }} />
      <p className="mt-2 text-xs text-muted">Forecasts are fixed at the origin for all 28 days (not refreshed daily). Hover or focus the chart and use the arrow keys to read daily values.</p>
    </>
  );
}

function MetricsTable({ bundle, models }: { bundle: ForecastsResponse; models: ModelRole[] }) {
  const rows = MODEL_ORDER.filter((r) => models.includes(r)).map((r) => bundle.models.find((m) => m.role === r))
    .filter((m): m is ForecastModelBundle => Boolean(m));
  return (
    <DataTable caption="Per-model forecast accuracy for this series and origin" rows={rows} rowKey={(r) => r.role} testId="metrics-table"
               columns={[
                 { key: "model", header: "Model", rowHeader: true,
                   cell: (r) => <SeriesKey color={MODEL_STYLE[r.role].color} dash={MODEL_STYLE[r.role].dash} label={MODEL_STYLE[r.role].short} /> },
                 ...METRIC_HELP.map((m) => ({ key: m.key, align: "right" as const,
                   header: <abbr title={m.help} className="cursor-help no-underline">{m.label}</abbr>,
                   cell: (r: ForecastModelBundle) => m.format(r.metrics[m.key]) })),
               ]} />
  );
}

function PopulationContext({ dataset, origin, pattern, models }: { dataset: DatasetKey; origin: string; pattern: string; models: ModelRole[] }) {
  const state = useApi<AggregateResponse>(apiPath("/metrics/aggregate", { dataset, origin, pattern }));
  return (
    <DataSection state={state} loadingLabel="Loading population context">
      {(data) => {
        const rows = MODEL_ORDER.filter((r) => models.includes(r)).map((r) => data.rows.find((x) => x.role === r)).filter(Boolean) as AggregateResponse["rows"];
        if (rows.length === 0) return <p className="text-sm text-muted">No population rows for this pattern and origin.</p>;
        return (
          <>
            <p className="mb-2 text-sm text-ink-2">
              All <strong>{int(rows[0].metrics.series)}</strong> {patternLabel(pattern).toLowerCase()} series in the full {DATASET_LABEL[dataset]} research
              population at this origin (not only the curated demo series):
            </p>
            <DataTable caption="Full-population accuracy for this demand pattern and origin" rows={rows} rowKey={(r) => r.role} dense testId="population-table"
                       columns={[
                         { key: "model", header: "Model", rowHeader: true, cell: (r) => MODEL_STYLE[r.role].short },
                         { key: "mae", header: "Pooled MAE", align: "right", cell: (r) => units4(r.metrics.mae) },
                         { key: "wape", header: "WAPE", align: "right", cell: (r) => pct(r.metrics.wape) },
                         { key: "mase", header: "Macro MASE", align: "right", cell: (r) => num(r.metrics.macroMase, 3) },
                         { key: "undef", header: "MASE undefined", align: "right", cell: (r) => int(r.metrics.undefinedMaseSeries) },
                       ]} />
          </>
        );
      }}
    </DataSection>
  );
}

function DailyTable({ bundle, models }: { bundle: ForecastsResponse; models: ModelRole[] }) {
  const shown = MODEL_ORDER.filter((r) => models.includes(r));
  const rows = bundle.actuals.map((a, i) => ({ ...a, day: i + 1,
    forecasts: Object.fromEntries(shown.map((r) => [r, bundle.models.find((m) => m.role === r)?.forecast.find((f) => f.date === a.date)?.value ?? null])) }));
  return (
    <DataTable caption="Daily actual demand and saved forecasts over the 28-day validation window" rows={rows} rowKey={(r) => r.date} dense
               columns={[
                 { key: "day", header: "Day", align: "right", cell: (r) => r.day },
                 { key: "date", header: "Date", cell: (r) => date(r.date) },
                 { key: "actual", header: "Actual", align: "right", cell: (r) => int(r.units) },
                 ...shown.map((role) => ({ key: role, header: MODEL_STYLE[role].short, align: "right" as const,
                                           cell: (r: (typeof rows)[number]) => num(r.forecasts[role], 2) })),
               ]} />
  );
}

export function ForecastExplorer() {
  const { params, update } = useQueryState();
  const selection = resolveSelection(params);
  const { dataset, series, origin, pattern, models } = selection;
  const datasets = useApi<DatasetsResponse>(apiPath("/datasets"));
  const detail = useApi<SeriesDetailResponse>(series ? apiPath(`/series/${encodeURIComponent(series)}`) : null);
  const forecasts = useApi<ForecastsResponse>(series ? apiPath("/forecasts", { series, origin }) : null);
  const info = datasets.data?.datasets.find((d) => d.datasetKey === dataset);

  const exportCsv = (bundle: ForecastsResponse) => {
    const shown = MODEL_ORDER.filter((r) => models.includes(r));
    const header = ["series_id", "origin", "date", "window", "units", ...shown.map((r) => `${r}_forecast`)];
    const lines = [
      ...bundle.history.map((h) => [bundle.series.seriesId, bundle.origin.foldLabel, h.date, "history", h.units, ...shown.map(() => "")]),
      ...bundle.actuals.map((a) => [bundle.series.seriesId, bundle.origin.foldLabel, a.date, "validation", a.units,
        ...shown.map((r) => bundle.models.find((m) => m.role === r)?.forecast.find((f) => f.date === a.date)?.value ?? "")]),
    ];
    downloadText(toCsv(header, lines, `Saved validation forecasts (export ${bundle.meta.exportVersion}); not the final holdout.`),
                 `forecasts_${bundle.series.seriesId}_origin${bundle.origin.fold}.csv`.replace(/[^A-Za-z0-9_.-]/g, "_"));
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside aria-label="Forecast filters" className="space-y-5 lg:sticky lg:top-6 lg:self-start">
        <Panel>
          <div className="space-y-5">
            <div>
              <FieldLabel>Dataset</FieldLabel>
              <DatasetSelector value={dataset} onChange={(d) => update({ dataset: d, series: DEFAULT_SERIES[d], origin: `${d}|4`, pattern: null })} />
              <p className="mt-1.5 text-xs text-muted">{info?.coverageNote}</p>
            </div>
            <div>
              <FieldLabel htmlFor="pattern-filter">Demand pattern</FieldLabel>
              <PatternSelect id="pattern-filter" value={pattern} onChange={(p) => update({ pattern: p })} />
            </div>
            <SeriesSelector dataset={dataset} pattern={pattern} value={series} onChange={(s) => update({ series: s, dataset })} />
          </div>
        </Panel>
      </aside>

      <div className="min-w-0 space-y-5">
        {selection.corrected && (
          <ScientificNotice kind="caution" title="Link adjusted">
            Some link parameters were invalid or belonged to another dataset, so defaults were used instead.
          </ScientificNotice>
        )}
        {dataset === "m5" && (
          <ScientificNotice kind="curated" title="Exploratory demo subset">
            M5 series here are a predeclared, pattern-stratified sample of 300 of the 30,490 research series (seed 42, drawn before any
            result was consulted). Use them to explore; population claims come only from the full-population tables.
          </ScientificNotice>
        )}

        <Panel>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="space-y-3">
              <div>
                <FieldLabel>Validation origin</FieldLabel>
                {info ? <OriginSelector origins={info.origins} value={origin} onChange={(o) => update({ origin: o })} />
                  : <div className="skeleton h-8 w-72" />}
              </div>
              <div>
                <FieldLabel>Models</FieldLabel>
                <ModelSelector value={models} onChange={(m) => update({ models: m.length === 3 ? null : m.join(",") })} />
              </div>
            </div>
            {series && (
              <div className="flex flex-wrap gap-2">
                <Link href={`/planner?series=${encodeURIComponent(series)}&origin=${encodeURIComponent(origin)}`}
                      className="inline-flex items-center gap-1.5 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-[#174c8e]">
                  <Icon name="planner" size={16} /> Open in Inventory Planner
                </Link>
                <button type="button" disabled={!forecasts.data} onClick={() => forecasts.data && exportCsv(forecasts.data)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-subtle disabled:opacity-50">
                  <Icon name="download" size={16} /> CSV
                </button>
              </div>
            )}
          </div>
        </Panel>

        {!series ? (
          <EmptyState title="Select a series">Choose a curated series from the list to see its history, actual demand and saved forecasts.</EmptyState>
        ) : (
          <>
            <Panel title={detail.data ? seriesLabel(detail.data.series, dataset) : "Series"}
                   subtitle={detail.data ? <>ID <code>{detail.data.series.seriesId}</code>
                     {detail.data.series.departmentId && <> · {detail.data.series.departmentId} · {detail.data.series.stateId}</>}</> : undefined}
                   actions={detail.data && <Badge tone="brand">{detail.data.series.demandPattern}</Badge>}
                   footer={detail.data && <>{detail.data.series.patternDescription}. Training-prefix mean {num(detail.data.series.trainingPrefixMeanUnits, 2)} units/day
                     {detail.data.series.retrospectiveSparseGroup === "Yes" && " · in the retrospective sparse (all-zero final-label) stratum"}.</>}>
              <DataSection state={forecasts} chart rows={0} loadingLabel="Loading forecasts">
                {(bundle) => <ForecastChartPanel bundle={bundle} models={models} />}
              </DataSection>
            </Panel>

            <div className="grid gap-5">
              <Panel title="Accuracy for this series" subtitle="28-day validation window; hover a metric name for its definition"
                     footer="— means undefined (for example WAPE with zero actual demand); undefined values are never shown as zero.">
                <DataSection state={forecasts} loadingLabel="Loading metrics">
                  {(bundle) => <MetricsTable bundle={bundle} models={models} />}
                </DataSection>
              </Panel>
              <Panel title="Population context" subtitle="Same demand pattern and origin, full research population">
                {detail.data ? <PopulationContext dataset={dataset} origin={origin} pattern={detail.data.series.patternKey} models={models} />
                  : <DataSection state={detail} loadingLabel="Loading series">{() => null}</DataSection>}
              </Panel>
            </div>

            <Panel title="Daily comparison" subtitle="Validation window, 28 consecutive days from the origin">
              <details>
                <summary className="cursor-pointer text-sm font-medium text-brand">Show the 28-day table</summary>
                <div className="mt-3">
                  <DataSection state={forecasts} loadingLabel="Loading daily values">
                    {(bundle) => <DailyTable bundle={bundle} models={models} />}
                  </DataSection>
                </div>
              </details>
            </Panel>
          </>
        )}
        <p className="text-xs text-muted">
          Saved fixed-origin validation forecasts (Phase 4 registry via the Phase 6 reporting layer); the final 28-day holdout is not
          shown here. Export {forecasts.data?.meta.exportVersion ?? "—"}.
        </p>
      </div>
    </div>
  );
}
