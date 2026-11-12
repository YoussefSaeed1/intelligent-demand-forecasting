import type { Metadata } from "next";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge, Panel } from "@/components/ui/Panel";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import {
  AuditFindings, DatasetsAndOrigins, FinalHoldoutReported, Limitations, Provenance, ScenarioCatalogue, SelectionTrials,
} from "@/features/research/ResearchData";

export const metadata: Metadata = { title: "Research & Methodology" };

/*
 * Every statement on this page is taken from the project documentation (README, PHASE4_FINAL_EVALUATION,
 * PHASE4_OPTIMISATION_PROTOCOL, BASELINE_MODELS, METRIC_DEFINITIONS, PHASE5_ASSUMPTIONS,
 * INVENTORY_POLICY_MATHEMATICS, PHASE5 limitations/audit response, PHASE7B_BACKEND_RESULTS). Tables are
 * read live from /api/v1. No external citations are added.
 */

const SECTIONS: [string, string][] = [
  ["problem", "Research problem"],
  ["evidence", "Types of evidence"],
  ["datasets", "Datasets"],
  ["forecasting", "Forecasting approach"],
  ["validation", "Validation protocol"],
  ["holdout", "Final holdout"],
  ["inventory", "Inventory simulation"],
  ["findings", "Main findings"],
  ["audit", "Independent audit"],
  ["limitations", "Limitations"],
  ["threats", "Threats to validity"],
  ["reproducibility", "Reproducibility"],
  ["future", "Future work"],
];

function Section({ id, title, children, subtitle }: { id: string; title: string; subtitle?: string; children: ReactNode }) {
  return (
    <Panel id={id} title={title} subtitle={subtitle} className="scroll-mt-20">
      <div className="space-y-3 text-[15px] leading-relaxed text-ink-2">{children}</div>
    </Panel>
  );
}

function Formula({ children }: { children: ReactNode }) {
  return <code className="block overflow-x-auto rounded-md bg-subtle px-3 py-2 font-mono text-[13px] text-ink">{children}</code>;
}

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Methodology and evidence" title="Research & Methodology"
                  description="How the evidence in this application was produced, what it can and cannot show, and how to reproduce it."
                  badges={<><Badge tone="teal">Validation evidence</Badge><Badge>Reported final holdout</Badge><Badge tone="caution">Hypothetical NCU</Badge></>} />
      <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav aria-label="On this page" className="lg:sticky lg:top-6 lg:self-start">
          <ol className="flex flex-wrap gap-2 text-sm lg:flex-col lg:gap-0.5">
            {SECTIONS.map(([id, label]) => (
              <li key={id}><a href={`#${id}`} className="block rounded px-2 py-1 text-ink-2 hover:bg-surface hover:text-brand">{label}</a></li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0 space-y-5">
          <Section id="problem" title="Research problem">
            <p>Retail planning must balance uncertain future sales against stock availability and inventory cost. The project compares
              reproducible daily forecasting approaches on two published datasets and investigates their implications under explicitly
              assumed inventory scenarios.</p>
            <p>The forecasting task is daily point forecasting 28 days ahead (H28). The central question is whether compact global
              machine-learning and statistical candidates improve over simple baselines when each forecast may use only information
              available at its origin. Observed sales may be constrained by availability; they are not necessarily latent demand.</p>
          </Section>

          <Section id="evidence" title="Types of evidence in this application">
            <div className="grid gap-3 md:grid-cols-2">
              <ScientificNotice kind="validation" title="Verified scientific evidence">
                Forecast accuracy at the four validation origins and the frozen Phase 5 scenario study, reconciled against the saved
                registry, leaderboard and audit values in automated quality gates.
              </ScientificNotice>
              <ScientificNotice kind="reported" title="Reported final-holdout result">
                The one-time Phase 4 final assessment, displayed exactly as recorded. It is never recomputed by the application.
              </ScientificNotice>
              <ScientificNotice kind="caution" title="Exploratory scenario analysis">
                The 17 frozen scenarios vary one assumption at a time. They reuse the same origins, series and forecasts, so they show
                sensitivity, not independent replications.
              </ScientificNotice>
              <ScientificNotice kind="hypothetical" title="Hypothetical simulation output">
                Planner runs with your own parameters execute the unchanged Phase 5 engine on saved validation sales. Results are in
                normalised cost units (NCU) under stated assumptions; they are not realised savings or forecasts of real outcomes.
              </ScientificNotice>
            </div>
          </Section>

          <Section id="datasets" title="Datasets" subtitle="Kaggle Store Item Demand Forecasting Challenge and M5 Forecasting Accuracy">
            <p>Store Item supplies 500 daily store-product series (913,000 historical rows, 2013–2017); M5 supplies 30,490 Walmart
              store-item series (59,181,090 historical rows, 2011–2016) with highly intermittent demand. They are separate benchmarks;
              direct transfer of models between them is not established.</p>
            <DatasetsAndOrigins />
            <p className="text-sm">The web demo includes every Store Item series and a predeclared, pattern-stratified sample of 300 M5
              series (seed 42; all-zero 10, insufficient history 5, erratic 40, intermittent 150, lumpy 60, smooth 35; the six Phase 5
              representatives force-included). All population statistics use the full 30,490 series.</p>
          </Section>

          <Section id="forecasting" title="Forecasting approach">
            <p>Two simple baselines are always reported next to the selected model:</p>
            <ul className="list-disc space-y-1 pl-5">
              <li><strong className="text-ink">MA28</strong>: repeats the arithmetic mean of the last 28 observed daily quantities.</li>
              <li><strong className="text-ink">Seasonal Naive</strong>: repeats the last seven observed daily quantities four times.</li>
            </ul>
            <p>Phase 4 evaluated 23 tuning configurations (a seed-42 finite random search over explicit discrete spaces, with initial
              anchors) and four unchanged references, each refitted at all four origins. Candidates included LightGBM, Random Forest,
              additive Holt-Winters (Store Item) and TSB (M5). Every Phase 4 ML candidate is price-free because M5 price publication latency
              could not be verified. The primary selection score is the equal-origin mean of equal-series MAE.</p>
            <SelectionTrials />
            <p className="text-sm">Selected: LightGBM for Store Item and a price-free Random Forest for M5. Baselines were not tuned, so the
              selected models&apos; validation advantage is an optimistic estimate after selection (limitation L6).</p>
          </Section>

          <Section id="validation" title="Validation protocol">
            <p>Four expanding validation origins per dataset, each followed by a 28-day window; the final 28 days of each dataset form a
              sealed holdout. Forecasts are fixed at the origin and are not refreshed daily within the window. Accuracy uses pooled MAE,
              RMSE, WAPE and bias, plus macro MASE and RMSSE scaled by the training-period weekly difference.</p>
            <Formula>WAPE = Σ|forecast − actual| / Σ|actual|  ·  bias = mean(forecast − actual)  ·  MASE = MAE / q_abs</Formula>
            <p className="text-sm">Undefined values (WAPE with zero actual demand; MASE or RMSSE with a zero training scale) are reported as
              undefined, never as zero.</p>
          </Section>

          <Section id="holdout" title="Final holdout (reported, sealed)">
            <p>The model selection was frozen in a manifest (fingerprint <code className="break-all text-xs">a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb</code>)
              before any final target was scored; the final window was then assessed once. This application shows those saved results only
              as reported values and has no access to the final-holdout targets.</p>
            <FinalHoldoutReported />
          </Section>

          <Section id="inventory" title="Inventory simulation assumptions" subtitle="Phase 5; configs/inventory.yaml was frozen before any simulation result">
            <p>The datasets contain no observed stock, orders, lead times, costs or service targets, so every inventory quantity is a
              stated assumption. The simulation is a discrete periodic end-of-day review with lost sales (no backorders), unlimited
              deterministic supply, integer orders rounded up, and a common initial stock for all policies.</p>
            <p>Let μ be the trailing 56-day training mean, L the lead time, R the review interval, P = L + R, buffer B = b·μ and inventory
              position IP = closing stock + pipeline. Orders placed on day t arrive on day t + L + 1.</p>
            <Formula>Forecast policies (order-up-to): S = Σ forecast(t+1 … t+P) + B;  order = ceil(max(0, S − IP))</Formula>
            <Formula>Fixed reorder point (comparator): s = μ·P + B, Q = ceil(μ·R); order Q when IP ≤ s</Formula>
            <p>Costs are normalised hypothetical cost units: holding h per unit of closing stock per day, shortage p per unmet unit, k per
              positive order, v per ordered unit and a terminal charge e on remaining stock and pipeline. Base: lead time 7, review 1,
              buffer 3 days, initial cover 7 days, h = 1, p = 10, k = 1, v = 0, e = 0. The fill rate is fulfilled ÷ demanded units; the
              stockout-day rate is not a cycle service level.</p>
            <p className="text-sm font-medium text-ink">The 17 frozen scenarios (one change at a time from the base):</p>
            <ScenarioCatalogue />
          </Section>

          <Section id="findings" title="Main findings">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Store Item: the selected LightGBM has a clearly lower validation MAE than both baselines at every origin, and the lowest
                MAE among the predeclared comparators in the reported final assessment.</li>
              <li>M5: the price-free Random Forest&apos;s advantage over MA28 is small (validation MAE 1.0201 versus 1.0338), and MA28 is
                better on the all-zero-label sparse group (limitation L7).</li>
              <li>Forecast accuracy and simulated inventory cost do not move together: on M5 the selected ML policy has a slightly higher
                mean hypothetical cost than MA28 in the base scenario, with a higher fill rate; on Store Item the cost advantage over MA28
                reverses at the final validation origin (L2, L3).</li>
              <li>The fixed reorder point reaches the lowest cost only by holding little stock and accepting a lower fill rate (L5).</li>
            </ul>
            <p className="text-sm">The Overview page states these comparisons with the exact values from the curated tables.</p>
          </Section>

          <Section id="audit" title="Independent scientific audit" subtitle="Phases 0-5: verdict conditional; 0 critical and 0 high findings">
            <AuditFindings />
          </Section>

          <Section id="limitations" title="Known limitations">
            <Limitations />
          </Section>

          <Section id="threats" title="Threats to validity">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Observed sales may be censored by availability and are a proxy for demand.</li>
              <li>SNAP, events and future prices are excluded; M5 Phase 4 models are price-free.</li>
              <li>Four validation windows and one final 28-day window cover limited seasonal regimes.</li>
              <li>ML training used seeded equal series- and time-stratified samples (150,000 Store Item and 182,940 M5 labels per origin), not
                full-history supervised training.</li>
              <li>Origin spread is descriptive variability, not a confidence interval; correlated series and only four origins do not
                establish statistical significance.</li>
              <li>Inventory results depend on assumed costs, lead times and policies; finite 28-day episodes create end-of-window artefacts.</li>
            </ul>
          </Section>

          <Section id="reproducibility" title="Reproducibility and provenance">
            <p>The curated tables are a read-only, deterministic export of hash-verified Phase 4–6 evidence (re-export is byte-identical).
              The simulation engine is a byte-identical copy of the Phase 5 engine, verified against the frozen execution contract; its
              parity test replays 3,264 Phase 5 episodes (816 at each of four origins) with bit-exact results.</p>
            <Provenance />
            <Formula>python -m intelligent_demand.bi.webapp_export   ·   python -m intelligent_demand.bi.webapp_qa</Formula>
            <p className="text-sm">Repository link: to be added when the project is published.</p>
          </Section>

          <Section id="future" title="Future work (not implemented)">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Saved planner scenarios and run history (requires accounts), and shareable run links.</li>
              <li>A tuned (s, S) inventory comparator, which would need a new, separately validated experiment (audit finding F-03).</li>
              <li>An off-device copy of the scientific evidence (audit finding F-02, an owner action before academic submission).</li>
            </ul>
          </Section>
        </div>
      </div>
    </>
  );
}
