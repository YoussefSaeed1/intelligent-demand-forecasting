import type { DatasetKey, ModelRole, PolicyKey, SeriesItem } from "./api/types";

/**
 * Fixed identity encoding used by every chart, legend and table: colour follows the entity, never its rank,
 * and each series also has its own line style so colour is never the only cue.
 */
export interface SeriesStyle {
  label: string;
  short: string;
  color: string;
  dash?: string;
}

export const ACTUAL_STYLE: SeriesStyle = { label: "Actual demand (saved sales)", short: "Actual", color: "var(--color-series-actual)" };
export const HISTORY_STYLE: SeriesStyle = { label: "Pre-origin history", short: "History", color: "var(--color-muted)" };

export const MODEL_STYLE: Record<ModelRole, SeriesStyle> = {
  selected_ml: { label: "Selected ML", short: "Selected ML", color: "var(--color-series-ml)" },
  moving_average_28: { label: "MA28 baseline", short: "MA28", color: "var(--color-series-ma28)", dash: "7 4" },
  seasonal_naive: { label: "Seasonal Naive baseline", short: "Seasonal Naive", color: "var(--color-series-snaive)", dash: "2 3" },
};

export const POLICY_STYLE: Record<PolicyKey, SeriesStyle & { description: string }> = {
  selected_ml: { ...MODEL_STYLE.selected_ml, label: "Selected ML order-up-to",
                 description: "Order-up-to policy driven by the frozen selected ML validation forecast." },
  moving_average_28: { ...MODEL_STYLE.moving_average_28, label: "MA28 order-up-to",
                       description: "Order-up-to policy driven by the 28-day moving-average forecast." },
  seasonal_naive: { ...MODEL_STYLE.seasonal_naive, label: "Seasonal Naive order-up-to",
                    description: "Order-up-to policy driven by the weekly seasonal naive forecast." },
  fixed_reorder_point: { label: "Fixed reorder point", short: "Fixed ROP", color: "var(--color-series-rop)", dash: "10 3 2 3",
                         description: "A low-stock comparator with lower fill rate: fixed (s, Q) from the 56-day history mean; not a tuned policy." },
};

export const POLICY_ORDER: PolicyKey[] = ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"];
export const MODEL_ORDER: ModelRole[] = ["selected_ml", "moving_average_28", "seasonal_naive"];

export const DATASET_LABEL: Record<DatasetKey, string> = { store_item: "Store Item", m5: "M5" };

export const ALGORITHM_LABEL: Record<string, string> = {
  lightgbm: "LightGBM",
  random_forest: "Random Forest (price-free)",
  moving_average_28: "28-day moving average",
  seasonal_naive: "Seasonal naive (weekly)",
};

/** Same keys and labels as `app.demand_patterns` (checked against /api/v1/research in tests). */
export const PATTERNS: { key: string; label: string }[] = [
  { key: "smooth", label: "Smooth" },
  { key: "erratic", label: "Erratic" },
  { key: "intermittent", label: "Intermittent" },
  { key: "lumpy", label: "Lumpy" },
  { key: "all_zero", label: "All zero" },
  { key: "insufficient_positive_history", label: "Insufficient history" },
];

export function patternLabel(key: string | null | undefined): string {
  return PATTERNS.find((p) => p.key === key)?.label ?? key ?? "Unknown";
}

/** Readable name of a curated series; the raw series ID stays visible as secondary text. */
export function seriesLabel(item: Pick<SeriesItem, "seriesId" | "storeId" | "itemId">, dataset: DatasetKey): string {
  if (item.storeId && item.itemId) {
    return dataset === "store_item" ? `Store ${item.storeId} · Item ${item.itemId}` : `${item.itemId} · ${item.storeId}`;
  }
  return item.seriesId;
}

export function datasetOf(key: string | null | undefined): DatasetKey | null {
  const prefix = key?.split("|")[0];
  return prefix === "store_item" || prefix === "m5" ? prefix : null;
}

export const COVERAGE_LABEL: Record<DatasetKey, string> = {
  store_item: "All 500 research series",
  m5: "Exploratory demo: 300 predeclared curated series of 30,490",
};
