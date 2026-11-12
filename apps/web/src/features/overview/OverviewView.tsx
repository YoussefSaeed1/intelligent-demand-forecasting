"use client";

import Link from "next/link";
import { useState } from "react";
import { DivergingBars, GroupedColumns } from "@/components/charts/Bars";
import { DataTable } from "@/components/ui/DataTable";
import { Icon, type IconName } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { Badge, Panel, SeriesKey } from "@/components/ui/Panel";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import { Segmented } from "@/components/ui/Segmented";
import { costRelativeByOrigin, datasetFindings, originMeanMae, perOriginMae, pooledRow } from "@/lib/analytics";
import { apiPath } from "@/lib/api/client";
import type { AggregateResponse, Dataset, DatasetKey, DatasetsResponse, ResearchResponse, StudyPooledRow, StudyResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { int, ncu, num, pct, relativeChange, signedPct, units4 } from "@/lib/format";
import { ALGORITHM_LABEL, COVERAGE_LABEL, DATASET_LABEL, MODEL_ORDER, MODEL_STYLE, POLICY_ORDER, POLICY_STYLE } from "@/lib/labels";
import { combine, DataSection } from "../common/DataSection";

const DATASETS: DatasetKey[] = ["store_item", "m5"];

function useDatasetBundle(dataset: DatasetKey) {
  const aggregate = useApi<AggregateResponse>(apiPath("/metrics/aggregate", { dataset }));
  const study = useApi<StudyResponse>(apiPath("/inventory/study", { dataset }));
  return combine<[AggregateResponse, StudyResponse]>([aggregate, study]);
}

function DatasetHeadline({ info, aggregate, study }: { info: Dataset; aggregate: AggregateResponse; study: StudyResponse }) {
  const selected = info.models.find((m) => m.isSelectedModel === "Yes");
  const mae = Object.fromEntries(MODEL_ORDER.map((r) => [r, originMeanMae(aggregate.rows, r)]));
  const ml = pooledRow(study.pooled, "base", "selected_ml");
  const ma = pooledRow(study.pooled, "base", "moving_average_28");
  const sn = pooledRow(study.pooled, "base", "seasonal_naive");
  return (
    <Panel title={info.dataset} subtitle={info.datasetDescription}
           actions={<Badge tone={info.datasetKey === "m5" ? "brand" : "teal"}>{COVERAGE_LABEL[info.datasetKey]}</Badge>}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <MetricCard label="Research series" value={int(info.seriesCount)} testId={`kpi-series-${info.datasetKey}`}
                    detail={`${int(info.curatedSeries)} available in the demo`}
                    context={`${info.origins.length} validation origins · 28-day horizon`} />
        <MetricCard label="Selected forecasting model" value={ALGORITHM_LABEL[selected?.algorithm ?? ""] ?? selected?.algorithm ?? "—"}
                    detail={<span className="text-xs">Trial <code>{info.selectedTrial}</code></span>}
                    context="Frozen before the final holdout (Phase 4)" accent="var(--color-series-ml)" />
        <MetricCard label="Validation MAE · selected ML" value={units4(mae.selected_ml)} testId={`kpi-mae-${info.datasetKey}`}
                    accent="var(--color-series-ml)"
                    detail={<>
                      <span className="block">{signedPct(relativeChange(mae.selected_ml, mae.moving_average_28))} vs MA28 ({units4(mae.moving_average_28)})</span>
                      <span className="block">{signedPct(relativeChange(mae.selected_ml, mae.seasonal_naive))} vs Seasonal Naive ({units4(mae.seasonal_naive)})</span>
                    </>}
                    context="Mean of the four validation-origin MAEs, full population (lower is better)" />
        <MetricCard label="Mean hypothetical cost · selected ML" value={ncu(ml?.meanCostNcu)} testId={`kpi-cost-${info.datasetKey}`}
                    accent="var(--color-series-ml)"
                    detail={<>
                      <span className="block">{signedPct(relativeChange(ml?.meanCostNcu, ma?.meanCostNcu))} vs MA28 order-up-to</span>
                      <span className="block">{signedPct(relativeChange(ml?.meanCostNcu, sn?.meanCostNcu))} vs Seasonal Naive order-up-to</span>
                    </>}
                    context={`Base scenario, per series-episode, pooled over ${ml?.origins ?? 4} origins. Hypothetical NCU, not savings.`} />
      </div>
      <p className="mt-3 text-xs text-muted">
        Fill rate (base): selected ML {pct(ml?.fillRate)}, MA28 {pct(ma?.fillRate)}, Seasonal Naive {pct(sn?.fillRate)}.
      </p>
    </Panel>
  );
}

function PolicyTable({ rows }: { rows: StudyPooledRow[] }) {
  const ordered = POLICY_ORDER.map((p) => rows.find((r) => r.scenarioKey === "base" && r.policyKey === p)).filter(Boolean) as StudyPooledRow[];
  return (
    <DataTable caption="Base-scenario hypothetical cost and service by inventory policy, pooled over four validation origins"
               rows={ordered} rowKey={(r) => r.policyKey} testId="policy-table"
               columns={[
                 { key: "policy", header: "Policy", rowHeader: true, cell: (r) => (
                   <span className="flex flex-col gap-0.5">
                     <SeriesKey color={POLICY_STYLE[r.policyKey].color} dash={POLICY_STYLE[r.policyKey].dash} label={POLICY_STYLE[r.policyKey].label} />
                     {r.policyKey === "fixed_reorder_point" && <span className="text-xs font-normal text-caution">Low-stock comparator with lower fill rate</span>}
                   </span>) },
                 { key: "cost", header: "Mean cost (NCU)", align: "right", cell: (r) => num(r.meanCostNcu) },
                 { key: "holding", header: "Holding", align: "right", cell: (r) => num(r.holdingCostNcu) },
                 { key: "shortage", header: "Shortage", align: "right", cell: (r) => num(r.unmetPenaltyNcu) },
                 { key: "ordering", header: "Ordering", align: "right", cell: (r) => num(r.orderingCostNcu) },
                 { key: "fill", header: "Fill rate", align: "right", cell: (r) => pct(r.fillRate) },
                 { key: "stockout", header: "Stockout days", align: "right", cell: (r) => num(r.stockoutDaysPerEpisode) },
                 { key: "onhand", header: "Avg on-hand", align: "right", cell: (r) => num(r.averageOnHand, 1) },
               ]} />
  );
}

const EVIDENCE: { icon: IconName; title: string; tone: string; body: string }[] = [
  { icon: "check", title: "Validated", tone: "text-teal",
    body: "Forecast accuracy at four expanding validation origins (28 days each) on the full research populations: 500 Store Item and 30,490 M5 series." },
  { icon: "shield", title: "Reported", tone: "text-ink-2",
    body: "The one-time final-holdout assessment from Phase 4, shown as recorded on the Research page. It is never recomputed and the final holdout stays sealed." },
  { icon: "flask", title: "Hypothetical", tone: "text-caution",
    body: "Inventory costs in normalised cost units (NCU) from a simulation under stated assumptions. Simulated differences are not realised savings." },
];

export function OverviewView() {
  const datasets = useApi<DatasetsResponse>(apiPath("/datasets"));
  const research = useApi<ResearchResponse>(apiPath("/research"));
  const storeItem = useDatasetBundle("store_item");
  const m5 = useDatasetBundle("m5");
  const bundles = { store_item: storeItem, m5 };
  const [tableDataset, setTableDataset] = useState<DatasetKey>("store_item");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {EVIDENCE.map((e) => (
          <div key={e.title} className="rounded-lg border border-line bg-surface p-4">
            <p className={`flex items-center gap-2 text-sm font-semibold ${e.tone}`}><Icon name={e.icon} size={17} />{e.title}</p>
            <p className="mt-1.5 text-sm text-ink-2">{e.body}</p>
          </div>
        ))}
      </div>

      <DataSection state={datasets} loadingLabel="Loading datasets" rows={4}>
        {(d) => (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {DATASETS.map((key) => {
              const info = d.datasets.find((x) => x.datasetKey === key);
              return info ? (
                <DataSection key={key} state={bundles[key]} loadingLabel={`Loading ${DATASET_LABEL[key]} results`} rows={5}>
                  {([aggregate, study]) => <DatasetHeadline info={info} aggregate={aggregate} study={study} />}
                </DataSection>
              ) : null;
            })}
          </div>
        )}
      </DataSection>

      <Panel title="Forecast accuracy by validation origin" id="origin-accuracy"
             subtitle="Pooled MAE per origin, full research population. Lower is better; the three models are always shown together."
             actions={<div className="flex flex-wrap gap-3">{MODEL_ORDER.map((r) => <SeriesKey key={r} color={MODEL_STYLE[r].color} label={MODEL_STYLE[r].short} />)}</div>}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {DATASETS.map((key) => (
            <div key={key} className="min-w-0">
              <p className="mb-2 text-sm font-semibold text-ink">{DATASET_LABEL[key]}</p>
              <DataSection state={bundles[key]} chart rows={0} loadingLabel="Loading accuracy">
                {([aggregate]) => (
                  <GroupedColumns testId={`origin-mae-${key}`} categories={["Origin 1", "Origin 2", "Origin 3", "Origin 4"]}
                                  description={`${DATASET_LABEL[key]} validation MAE by origin for selected ML, MA28 and Seasonal Naive`}
                                  format={(v) => units4(v)}
                                  series={MODEL_ORDER.map((r) => ({ id: r, label: MODEL_STYLE[r].short, color: MODEL_STYLE[r].color,
                                                                     values: perOriginMae(aggregate.rows, r).map((x) => x.mae) }))} />
                )}
              </DataSection>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Hypothetical cost of selected ML relative to each baseline, by origin" id="origin-cost"
             subtitle="Base scenario, full population: (ML mean cost − baseline mean cost) / baseline mean cost. Negative means lower simulated cost."
             actions={<div className="flex flex-wrap gap-3">
               <SeriesKey color={MODEL_STYLE.moving_average_28.color} label="vs MA28 order-up-to" />
               <SeriesKey color={MODEL_STYLE.seasonal_naive.color} label="vs Seasonal Naive order-up-to" />
             </div>}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {DATASETS.map((key) => (
            <div key={key} className="min-w-0">
              <p className="mb-2 text-sm font-semibold text-ink">{DATASET_LABEL[key]}</p>
              <DataSection state={bundles[key]} chart rows={0} loadingLabel="Loading costs">
                {([, study]) => {
                  const vsMa = costRelativeByOrigin(study.perOrigin, "base", "moving_average_28");
                  const vsSn = costRelativeByOrigin(study.perOrigin, "base", "seasonal_naive");
                  const reversed = vsMa.filter((v) => v !== null && v > 0).length;
                  return (
                    <>
                      <DivergingBars testId={`origin-cost-${key}`} categories={["Origin 1", "Origin 2", "Origin 3", "Origin 4"]}
                                     description={`${DATASET_LABEL[key]} selected ML relative hypothetical cost per origin`}
                                     format={(v) => signedPct(v, 1)}
                                     series={[{ id: "ma", label: "vs MA28", color: MODEL_STYLE.moving_average_28.color, values: vsMa },
                                              { id: "sn", label: "vs Seasonal Naive", color: MODEL_STYLE.seasonal_naive.color, values: vsSn }]} />
                      {reversed > 0 && (
                        <div className="mt-2">
                          <ScientificNotice kind="caution" compact title="Not uniform across origins">
                            Selected ML has a higher simulated cost than MA28 at {reversed} of 4 origins
                            {key === "store_item" && vsMa[3] !== null && vsMa[3] > 0 ? ", including the final validation origin (the Store Item cost reversal)" : ""}.
                          </ScientificNotice>
                        </div>
                      )}
                    </>
                  );
                }}
              </DataSection>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Policy cost and service trade-off" id="policy-table-panel"
             subtitle="Base scenario per series-episode, pooled over the four validation origins (full populations). All costs are hypothetical NCU."
             actions={<Segmented label="Dataset for policy table" value={tableDataset} onChange={setTableDataset}
                                 options={DATASETS.map((k) => ({ value: k, label: DATASET_LABEL[k] }))} size="sm" />}
             footer="Lower cost can coincide with lower service: compare fill rate and stockout days, not cost alone.">
        <DataSection state={bundles[tableDataset]} loadingLabel="Loading policies">
          {([, study]) => <PolicyTable rows={study.pooled} />}
        </DataSection>
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Main findings" subtitle="Generated from the same API values shown above (validation evidence)">
          <DataSection state={combine<[[AggregateResponse, StudyResponse], [AggregateResponse, StudyResponse]]>([storeItem, m5])} rows={4}>
            {(both) => (
              <ul className="space-y-2" data-testid="findings">
                {DATASETS.flatMap((key, i) => datasetFindings(DATASET_LABEL[key], both[i][0].rows, both[i][1].perOrigin, both[i][1].pooled))
                  .map((f) => (
                    <li key={f.id} className="flex gap-2 text-sm text-ink-2">
                      <span aria-hidden="true" className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                        f.tone === "positive" ? "bg-teal" : f.tone === "caution" ? "bg-[#c98500]" : "bg-muted"}`} />
                      <span>{f.text}</span>
                    </li>
                  ))}
              </ul>
            )}
          </DataSection>
          <p className="mt-3 text-xs text-muted">Better forecast accuracy does not by itself imply lower simulated inventory cost (limitation L2).</p>
        </Panel>
        <Panel title="Limitations to keep in view" subtitle="From the Phase 5 audit response and limitations documents"
               footer={<Link className="text-brand hover:underline" href="/research#limitations">All eight limitations and the audit findings →</Link>}>
          <DataSection state={research} rows={4}>
            {(r) => (
              <ul className="space-y-2 text-sm text-ink-2" data-testid="overview-limitations">
                {r.limitations.slice(0, 5).map((l) => (
                  <li key={l.limitationId} className="flex gap-2"><Badge>{l.limitationId}</Badge><span>{l.limitation}</span></li>
                ))}
              </ul>
            )}
          </DataSection>
        </Panel>
      </div>

      <nav aria-label="Explore further" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { href: "/forecasts", title: "Forecast Explorer", text: "Saved forecasts against actual demand for any curated series." },
          { href: "/planner", title: "Inventory Planner", text: "Run the verified Phase 5 engine on your own hypothetical scenario." },
          { href: "/scenarios", title: "Scenario Comparison", text: "All 17 frozen scenarios, by origin and policy." },
          { href: "/research", title: "Research & Methodology", text: "Protocol, audit findings, limitations and provenance." },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="group rounded-lg border border-line bg-surface p-4 hover:border-brand/40">
            <p className="flex items-center justify-between font-semibold text-ink">{l.title}
              <Icon name="arrow" size={16} className="text-muted group-hover:text-brand" /></p>
            <p className="mt-1 text-sm text-ink-2">{l.text}</p>
          </Link>
        ))}
      </nav>

      <p className="text-xs text-muted">
        Source: Phase 7B curated export <code>{datasets.data?.meta.exportVersion ?? "—"}</code>, derived read-only from the hash-verified
        Phase 4–6 evidence (see Research → Reproducibility). Percentages are relative differences of the displayed values.
      </p>
    </div>
  );
}
