import { originKeySchema, seriesKeySchema } from "./schemas";
import type { DatasetKey, ModelRole } from "./api/types";
import { datasetOf, MODEL_ORDER, PATTERNS } from "./labels";

/** Default series per dataset: the Phase 5 representatives (present in the curated sets by construction). */
export const DEFAULT_SERIES: Record<DatasetKey, string> = {
  store_item: "store_item|1:11",
  m5: "m5|4:CA_1FOODS_1_001",
};

export interface Selection {
  dataset: DatasetKey;
  series: string | null;
  origin: string;
  pattern: string | null;
  models: ModelRole[];
  /** True when a URL value was dropped because it was malformed or belonged to another dataset. */
  corrected: boolean;
}

/**
 * Resolves URL parameters into a consistent selection. Incompatible combinations (an M5 series with a Store
 * Item origin, malformed keys, unknown patterns) are corrected rather than sent to the API.
 */
export function resolveSelection(params: { get(name: string): string | null }, fallbackSeries = true): Selection {
  let corrected = false;
  const rawSeries = params.get("series");
  const rawDataset = params.get("dataset");
  const seriesOk = rawSeries !== null && seriesKeySchema.safeParse(rawSeries).success;
  if (rawSeries !== null && !seriesOk) corrected = true;

  let dataset: DatasetKey = rawDataset === "m5" || rawDataset === "store_item" ? rawDataset
    : (seriesOk ? datasetOf(rawSeries) : null) ?? "store_item";
  if (rawDataset !== null && rawDataset !== dataset) corrected = true;

  let series = seriesOk ? rawSeries : null;
  if (series && datasetOf(series) !== dataset) {
    if (rawDataset === null) dataset = datasetOf(series) ?? dataset;
    else {
      series = null;
      corrected = true;
    }
  }
  if (!series && fallbackSeries) series = DEFAULT_SERIES[dataset];

  const rawOrigin = params.get("origin");
  let origin = `${dataset}|4`;
  if (rawOrigin !== null) {
    if (originKeySchema.safeParse(rawOrigin).success && datasetOf(rawOrigin) === dataset) origin = rawOrigin;
    else corrected = true;
  }

  const rawPattern = params.get("pattern");
  const pattern = rawPattern && PATTERNS.some((p) => p.key === rawPattern) ? rawPattern : null;
  if (rawPattern && !pattern) corrected = true;

  const rawModels = params.get("models");
  let models = [...MODEL_ORDER];
  if (rawModels !== null) {
    const picked = MODEL_ORDER.filter((m) => rawModels.split(",").includes(m));
    if (picked.length > 0) models = picked;
    else corrected = true;
  }
  return { dataset, series, origin, pattern, models, corrected };
}
