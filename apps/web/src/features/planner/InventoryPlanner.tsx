"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { StackedBars } from "@/components/charts/Bars";
import { TimeChart } from "@/components/charts/TimeChart";
import { DatasetSelector, FieldLabel, OriginSelector, SeriesSelector } from "@/components/selectors/Selectors";
import { DataTable } from "@/components/ui/DataTable";
import { Icon } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { Badge, Panel, SeriesKey } from "@/components/ui/Panel";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import { Segmented } from "@/components/ui/Segmented";
import { ErrorState, LoadingSkeleton } from "@/components/ui/States";
import { ApiError, apiPath, exportPlannerCsv, simulate } from "@/lib/api/client";
import type { DatasetsResponse, PolicyKey, ScenarioInput, SeriesBaseResponse, SimulateRequest, SimulateResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { date, int, ncu, num, pct, signed } from "@/lib/format";
import { DATASET_LABEL, POLICY_ORDER, POLICY_STYLE } from "@/lib/labels";
import { PLANNER_BOUNDS, scenarioSchema } from "@/lib/schemas";
import { DEFAULT_SERIES, resolveSelection } from "@/lib/selection";
import { useQueryState } from "@/lib/useQueryState";
import { DataSection } from "../common/DataSection";
import { downloadBlob } from "../common/download";

/** Phase 5 base scenario = the API schema defaults (the engine's base configuration). */
export const BASE_SCENARIO: ScenarioInput = scenarioSchema.parse({});

type Field = keyof ScenarioInput;
const FIELDS: Record<Field, { label: string; help: string; step: number | "any" }> = {
  leadDays: { label: "Lead time (days)", help: "Days between placing an order and its arrival; orders arrive on day t + L + 1.", step: 1 },
  reviewDays: { label: "Review interval (days)", help: "Orders may be placed every R days.", step: 1 },
  bufferDays: { label: "Buffer (days)", help: "Safety buffer = buffer days × 56-day history mean.", step: 0.5 },
  initialCoverDays: { label: "Initial cover (days)", help: "Starting stock = cover days × 56-day history mean (common to all policies).", step: 0.5 },
  holdingCost: { label: "Holding rate (NCU)", help: "Per unit of closing stock per day.", step: "any" },
  shortageCost: { label: "Unmet-demand penalty (NCU)", help: "Per unit of demand not met (lost sales).", step: "any" },
  fixedOrderCost: { label: "Fixed order rate (NCU)", help: "Per positive order placed.", step: "any" },
  variableOrderCost: { label: "Variable order rate (NCU)", help: "Per unit ordered, charged at placement.", step: "any" },
  terminalCost: { label: "Terminal rate (NCU)", help: "Per unit of stock plus pipeline left at the end of the 28 days.", step: "any" },
  variabilityMultiplier: { label: "Demand variability multiplier", help: "Server-side stress of saved sales: max(0, μ + a·(sales − μ)) with μ the 56-day history mean; 1 = unchanged.", step: "any" },
};
const GROUPS: { title: string; fields: Field[] }[] = [
  { title: "Replenishment timing", fields: ["leadDays", "reviewDays", "bufferDays", "initialCoverDays"] },
  { title: "Hypothetical cost rates", fields: ["holdingCost", "shortageCost", "fixedOrderCost", "variableOrderCost", "terminalCost"] },
  { title: "Demand stress", fields: ["variabilityMultiplier"] },
];

const isBase = (s: ScenarioInput) => (Object.keys(BASE_SCENARIO) as Field[]).every((k) => s[k] === BASE_SCENARIO[k]);
const signature = (r: SimulateRequest) => JSON.stringify(r);

function fieldErrors(scenario: ScenarioInput): Partial<Record<Field | "form", string>> {
  const parsed = scenarioSchema.safeParse(scenario);
  if (parsed.success) return {};
  const errors: Partial<Record<Field | "form", string>> = {};
  for (const issue of parsed.error.issues) {
    const key = (issue.path[0] as Field | undefined) ?? "form";
    errors[key] ??= key === "form" ? issue.message
      : `Enter a number from ${PLANNER_BOUNDS[key][0]} to ${PLANNER_BOUNDS[key][1]}${FIELDS[key].step === 1 ? " (whole days)" : ""}.`;
  }
  return errors;
}

export function InventoryPlanner() {
  const { params, update } = useQueryState();
  const selection = resolveSelection(params);
  const seriesKey = selection.series ?? DEFAULT_SERIES[selection.dataset];
  const datasets = useApi<DatasetsResponse>(apiPath("/datasets"));
  const info = datasets.data?.datasets.find((d) => d.datasetKey === selection.dataset);

  // Inputs persist across series/origin changes and page navigation (Activity keeps this state alive).
  const [scenario, setScenario] = useState<ScenarioInput>(BASE_SCENARIO);
  const [policies, setPolicies] = useState<PolicyKey[]>([...POLICY_ORDER]);
  const [run, setRun] = useState<{ key: string; result?: SimulateResponse; error?: ApiError } | null>(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<ApiError | null>(null);
  const inFlight = useRef<AbortController | null>(null);
  useEffect(() => () => inFlight.current?.abort(), []);

  const errors = fieldErrors(scenario);
  const valid = Object.keys(errors).length === 0 && policies.length > 0;
  const request: SimulateRequest = { seriesKey, originKey: selection.origin, policies, scenario };
  const current = run && run.key === signature(request) ? run : null; // never show a result for other inputs

  async function execute() {
    if (!valid || busy) return;
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    const key = signature(request);
    setBusy(true);
    setExportError(null);
    try {
      const result = await simulate(request, controller.signal);
      setRun({ key, result });
    } catch (e) {
      if (controller.signal.aborted) return;
      setRun({ key, error: e instanceof ApiError ? e : new ApiError(0, "network_error", "The simulation service could not be reached.") });
    } finally {
      if (inFlight.current === controller) {
        inFlight.current = null;
        setBusy(false);
      }
    }
  }

  async function exportRun(result: SimulateResponse) {
    if (exporting) return;
    setExporting(true);
    setExportError(null);
    try {
      const file = await exportPlannerCsv({ seriesKey: result.inputs.seriesKey, originKey: result.inputs.originKey,
                                            policies: result.inputs.policies, scenario: result.inputs.scenario });
      downloadBlob(file.blob, file.filename);
    } catch (e) {
      setExportError(e instanceof ApiError ? e : new ApiError(0, "network_error", "The export service could not be reached."));
    } finally {
      setExporting(false);
    }
  }

  const togglePolicy = (p: PolicyKey) => setPolicies((list) => {
    const next = list.includes(p) ? list.filter((x) => x !== p) : [...list, p];
    return next.length === 0 ? list : POLICY_ORDER.filter((x) => next.includes(x));
  });

  return (
    <div className="space-y-5">
      <ScientificNotice kind="hypothetical" title="Hypothetical simulation">
        Runs execute the verified Phase 5 Python engine (via the server) on saved validation-window sales and the saved fixed-origin
        forecasts; your browser never sends demand. Costs are normalised cost units (NCU), not currency, and simulated differences are
        not realised savings. The fixed reorder point is a low-stock comparator with lower fill rate.
      </ScientificNotice>
      {selection.corrected && (
        <ScientificNotice kind="caution" title="Link adjusted">Invalid or incompatible link parameters were replaced with defaults.</ScientificNotice>
      )}

      <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Panel title="1 · Series and origin" subtitle={info?.coverageNote}>
          <div className="space-y-4">
            <div>
              <FieldLabel>Dataset</FieldLabel>
              <DatasetSelector value={selection.dataset}
                               onChange={(dataset) => update({ dataset, series: DEFAULT_SERIES[dataset], origin: `${dataset}|4` })} />
            </div>
            <SeriesSelector dataset={selection.dataset} pattern={null} value={seriesKey} onChange={(series) => update({ series })} />
            <div>
              <FieldLabel>Validation origin</FieldLabel>
              {info ? <OriginSelector origins={info.origins} value={selection.origin} onChange={(origin) => update({ origin })} />
                : datasets.error ? <ErrorState error={datasets.error} onRetry={datasets.reload} /> : <div className="skeleton h-8 w-full" />}
            </div>
            <Link className="inline-flex items-center gap-1 text-sm text-brand hover:underline"
                  href={`/forecasts?series=${encodeURIComponent(seriesKey)}&origin=${encodeURIComponent(selection.origin)}`}>
              View this series in the Forecast Explorer <Icon name="arrow" size={14} />
            </Link>
          </div>
        </Panel>

        <Panel title="2 · Policies and scenario" subtitle="Bounds published by the Phase 7B API; the engine validates them again"
               actions={isBase(scenario) ? <Badge tone="teal">Matches published scenario: base</Badge> : <Badge tone="caution">Custom hypothetical scenario</Badge>}>
          <form noValidate onSubmit={(e) => { e.preventDefault(); void execute(); }}>
            <fieldset disabled={busy} className="space-y-5">
              <fieldset>
                <legend className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-2">Forecast source / policy</legend>
                <div className="flex flex-wrap gap-2">
                  {POLICY_ORDER.map((p) => {
                    const on = policies.includes(p);
                    return (
                      <label key={p} className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm ${
                        on ? "border-ink/25 bg-surface text-ink" : "border-line bg-subtle text-muted"}`}>
                        <input type="checkbox" checked={on} disabled={on && policies.length === 1} onChange={() => togglePolicy(p)}
                               className="h-3.5 w-3.5 accent-[var(--color-brand)]" />
                        <SeriesKey color={POLICY_STYLE[p].color} dash={POLICY_STYLE[p].dash} label={POLICY_STYLE[p].short} />
                      </label>
                    );
                  })}
                </div>
                {!policies.includes("moving_average_28") && (
                  <p className="mt-1 text-xs text-muted">Include MA28 to see each policy&apos;s difference from the MA28 baseline.</p>
                )}
              </fieldset>
              {GROUPS.map((group) => (
                <div key={group.title}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-2">{group.title}</p>
                  <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                    {group.fields.map((key) => {
                      const id = `planner-${key}`;
                      const error = errors[key];
                      return (
                        <div key={key}>
                          <label htmlFor={id} className="block text-sm font-medium text-ink">{FIELDS[key].label}</label>
                          <input id={id} type="number" inputMode="decimal" required min={PLANNER_BOUNDS[key][0]} max={PLANNER_BOUNDS[key][1]}
                                 step={FIELDS[key].step} aria-invalid={Boolean(error)} aria-describedby={`${id}-help`}
                                 value={Number.isNaN(scenario[key]) ? "" : scenario[key]}
                                 onChange={(e) => setScenario({ ...scenario, [key]: e.target.valueAsNumber })}
                                 className={`tabular mt-1 block h-9 w-full rounded-md border bg-surface px-2.5 text-sm ${error ? "border-danger" : "border-line"}`} />
                          <p id={`${id}-help`} className={`mt-1 text-xs ${error ? "text-danger" : "text-muted"}`}>
                            {error ?? `${FIELDS[key].help} Range ${PLANNER_BOUNDS[key][0]}–${PLANNER_BOUNDS[key][1]}; base ${BASE_SCENARIO[key]}.`}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
              {errors.form && <p role="alert" className="text-sm text-danger">{errors.form}</p>}
            </fieldset>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button type="submit" disabled={busy || !valid}
                      className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-[#174c8e] disabled:cursor-not-allowed disabled:opacity-50">
                <Icon name="planner" size={16} />{busy ? "Running the Phase 5 engine…" : "Run simulation"}
              </button>
              <button type="button" disabled={busy} onClick={() => { setScenario(BASE_SCENARIO); setPolicies([...POLICY_ORDER]); }}
                      className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-subtle disabled:opacity-50">
                <Icon name="reset" size={15} />Reset to Phase 5 base
              </button>
              {!valid && <p role="alert" className="text-sm text-danger">Correct the highlighted inputs to run.</p>}
            </div>
          </form>
        </Panel>
      </div>

      <section aria-live="polite" aria-label="Simulation results" className="space-y-5">
        {busy && <Panel title="3 · Results"><LoadingSkeleton label="Running the Phase 5 engine" chart rows={2} /></Panel>}
        {!busy && !current && (
          <Panel title="3 · Results">
            <p className="text-sm text-muted">{run ? "Inputs changed since the last run. Run the simulation again to see results for these inputs."
              : "Run the simulation to see hypothetical cost, service and inventory trajectories for the selected series and origin."}</p>
          </Panel>
        )}
        {!busy && current?.error && (
          <>
            <ErrorState error={current.error} title="Simulation unavailable" onRetry={() => void execute()} />
            {(current.error.code === "engine_unavailable" || current.error.code === "timeout") && (
              <PrecomputedFallback seriesKey={seriesKey} originKey={selection.origin} userIsBase={isBase(scenario)} />
            )}
          </>
        )}
        {!busy && current?.result && (
          <Results result={current.result} exporting={exporting} exportError={exportError} onExport={() => void exportRun(current.result!)} />
        )}
      </section>
    </div>
  );
}

function PrecomputedFallback({ seriesKey, originKey, userIsBase }: { seriesKey: string; originKey: string; userIsBase: boolean }) {
  const state = useApi<SeriesBaseResponse>(apiPath("/inventory/series-base", { series: seriesKey, origin: originKey }));
  return (
    <Panel title="Precomputed Phase 5 results (fallback)" subtitle="Saved base-scenario study values for this series and origin">
      <div className="mb-3">
        <ScientificNotice kind="fallback" title="Not your scenario">
          {userIsBase
            ? "Your inputs equal the published base scenario. These saved values were produced by the Phase 5 study, not by a run just now."
            : "These saved values are for the published base scenario only. They are not the result of your custom inputs."}
        </ScientificNotice>
      </div>
      <DataSection state={state} loadingLabel="Loading precomputed results">
        {(d) => (
          <DataTable caption="Precomputed Phase 5 base-scenario results (hypothetical NCU)" testId="fallback-table"
                     rows={POLICY_ORDER.map((p) => d.rows.find((r) => r.policyKey === p)).filter((r): r is SeriesBaseResponse["rows"][number] => Boolean(r))}
                     rowKey={(r) => r.policyKey}
                     columns={[
                       { key: "policy", header: "Policy (base scenario)", rowHeader: true, cell: (r) => POLICY_STYLE[r.policyKey].label },
                       { key: "cost", header: "Total cost (NCU)", align: "right", cell: (r) => ncu(r.totalCost, 0) },
                       { key: "fill", header: "Fulfilled / demand units", align: "right", cell: (r) => `${int(r.fulfilledUnits)} / ${int(r.demandUnits)}` },
                       { key: "stockout", header: "Stockout days", align: "right", cell: (r) => int(r.stockoutDays) },
                       { key: "orders", header: "Orders", align: "right", cell: (r) => int(r.orders) },
                     ]} />
        )}
      </DataSection>
    </Panel>
  );
}

function Results({ result, onExport, exporting, exportError }: {
  result: SimulateResponse;
  onExport: () => void;
  exporting: boolean;
  exportError: ApiError | null;
}) {
  const [focus, setFocus] = useState<PolicyKey>(result.policies[0].policyKey);
  const focused = result.policies.find((p) => p.policyKey === focus) ?? result.policies[0];
  const reference = result.studyReference;
  const s = result.inputs.scenario;
  return (
    <>
      <Panel title="3 · Results" subtitle={`One series, one 28-day validation episode (${date(result.inputs.dates[0])} – ${date(result.inputs.dates[result.inputs.dates.length - 1])})`}
             actions={<button type="button" disabled={exporting} onClick={onExport}
                              className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-subtle disabled:opacity-50">
               <Icon name="download" size={15} />{exporting ? "Exporting…" : "Export planner CSV"}</button>}
             footer={<>Declared scenario: lead {s.leadDays} d · review {s.reviewDays} d · buffer {s.bufferDays} d · initial cover {s.initialCoverDays} d ·
               holding {s.holdingCost} · penalty {s.shortageCost} · fixed order {s.fixedOrderCost} · variable {s.variableOrderCost} · terminal {s.terminalCost} ·
               variability ×{s.variabilityMultiplier} · 56-day history mean {num(result.inputs.historicalMean56, 2)} units/day.</>}>
        {exportError && <div className="mb-3"><ErrorState error={exportError} title="CSV export failed" onRetry={onExport} /></div>}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {result.policies.map((p) => (
            <MetricCard key={p.policyKey} accent={POLICY_STYLE[p.policyKey].color} testId={`planner-card-${p.policyKey}`}
                        label={POLICY_STYLE[p.policyKey].label} value={ncu(p.summary.totalCost, 0)}
                        detail={<>
                          <span className="block">Fill rate {pct(p.summary.fillRate)} · stockout days {int(p.summary.stockoutDays)}</span>
                          <span className="block">Avg on-hand {num(p.summary.averageOnHand, 1)} · orders {int(p.summary.orders)}</span>
                        </>}
                        context={p.policyKey === "fixed_reorder_point" ? "Low-stock comparator with lower fill rate · hypothetical NCU" : "Hypothetical total cost (NCU)"} />
          ))}
        </div>
        {result.comparison && (
          <div className="mt-4 rounded-md border border-line bg-subtle px-3 py-2.5" data-testid="planner-deltas">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-2">Difference from MA28 order-up-to (server-computed)</p>
            <ul className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm">
              {result.comparison.deltas.map((d) => (
                <li key={d.policyKey} className="tabular text-ink-2">
                  <span className="font-medium text-ink">{POLICY_STYLE[d.policyKey].short}</span>: {signed(d.totalCostNcu, 0)} NCU,{" "}
                  {d.fillRatePoints === null ? "fill rate undefined" : `${signed(d.fillRatePoints, 2)} fill-rate points`}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="mt-3 text-sm text-ink-2" data-testid="study-reference">
          {reference ? <><Badge tone="teal">Published scenario: {reference.scenarioMatched.replace(/_/g, " ")}</Badge> {reference.note}</>
            : <><Badge tone="caution">User hypothetical</Badge> These inputs are outside the 17 published Phase 5 scenarios.</>}
        </p>
        <DataTable testId="planner-results" caption="Simulation results by policy (hypothetical NCU)" rows={result.policies} rowKey={(r) => r.policyKey}
                   columns={[
                     { key: "policy", header: "Policy", rowHeader: true, cell: (r) => POLICY_STYLE[r.policyKey].short },
                     { key: "cost", header: "Total cost (NCU)", align: "right", cell: (r) => ncu(r.summary.totalCost, 0) },
                     ...(reference && Object.keys(reference.phase5TotalCostNcu).length > 0 ? [{
                       key: "reference", header: "Saved Phase 5 (NCU)", align: "right" as const,
                       cell: (r: SimulateResponse["policies"][number]) => ncu(reference.phase5TotalCostNcu[r.policyKey], 0) }] : []),
                     { key: "fill", header: "Fill rate", align: "right", cell: (r) => pct(r.summary.fillRate) },
                     { key: "unmet", header: "Unmet units", align: "right", cell: (r) => int(r.summary.unmetUnits) },
                     { key: "stockout", header: "Stockout days", align: "right", cell: (r) => int(r.summary.stockoutDays) },
                     { key: "stock", header: "Avg on-hand", align: "right", cell: (r) => num(r.summary.averageOnHand, 1) },
                     { key: "orders", header: "Orders", align: "right", cell: (r) => int(r.summary.orders) },
                   ]} />
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Cost breakdown" subtitle="Engine-returned components of total hypothetical cost (NCU)">
          <div className="mb-2 flex flex-wrap gap-4">
            <SeriesKey color="var(--color-series-ml)" label="Holding" />
            <SeriesKey color="var(--color-series-snaive)" label="Unmet-demand penalty" />
            <SeriesKey color="var(--color-series-ma28)" label="Ordering" />
            <SeriesKey color="var(--color-series-rop)" label="Terminal" />
          </div>
          <StackedBars testId="cost-breakdown" description="Hypothetical cost components by policy"
                       format={(v) => num(v, 0)}
                       parts={[{ id: "h", label: "Holding", color: "var(--color-series-ml)" },
                               { id: "p", label: "Unmet-demand penalty", color: "var(--color-series-snaive)" },
                               { id: "k", label: "Ordering", color: "var(--color-series-ma28)" },
                               { id: "e", label: "Terminal", color: "var(--color-series-rop)" }]}
                       rows={result.policies.map((p) => ({ id: p.policyKey, label: POLICY_STYLE[p.policyKey].short,
                         values: [p.summary.holdingCost, p.summary.shortageCost, p.summary.orderingCost, p.summary.terminalCost] }))} />
        </Panel>
        <Panel title="Closing inventory by policy" subtitle="Units on hand at the end of each validation day">
          <div className="mb-2 flex flex-wrap gap-4">
            {result.policies.map((p) => <SeriesKey key={p.policyKey} color={POLICY_STYLE[p.policyKey].color} dash={POLICY_STYLE[p.policyKey].dash} label={POLICY_STYLE[p.policyKey].short} />)}
          </div>
          <TimeChart testId="inventory-chart" dates={result.inputs.dates} height={260} valueDigits={0}
                     description="Daily closing on-hand inventory for the simulated policies"
                     series={result.policies.map((p) => ({ id: p.policyKey, label: POLICY_STYLE[p.policyKey].short, color: POLICY_STYLE[p.policyKey].color,
                                                           dash: POLICY_STYLE[p.policyKey].dash, kind: "step" as const, values: p.daily.map((d) => d.closingStock) }))} />
        </Panel>
      </div>

      <Panel title="Inventory trajectory and replenishment timing" subtitle="One policy at a time: demand, closing stock, inventory position and orders placed"
             actions={<Segmented label="Policy shown" size="sm" value={focused.policyKey} onChange={setFocus}
                                 options={result.policies.map((p) => ({ value: p.policyKey, label: POLICY_STYLE[p.policyKey].short }))} />}>
        <div className="mb-2 flex flex-wrap gap-4">
          <SeriesKey color="#b9c5d3" label="Demand (saved sales)" />
          <SeriesKey color={POLICY_STYLE[focused.policyKey].color} label="Closing stock" />
          <SeriesKey color="var(--color-ink-2)" dash="4 3" label="Inventory position (stock + pipeline)" />
          <span className="inline-flex items-center gap-1.5 text-sm text-ink-2"><svg width="12" height="10" aria-hidden="true"><path d="M6,1l5,8h-10z" fill="var(--color-ink)" /></svg>Order placed (quantity)</span>
        </div>
        <TimeChart testId="trajectory-chart" dates={result.inputs.dates} height={300} valueDigits={0}
                   description={`Daily inventory trajectory for ${POLICY_STYLE[focused.policyKey].label}`}
                   series={[
                     { id: "demand", label: "Demand", color: "#b9c5d3", kind: "bars", values: focused.daily.map((d) => d.demand) },
                     { id: "closing", label: "Closing stock", color: POLICY_STYLE[focused.policyKey].color, kind: "step", values: focused.daily.map((d) => d.closingStock) },
                     { id: "position", label: "Inventory position", color: "var(--color-ink-2)", dash: "4 3", width: 1.5, values: focused.daily.map((d) => d.inventoryPosition) },
                     { id: "orders", label: "Order placed", color: "var(--color-ink)", kind: "markers", values: focused.daily.map((d) => (d.orderQuantity > 0 ? d.orderQuantity : null)) },
                   ]} />
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-brand">Daily engine events for {POLICY_STYLE[focused.policyKey].short}</summary>
          <p className="my-2 text-xs text-muted">
            Holding {ncu(focused.summary.holdingCost, 0)} · unmet-demand penalty {ncu(focused.summary.shortageCost, 0)} · ordering {ncu(focused.summary.orderingCost, 0)} ·
            terminal {ncu(focused.summary.terminalCost, 0)} (all hypothetical). Received {int(focused.summary.receivedUnits)} of {int(focused.summary.placedUnits)} units ordered.
          </p>
          <DataTable caption={`${POLICY_STYLE[focused.policyKey].short} daily engine events`} rows={focused.daily} rowKey={(r) => r.date} dense testId="daily-events"
                     columns={[
                       { key: "date", header: "Date", rowHeader: true, cell: (r) => date(r.date, false) },
                       { key: "opening", header: "Opening", align: "right", cell: (r) => int(r.openingStock) },
                       { key: "receipts", header: "Receipts", align: "right", cell: (r) => int(r.receipts) },
                       { key: "demand", header: "Demand", align: "right", cell: (r) => int(r.demand) },
                       { key: "unmet", header: "Unmet", align: "right", cell: (r) => int(r.unmet) },
                       { key: "closing", header: "Closing", align: "right", cell: (r) => int(r.closingStock) },
                       { key: "pipeline", header: "Pipeline", align: "right", cell: (r) => int(r.pipelineAfter) },
                       { key: "order", header: "Order", align: "right", cell: (r) => int(r.orderQuantity) },
                       { key: "holding", header: "Holding (NCU)", align: "right", cell: (r) => num(r.holdingCost, 0) },
                       { key: "penalty", header: "Penalty (NCU)", align: "right", cell: (r) => num(r.shortageCost, 0) },
                       { key: "ordering", header: "Ordering (NCU)", align: "right", cell: (r) => num(r.orderingCost, 0) },
                     ]} />
        </details>
      </Panel>

      <p className="text-xs text-muted">
        {DATASET_LABEL[result.inputs.seriesKey.startsWith("m5|") ? "m5" : "store_item"]} · validation evidence · export {result.meta.exportVersion} ·
        engine {result.meta.engineVersion} · request {result.meta.requestId}. Demand source: {result.inputs.demandSource}. — means undefined, never zero.
      </p>
    </>
  );
}
