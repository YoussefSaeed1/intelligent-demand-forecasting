"use client";

import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Panel";
import { apiPath } from "@/lib/api/client";
import type { AuditFinding, DatasetsResponse, FinalHoldoutRow, ResearchResponse, SelectionTrial, StudyResponse } from "@/lib/api/types";
import { useApi } from "@/lib/api/useApi";
import { date, int, num, units4 } from "@/lib/format";
import { ALGORITHM_LABEL, DATASET_LABEL } from "@/lib/labels";
import { DataSection } from "../common/DataSection";

const useResearch = () => useApi<ResearchResponse>(apiPath("/research"));
const algorithm = (a: string) => ALGORITHM_LABEL[a] ?? a.replace(/_/g, " ");

export function DatasetsAndOrigins() {
  const state = useApi<DatasetsResponse>(apiPath("/datasets"));
  return (
    <DataSection state={state} loadingLabel="Loading datasets">
      {(d) => (
        <div className="space-y-4">
          <DataTable caption="Datasets" rows={d.datasets} rowKey={(r) => r.datasetKey} testId="research-datasets"
                     columns={[
                       { key: "name", header: "Dataset", rowHeader: true, cell: (r) => r.dataset },
                       { key: "series", header: "Research series", align: "right", cell: (r) => int(r.seriesCount) },
                       { key: "demo", header: "In this demo", align: "right", cell: (r) => int(r.curatedSeries) },
                       { key: "train", header: "History from", cell: (r) => date(r.trainingStart) },
                       { key: "test", header: "Final holdout from", cell: (r) => date(r.testStart) },
                     ]} />
          <DataTable caption="Validation origins" dense rowKey={(r) => r.originKey} testId="research-origins"
                     rows={d.datasets.flatMap((x) => x.origins.map((o) => ({ ...o, dataset: x.dataset })))}
                     columns={[
                       { key: "dataset", header: "Dataset", rowHeader: true, cell: (r) => r.dataset },
                       { key: "fold", header: "Origin", cell: (r) => r.foldLabel },
                       { key: "origin", header: "Forecast made at end of", cell: (r) => date(r.originDate) },
                       { key: "window", header: "Validation window (28 days)", cell: (r) => `${date(r.validationStart)} – ${date(r.validationEnd)}` },
                     ]} />
        </div>
      )}
    </DataSection>
  );
}

export function SelectionTrials() {
  const state = useResearch();
  return (
    <DataSection state={state} loadingLabel="Loading trials">
      {(r) => (
        <div className="grid min-w-0 grid-cols-1 gap-5">
          {(["store_item", "m5"] as const).map((ds) => {
            const rows = r.modelSelectionTrials.rows.filter((t) => t.datasetKey === ds)
              .sort((a, b) => a.validationMacroMae - b.validationMacroMae);
            return (
              <div key={ds}>
                <p className="mb-1.5 text-sm font-semibold text-ink">{DATASET_LABEL[ds]} · {rows.length} candidates</p>
                <DataTable<SelectionTrial> caption={`${DATASET_LABEL[ds]} model-selection leaderboard (validation)`} rows={rows} dense
                           rowKey={(t) => t.trialId} highlight={(t) => t.isSelected === "Yes"} testId={`trials-${ds}`}
                           columns={[
                             { key: "trial", header: "Trial", rowHeader: true, cell: (t) => (
                               <span className="flex flex-wrap items-center gap-1.5"><code className="text-xs">{t.trialId}</code>
                                 {t.isSelected === "Yes" && <Badge tone="brand">Selected</Badge>}
                                 {t.trialKind === "reference" && <Badge>Reference</Badge>}</span>) },
                             { key: "alg", header: "Algorithm", cell: (t) => algorithm(t.algorithm) },
                             { key: "mae", header: "Validation MAE", align: "right", cell: (t) => units4(t.validationMacroMae) },
                             { key: "mase", header: "MASE", align: "right", cell: (t) => num(t.validationMacroMase, 3) },
                             { key: "rmsse", header: "RMSSE", align: "right", cell: (t) => num(t.validationMacroRmsse, 3) },
                             { key: "wape", header: "WAPE", align: "right", cell: (t) => `${num(t.validationPooledWapePercent, 2)}%` },
                           ]} />
              </div>
            );
          })}
        </div>
      )}
    </DataSection>
  );
}

export function FinalHoldoutReported() {
  const state = useResearch();
  return (
    <DataSection state={state} loadingLabel="Loading reported results">
      {(r) => (
        <>
          <p className="mb-2 text-sm text-ink-2">{r.finalHoldout.note}</p>
          <DataTable<FinalHoldoutRow> caption="Reported Phase 4 final-holdout results" rows={r.finalHoldout.rows} dense testId="final-holdout"
                     rowKey={(t) => t.trialId} highlight={(t) => t.role === "selected"}
                     columns={[
                       { key: "ds", header: "Dataset", rowHeader: true, cell: (t) => DATASET_LABEL[t.datasetKey] },
                       { key: "alg", header: "Model", cell: (t) => <>{algorithm(t.algorithm)} {t.role === "selected" && <Badge tone="brand">Selected</Badge>}</> },
                       { key: "mae", header: "MAE", align: "right", cell: (t) => units4(t.macroMae) },
                       { key: "mase", header: "MASE", align: "right", cell: (t) => num(t.macroMase, 3) },
                       { key: "rmsse", header: "RMSSE", align: "right", cell: (t) => num(t.macroRmsse, 3) },
                       { key: "wape", header: "WAPE", align: "right", cell: (t) => `${num(t.pooledWapePercent, 2)}%` },
                       { key: "n", header: "Series", align: "right", cell: (t) => int(t.series) },
                     ]} />
        </>
      )}
    </DataSection>
  );
}

export function ScenarioCatalogue() {
  const state = useApi<StudyResponse>(apiPath("/inventory/study", { dataset: "store_item" }));
  return (
    <DataSection state={state} loadingLabel="Loading scenarios">
      {(s) => {
        const groups = new Map<string, string[]>();
        for (const r of s.pooled) {
          if (r.policyKey !== "selected_ml") continue;
          groups.set(r.scenarioGroup, [...(groups.get(r.scenarioGroup) ?? []), r.scenario]);
        }
        return (
          <ul className="grid gap-x-6 gap-y-1 text-sm text-ink-2 sm:grid-cols-2" data-testid="scenario-catalogue">
            {[...groups].map(([group, names]) => (
              <li key={group}><span className="font-medium text-ink">{group}:</span> {names.join(", ")}</li>
            ))}
          </ul>
        );
      }}
    </DataSection>
  );
}

const SEVERITY_TONE: Record<string, "danger" | "caution" | "neutral" | "brand"> = { High: "danger", Medium: "caution", Low: "neutral", Info: "brand" };

export function AuditFindings() {
  const state = useResearch();
  return (
    <DataSection state={state} loadingLabel="Loading audit findings">
      {(r) => (
        <DataTable<AuditFinding> caption="Independent audit findings (Phases 0-5)" rows={r.auditFindings} rowKey={(f) => f.findingId} testId="audit-findings"
                   columns={[
                     { key: "id", header: "ID", rowHeader: true, cell: (f) => f.findingId },
                     { key: "sev", header: "Severity", cell: (f) => <Badge tone={SEVERITY_TONE[f.severity] ?? "neutral"}>{f.severity}</Badge> },
                     { key: "finding", header: "Finding", className: "min-w-48", cell: (f) => <span className="font-medium text-ink">{f.finding}</span> },
                     { key: "disp", header: "Disposition", className: "min-w-64", cell: (f) => f.disposition },
                     { key: "status", header: "Status", className: "min-w-40", cell: (f) => f.status },
                   ]} />
      )}
    </DataSection>
  );
}

export function Limitations() {
  const state = useResearch();
  return (
    <DataSection state={state} loadingLabel="Loading limitations">
      {(r) => (
        <ol className="space-y-2" data-testid="limitations">
          {r.limitations.map((l) => (
            <li key={l.limitationId} className="flex gap-3 rounded-md border border-line bg-surface px-3 py-2.5 text-sm">
              <Badge tone="caution">{l.limitationId}</Badge>
              <span className="text-ink-2">{l.limitation} <span className="text-xs text-muted">Source: <code>{l.sourceDocument}</code></span></span>
            </li>
          ))}
        </ol>
      )}
    </DataSection>
  );
}

const PROVENANCE_LABELS: [string, string][] = [
  ["exportVersion", "Curated export version"],
  ["gitCommit", "Source commit of the export"],
  ["planSha256", "Phase 5 plan SHA-256"],
  ["executionSha256", "Phase 5 execution contract SHA-256"],
  ["selectionFingerprint", "Frozen model-selection fingerprint"],
  ["ledgerSha256", "Holdout access ledger SHA-256"],
  ["phase6ManifestSha256", "Phase 6 reporting manifest SHA-256"],
  ["curatedM5Sha256", "Curated M5 series list SHA-256"],
];

export function Provenance() {
  const state = useResearch();
  return (
    <DataSection state={state} loadingLabel="Loading provenance">
      {(r) => (
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_minmax(0,1fr)]" data-testid="provenance">
          {PROVENANCE_LABELS.map(([key, label]) => (
            <div key={key} className="contents">
              <dt className="text-muted">{label}</dt>
              <dd className="min-w-0 break-all font-mono text-xs text-ink">{String(r.provenance[key] ?? "—")}</dd>
            </div>
          ))}
          <dt className="text-muted">Final-holdout targets read by the export</dt>
          <dd className="font-medium text-ink">{r.provenance.finalHoldoutTargetsRead ? "Yes" : "No"}</dd>
        </dl>
      )}
    </DataSection>
  );
}
