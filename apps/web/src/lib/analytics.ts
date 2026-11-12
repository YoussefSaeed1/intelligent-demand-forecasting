/**
 * Presentation helpers over API responses. Nothing here re-implements forecasting or inventory mathematics:
 * every input value is computed server-side from saved evidence. The only derived quantities are
 *  - the equal-origin mean of per-origin MAE (the Phase 4 primary score; tests reproduce the saved leaderboard
 *    values from /api/v1/research), and
 *  - relative differences between two displayed values.
 */
import type { AggregateRow, ModelRole, PolicyKey, StudyPerOriginRow, StudyPooledRow } from "./api/types";
import { relativeChange } from "./format";

export function perOriginMae(rows: AggregateRow[], role: ModelRole): { fold: number; mae: number | null }[] {
  return rows.filter((r) => r.role === role).sort((a, b) => a.fold - b.fold).map((r) => ({ fold: r.fold, mae: r.metrics.mae }));
}

/** Equal-origin mean of per-origin MAE; null unless all four origins are defined. */
export function originMeanMae(rows: AggregateRow[], role: ModelRole): number | null {
  const values = perOriginMae(rows, role).map((r) => r.mae);
  if (values.length !== 4 || values.some((v) => v === null)) return null;
  return (values as number[]).reduce((a, b) => a + b, 0) / values.length;
}

export function pooledRow(rows: StudyPooledRow[], scenario: string, policy: PolicyKey): StudyPooledRow | undefined {
  return rows.find((r) => r.scenarioKey === scenario && r.policyKey === policy);
}

export function originRow(rows: StudyPerOriginRow[], scenario: string, policy: PolicyKey, fold: number) {
  return rows.find((r) => r.scenarioKey === scenario && r.policyKey === policy && r.fold === fold);
}

/** Selected ML mean hypothetical cost relative to a baseline policy, per origin (fold 1-4). */
export function costRelativeByOrigin(rows: StudyPerOriginRow[], scenario: string, baseline: PolicyKey): (number | null)[] {
  return [1, 2, 3, 4].map((fold) => relativeChange(originRow(rows, scenario, "selected_ml", fold)?.meanCostNcu,
                                                   originRow(rows, scenario, baseline, fold)?.meanCostNcu));
}

export interface Finding {
  id: string;
  tone: "positive" | "neutral" | "caution";
  text: string;
}

/**
 * Data-driven statements for one dataset. Each sentence is chosen by comparing API values, so the copy cannot
 * claim an advantage the evidence does not show.
 */
export function datasetFindings(name: string, aggregates: AggregateRow[], perOrigin: StudyPerOriginRow[],
                                pooled: StudyPooledRow[]): Finding[] {
  const findings: Finding[] = [];
  const ml = perOriginMae(aggregates, "selected_ml");
  for (const baseline of ["moving_average_28", "seasonal_naive"] as const) {
    const other = perOriginMae(aggregates, baseline);
    const wins = ml.filter((r, i) => r.mae !== null && other[i]?.mae !== null && r.mae < (other[i].mae as number)).length;
    const label = baseline === "moving_average_28" ? "MA28" : "Seasonal Naive";
    findings.push({
      id: `${name}-mae-${baseline}`,
      tone: wins === 4 ? "positive" : wins === 0 ? "caution" : "neutral",
      text: `${name}: selected ML has a lower validation MAE than ${label} at ${wins} of 4 origins.`,
    });
  }
  for (const baseline of ["moving_average_28", "seasonal_naive"] as const) {
    const rel = costRelativeByOrigin(perOrigin, "base", baseline);
    const lower = rel.filter((v) => v !== null && v < 0).length;
    const label = baseline === "moving_average_28" ? "MA28" : "Seasonal Naive";
    const pooledRel = relativeChange(pooledRow(pooled, "base", "selected_ml")?.meanCostNcu,
                                     pooledRow(pooled, "base", baseline)?.meanCostNcu);
    findings.push({
      id: `${name}-cost-${baseline}`,
      tone: lower === 4 ? "positive" : "caution",
      text: `${name} (base scenario): selected ML's mean hypothetical cost is ${pooledRel === null ? "undefined"
        : pooledRel < 0 ? "lower" : "higher"} than ${label} when pooled over origins, and lower at ${lower} of 4 origins.`,
    });
  }
  return findings;
}
