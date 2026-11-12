"use client";

import { DivergingBars, StackedBars } from "@/components/charts/Bars";
import { ScatterChart, type ScatterPoint } from "@/components/charts/Scatter";
import { DatasetSelector, FieldLabel, PatternSelect } from "@/components/selectors/Selectors";
import { DataTable } from "@/components/ui/DataTable";
import { Icon } from "@/components/ui/Icon";
import { Badge, Panel, SeriesKey } from "@/components/ui/Panel";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import { Segmented } from "@/components/ui/Segmented";
import { EmptyState } from "@/components/ui/States";
import { apiPath } from "@/lib/api/client";
import type { DatasetKey, PolicyKey, StudyMeasures, StudyResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { num, pct, relativeChange, signedPct } from "@/lib/format";
import { DATASET_LABEL, MODEL_STYLE, POLICY_ORDER, POLICY_STYLE, patternLabel } from "@/lib/labels";
import { originKeySchema } from "@/lib/schemas";
import { resolveSelection } from "@/lib/selection";
import { useQueryState } from "@/lib/useQueryState";
import { DataSection } from "../common/DataSection";
import { downloadText, toCsv } from "../common/download";

type Row = StudyMeasures & { scenarioKey: string; scenario: string; scenarioGroup: string; policyKey: PolicyKey };
const SHAPES = ["circle", "square", "diamond", "triangle"] as const;
const FOLDS = [1, 2, 3, 4];

/** Background tint for a signed relative difference; the signed text value is always printed in the cell. */
function tint(value: number | null): string {
  if (value === null) return "";
  const m = Math.abs(value);
  const step = m >= 0.05 ? 2 : m >= 0.01 ? 1 : 0;
  if (step === 0) return "bg-subtle";
  return value < 0 ? (step === 2 ? "bg-[#cfe0f5]" : "bg-[#e7f0fb]") : (step === 2 ? "bg-[#fbd9c8]" : "bg-[#fdece3]");
}

function Matrix({ data, rows, scenarios, origin, dataset, pattern }: {
  data: StudyResponse; rows: Row[]; scenarios: [string, string, string][]; origin: string; dataset: DatasetKey; pattern: string | null;
}) {
  const cell = (scenario: string, policy: PolicyKey) => rows.find((r) => r.scenarioKey === scenario && r.policyKey === policy);
  const exportCsv = () => {
    const header = ["dataset", "pattern", "origin", "scenario_group", "scenario", "policy", "series_episodes", "mean_cost_ncu",
                    "holding_ncu", "unmet_penalty_ncu", "ordering_ncu", "terminal_ncu", "fill_rate", "stockout_days_per_episode"];
    const lines = scenarios.flatMap(([key, label, group]) => POLICY_ORDER.map((p) => {
      const r = cell(key, p);
      return [dataset, pattern ?? "all", origin === "all" ? "pooled" : origin, group, label, p, r?.seriesEpisodes, r?.meanCostNcu,
              r?.holdingCostNcu, r?.unmetPenaltyNcu, r?.orderingCostNcu, r?.terminalCostNcu, r?.fillRate, r?.stockoutDaysPerEpisode];
    }));
    downloadText(toCsv(header, lines, `${data.meta.ncuNotice ?? "Hypothetical NCU."} Saved Phase 5 study, export ${data.meta.exportVersion}; scenarios are not independent replications.`),
                 `scenario_matrix_${dataset}_${pattern ?? "all"}_${origin === "all" ? "pooled" : origin.replace("|", "_origin")}.csv`);
  };
  return (
    <Panel title="17-scenario cost matrix" id="matrix"
           subtitle={`Hypothetical mean NCU per series-episode · ${origin === "all" ? "pooled over the four origins" : `origin ${origin.split("|")[1]} only`}`}
           actions={<button type="button" onClick={exportCsv}
                            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-subtle">
             <Icon name="download" size={15} />CSV</button>}>
      <DataTable caption="Saved scenario costs across all four policies (hypothetical NCU)" rows={scenarios} rowKey={(r) => r[0]} dense testId="scenario-matrix"
                 columns={[
                   { key: "scenario", header: "Scenario", rowHeader: true, cell: (r) => <span>{r[1]}<span className="block text-xs font-normal text-muted">{r[2]}</span></span> },
                   ...POLICY_ORDER.map((policy) => ({ key: policy, header: POLICY_STYLE[policy].short, align: "right" as const,
                     cell: (r: [string, string, string]) => num(cell(r[0], policy)?.meanCostNcu) })),
                   { key: "fill", header: "ML fill rate", align: "right", cell: (r) => pct(cell(r[0], "selected_ml")?.fillRate) },
                 ]} />
    </Panel>
  );
}

function OriginGrid({ data, scenarios }: { data: StudyResponse; scenarios: [string, string, string][] }) {
  const rel = (scenario: string, fold: number | null) => {
    const src = fold === null ? data.pooled : data.perOrigin.filter((r) => r.fold === fold);
    return relativeChange(src.find((r) => r.scenarioKey === scenario && r.policyKey === "selected_ml")?.meanCostNcu,
                          src.find((r) => r.scenarioKey === scenario && r.policyKey === "moving_average_28")?.meanCostNcu);
  };
  return (
    <Panel title="Scenario × origin: selected ML versus MA28" id="origin-grid"
           subtitle="Relative difference in mean hypothetical cost; negative = ML lower. Each column is the same validation window for every scenario."
           footer="Blue tint: ML lower cost; orange tint: ML higher cost; grey: within ±1%. Values are always printed.">
      <DataTable caption="Selected ML relative mean cost versus MA28 by scenario and origin" rows={scenarios} rowKey={(r) => r[0]} dense testId="origin-grid-table"
                 columns={[
                   { key: "scenario", header: "Scenario", rowHeader: true, cell: (r) => r[1] },
                   ...FOLDS.map((fold) => ({ key: `o${fold}`, header: `Origin ${fold}`, align: "right" as const,
                     cell: (r: [string, string, string]) => { const v = rel(r[0], fold); return <span className={`block rounded px-1.5 py-0.5 ${tint(v)}`}>{signedPct(v)}</span>; } })),
                   { key: "pooled", header: "Pooled", align: "right", cell: (r) => <span className="font-semibold text-ink">{signedPct(rel(r[0], null))}</span> },
                 ]} />
    </Panel>
  );
}

export function ScenarioComparison() {
  const { params, update } = useQueryState();
  const { dataset, pattern } = resolveSelection(params, false);
  const rawOrigin = params.get("origin");
  const origin = rawOrigin && originKeySchema.safeParse(rawOrigin).success && rawOrigin.startsWith(`${dataset}|`) ? rawOrigin : "all";
  const state = useApi<StudyResponse>(apiPath("/inventory/study", { dataset, pattern }));

  return (
    <div className="space-y-5">
      <Panel title="Study filters" subtitle="Saved full-population Phase 5 results (not the curated demo subset)">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
          <div><FieldLabel>Dataset</FieldLabel>
            <DatasetSelector value={dataset} onChange={(d) => update({ dataset: d, origin: null, pattern: null })} /></div>
          <div className="w-full sm:w-64"><FieldLabel htmlFor="study-pattern">Demand pattern</FieldLabel>
            <PatternSelect id="study-pattern" value={pattern} onChange={(p) => update({ pattern: p })} /></div>
          <div><FieldLabel>Validation origin</FieldLabel>
            <Segmented label="Validation origin" size="sm" value={origin} onChange={(o) => update({ origin: o === "all" ? null : o })}
                       options={[{ value: "all", label: "All (pooled)" }, ...FOLDS.map((f) => ({ value: `${dataset}|${f}`, label: `Origin ${f}` }))]} /></div>
        </div>
      </Panel>
      <ScientificNotice kind="caution" title="Scenario-dependent, not independent evidence">
        The 17 scenarios change one hypothetical assumption at a time and reuse the same four validation origins, series and forecasts;
        they are sensitivity analyses, not independent replications, so counting scenarios is not evidence of model superiority.
        Costs are hypothetical normalised cost units (NCU), not currency. Fixed ROP is a low-stock comparator with lower fill rate.
        Demand is represented by saved sales and unmet demand is simulated. No final-holdout targets are used.
      </ScientificNotice>
      <DataSection state={state} loadingLabel="Loading saved Phase 5 scenarios" chart>
        {(data) => {
          const scenarios = [...new Map(data.pooled.map((r) => [r.scenarioKey, [r.scenarioKey, r.scenario, r.scenarioGroup] as [string, string, string]])).values()];
          if (!scenarios.length) {
            return <EmptyState title="No saved study episodes">No {patternLabel(pattern).toLowerCase()} series exist in the {DATASET_LABEL[dataset]} study population. No values are inferred.</EmptyState>;
          }
          const rawScenario = params.get("scenario");
          const selected = scenarios.some(([key]) => key === rawScenario) ? rawScenario as string : scenarios.some(([k]) => k === "base") ? "base" : scenarios[0][0];
          const fold = origin === "all" ? null : Number(origin.split("|")[1]);
          const view: Row[] = fold === null ? data.pooled : data.perOrigin.filter((r) => r.fold === fold);
          const current = POLICY_ORDER.map((p) => view.find((r) => r.scenarioKey === selected && r.policyKey === p)).filter((r): r is Row => Boolean(r));
          const label = scenarios.find(([k]) => k === selected)?.[1] ?? selected;
          const points: ScatterPoint[] = current.flatMap((r) => (r.fillRate === null || r.meanCostNcu === null ? [] : [{
            id: r.policyKey, group: label, label: POLICY_STYLE[r.policyKey].label, x: r.fillRate, y: r.meanCostNcu,
            color: POLICY_STYLE[r.policyKey].color, shape: SHAPES[POLICY_ORDER.indexOf(r.policyKey)],
            detail: `${num(r.stockoutDaysPerEpisode, 2)} stockout days per episode`,
          }]));
          const relBy = (baseline: PolicyKey) => scenarios.map(([key]) => relativeChange(
            view.find((r) => r.scenarioKey === key && r.policyKey === "selected_ml")?.meanCostNcu,
            view.find((r) => r.scenarioKey === key && r.policyKey === baseline)?.meanCostNcu));
          const originRel = FOLDS.map((f) => relativeChange(
            data.perOrigin.find((r) => r.fold === f && r.scenarioKey === selected && r.policyKey === "selected_ml")?.meanCostNcu,
            data.perOrigin.find((r) => r.fold === f && r.scenarioKey === selected && r.policyKey === "moving_average_28")?.meanCostNcu));
          const higherAt = FOLDS.filter((_, i) => originRel[i] !== null && (originRel[i] as number) > 0);
          const lowerAt = FOLDS.filter((_, i) => originRel[i] !== null && (originRel[i] as number) < 0);
          return (
            <>
              <Panel title="Selected scenario" subtitle={`${DATASET_LABEL[dataset]} · ${pattern ? patternLabel(pattern) : "all demand patterns"} · ${fold === null ? "four origins pooled with saved additive totals" : `origin ${fold}`}`}
                     actions={<label className="flex items-center gap-2 text-sm text-ink-2">Scenario
                       <select aria-label="Scenario" value={selected} onChange={(e) => update({ scenario: e.target.value === "base" ? null : e.target.value })}
                               className="h-9 max-w-full rounded-md border border-line bg-surface px-2 text-sm text-ink">
                         {scenarios.map(([key, name, group]) => <option key={key} value={key}>{group}: {name}</option>)}
                       </select></label>}>
                {higherAt.length > 0 && lowerAt.length > 0 && (
                  <div className="mb-4">
                    <ScientificNotice kind="caution" title="Origin-dependent result" compact>
                      In this scenario selected ML has a lower mean hypothetical cost than MA28 at origin{lowerAt.length > 1 ? "s" : ""} {lowerAt.join(", ")} but a higher one at
                      origin{higherAt.length > 1 ? "s" : ""} {higherAt.join(", ")}{dataset === "store_item" && higherAt.includes(4) ? " — the Store Item final-origin cost reversal" : ""}.
                    </ScientificNotice>
                  </div>
                )}
                {higherAt.length === 4 && (
                  <div className="mb-4">
                    <ScientificNotice kind="caution" title="Selected ML not lower-cost here" compact>
                      Selected ML has a higher mean hypothetical cost than MA28 at all four origins in this scenario.
                    </ScientificNotice>
                  </div>
                )}
                <div className="grid gap-6 xl:grid-cols-2">
                  <div className="min-w-0">
                    <p className="mb-2 text-sm font-semibold text-ink">Cost and service trade-off</p>
                    <div className="mb-2 flex flex-wrap gap-3">{current.map((r) => <SeriesKey key={r.policyKey} color={POLICY_STYLE[r.policyKey].color} label={POLICY_STYLE[r.policyKey].short} />)}</div>
                    {points.length ? <ScatterChart testId="scenario-tradeoff" points={points} height={280}
                                                   description={`Mean hypothetical cost against fill rate for each policy, scenario ${label}`}
                                                   xLabel="Fill rate (fulfilled ÷ demanded units)" yLabel="Mean cost (NCU)" formatX={(v) => pct(v, 1)} formatY={(v) => num(v, 0)} />
                      : <EmptyState title="Trade-off undefined">No defined cost and fill-rate pairs for this selection.</EmptyState>}
                    <p className="mt-1 text-xs text-muted">Points with almost identical fill rates overlap; hover a point or use the table below for exact values.</p>
                  </div>
                  <div className="min-w-0">
                    <p className="mb-2 text-sm font-semibold text-ink">Mean cost components per series-episode (NCU)</p>
                    <div className="mb-2 flex flex-wrap gap-3">
                      <SeriesKey color="var(--color-series-ml)" label="Holding" /><SeriesKey color="var(--color-series-snaive)" label="Unmet-demand penalty" />
                      <SeriesKey color="var(--color-series-ma28)" label="Ordering" /><SeriesKey color="var(--color-series-rop)" label="Terminal" />
                    </div>
                    <StackedBars testId="scenario-breakdown" description={`Mean hypothetical cost components by policy, scenario ${label}`} format={(v) => num(v, 2)}
                                 parts={[{ id: "h", label: "Holding", color: "var(--color-series-ml)" }, { id: "p", label: "Unmet-demand penalty", color: "var(--color-series-snaive)" },
                                         { id: "k", label: "Ordering", color: "var(--color-series-ma28)" }, { id: "e", label: "Terminal", color: "var(--color-series-rop)" }]}
                                 rows={current.map((r) => ({ id: r.policyKey, label: POLICY_STYLE[r.policyKey].short,
                                   values: [r.holdingCostNcu ?? 0, r.unmetPenaltyNcu ?? 0, r.orderingCostNcu ?? 0, r.terminalCostNcu ?? 0] }))} />
                  </div>
                </div>
                <div className="mt-5">
                  <DataTable testId="scenario-pooled" caption="Saved Phase 5 policy measures for the selected scenario (hypothetical NCU)" rows={current} rowKey={(r) => r.policyKey}
                             columns={[
                               { key: "policy", header: "Policy", rowHeader: true, cell: (r) => (
                                 <span className="flex flex-col"><SeriesKey color={POLICY_STYLE[r.policyKey].color} dash={POLICY_STYLE[r.policyKey].dash} label={<span className="whitespace-nowrap">{POLICY_STYLE[r.policyKey].short}</span>} />
                                   {r.policyKey === "fixed_reorder_point" && <span className="text-xs font-normal text-caution">Low-stock comparator with lower fill rate</span>}</span>) },
                               { key: "episodes", header: "Series-episodes", align: "right", cell: (r) => num(r.seriesEpisodes, 0) },
                               { key: "cost", header: "Mean cost (NCU)", align: "right", cell: (r) => num(r.meanCostNcu) },
                               { key: "unit", header: "NCU per demanded unit", align: "right", cell: (r) => num(r.costPerDemandedUnitNcu, 3) },
                               { key: "fill", header: "Fill rate", align: "right", cell: (r) => pct(r.fillRate) },
                               { key: "stockout", header: "Stockout days / episode", align: "right", cell: (r) => num(r.stockoutDaysPerEpisode, 2) },
                               { key: "onhand", header: "Avg on-hand", align: "right", cell: (r) => num(r.averageOnHand, 1) },
                               { key: "orders", header: "Orders / episode", align: "right", cell: (r) => num(r.ordersPerEpisode, 2) },
                             ]} />
                </div>
              </Panel>

              <Panel title="Scenario sensitivity: selected ML relative to each baseline" id="sensitivity"
                     subtitle={`(ML mean cost − baseline mean cost) ÷ baseline mean cost, ${fold === null ? "pooled over origins" : `origin ${fold}`}. Negative = ML lower hypothetical cost.`}
                     actions={<div className="flex flex-wrap gap-3"><SeriesKey color={MODEL_STYLE.moving_average_28.color} label="vs MA28" /><SeriesKey color={MODEL_STYLE.seasonal_naive.color} label="vs Seasonal Naive" /></div>}>
                <DivergingBars testId="sensitivity-chart" categories={scenarios.map((s) => s[1])} format={(v) => signedPct(v, 1)}
                               description="Selected ML relative mean hypothetical cost versus MA28 and Seasonal Naive for each frozen scenario"
                               series={[{ id: "ma", label: "vs MA28", color: MODEL_STYLE.moving_average_28.color, values: relBy("moving_average_28") },
                                        { id: "sn", label: "vs Seasonal Naive", color: MODEL_STYLE.seasonal_naive.color, values: relBy("seasonal_naive") }]} />
              </Panel>

              <OriginGrid data={data} scenarios={scenarios} />
              <Matrix data={data} rows={view} scenarios={scenarios} origin={origin} dataset={dataset} pattern={pattern} />

              <Panel title="Per-origin detail for the selected scenario" subtitle="Each origin is a separate 28-day validation window">
                <DataTable testId="scenario-origins" caption="Saved Phase 5 measures for each origin and policy (hypothetical NCU)" dense
                           rows={data.perOrigin.filter((r) => r.scenarioKey === selected)} rowKey={(r) => `${r.originKey}|${r.policyKey}`}
                           highlight={(r) => fold !== null && r.fold === fold}
                           columns={[
                             { key: "origin", header: "Origin", rowHeader: true, cell: (r) => `Origin ${r.fold}` },
                             { key: "policy", header: "Policy", cell: (r) => POLICY_STYLE[r.policyKey].short },
                             { key: "cost", header: "Mean cost (NCU)", align: "right", cell: (r) => num(r.meanCostNcu) },
                             { key: "fill", header: "Fill rate", align: "right", cell: (r) => pct(r.fillRate) },
                             { key: "stockout", header: "Stockout days / episode", align: "right", cell: (r) => num(r.stockoutDaysPerEpisode, 2) },
                             { key: "episodes", header: "Series-episodes", align: "right", cell: (r) => num(r.seriesEpisodes, 0) },
                           ]} />
              </Panel>

              <Panel title="Policy definitions">
                <ul className="grid gap-3 text-sm md:grid-cols-2">
                  {POLICY_ORDER.map((p) => (
                    <li key={p} className="flex gap-2"><SeriesKey color={POLICY_STYLE[p].color} dash={POLICY_STYLE[p].dash} label={<span className="font-medium text-ink">{POLICY_STYLE[p].label}</span>} />
                      <span className="text-ink-2">{POLICY_STYLE[p].description}</span>
                      {p === "fixed_reorder_point" && <Badge tone="caution">Comparator</Badge>}</li>
                  ))}
                </ul>
              </Panel>
              <p className="text-xs text-muted">
                Validation evidence · saved Phase 5 study · export {data.meta.exportVersion}. Mean costs are saved cost totals divided by series-episodes (server-side);
                fill rates are fulfilled ÷ demanded units. — means undefined, never zero.
              </p>
            </>
          );
        }}
      </DataSection>
    </div>
  );
}
