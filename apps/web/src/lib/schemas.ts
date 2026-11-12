import { z } from "zod";

/** Planner bounds; must equal configs/webapp.yaml planner_bounds and the engine's Pydantic model (tested). */
export const PLANNER_BOUNDS = {
  leadDays: [0, 14], reviewDays: [1, 7], bufferDays: [0, 7], initialCoverDays: [0, 14], holdingCost: [0.1, 5],
  shortageCost: [1, 50], fixedOrderCost: [0, 10], variableOrderCost: [0, 1], terminalCost: [0, 1],
  variabilityMultiplier: [0.5, 1.5],
} as const;

export const DATASETS = ["store_item", "m5"] as const;
export const POLICIES = ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"] as const;
export const MODEL_ROLES = ["selected_ml", "moving_average_28", "seasonal_naive"] as const;

export const datasetSchema = z.enum(DATASETS);
export const seriesKeySchema = z.string().regex(/^(store_item|m5)\|[A-Za-z0-9_:-]{1,40}$/, "invalid series key");
export const originKeySchema = z.string().regex(/^(store_item|m5)\|[1-4]$/, "invalid origin key");
const number = (key: keyof typeof PLANNER_BOUNDS) =>
  z.number().finite().min(PLANNER_BOUNDS[key][0]).max(PLANNER_BOUNDS[key][1]);
const integer = (key: "leadDays" | "reviewDays") => number(key).int();

export const scenarioSchema = z.strictObject({
  leadDays: integer("leadDays").default(7),
  reviewDays: integer("reviewDays").default(1),
  bufferDays: number("bufferDays").default(3),
  initialCoverDays: number("initialCoverDays").default(7),
  holdingCost: number("holdingCost").default(1),
  shortageCost: number("shortageCost").default(10),
  fixedOrderCost: number("fixedOrderCost").default(1),
  variableOrderCost: number("variableOrderCost").default(0),
  terminalCost: number("terminalCost").default(0),
  variabilityMultiplier: number("variabilityMultiplier").default(1),
}).refine((s) => s.leadDays + s.reviewDays <= 28, { message: "leadDays + reviewDays must not exceed 28" });

export const simulateSchema = z.strictObject({
  seriesKey: seriesKeySchema,
  originKey: originKeySchema,
  policies: z.array(z.enum(POLICIES)).min(1).max(4).default([...POLICIES])
    .refine((p) => new Set(p).size === p.length, { message: "policies must be distinct" }),
  scenario: scenarioSchema.default(() => scenarioSchema.parse({})),
}).refine((b) => b.seriesKey.split("|")[0] === b.originKey.split("|")[0],
          { message: "series and origin belong to different datasets", path: ["originKey"] });

export type SimulateBody = z.infer<typeof simulateSchema>;

export const seriesListSchema = z.strictObject({
  dataset: datasetSchema,
  pattern: z.string().regex(/^[a-z_]{1,40}$/).optional(),
  q: z.string().max(32).regex(/^[A-Za-z0-9_:-]*$/, "invalid search text").optional(),
  limit: z.coerce.number().int().min(1).max(50).default(25),
  cursor: z.string().max(64).regex(/^[A-Za-z0-9_:-]*$/).optional(),
});

export const forecastQuerySchema = z.strictObject({ series: seriesKeySchema, origin: originKeySchema })
  .refine((q) => q.series.split("|")[0] === q.origin.split("|")[0],
          { message: "series and origin belong to different datasets", path: ["origin"] });

export const aggregateQuerySchema = z.strictObject({
  dataset: datasetSchema,
  origin: originKeySchema.optional(),
  pattern: z.string().regex(/^[a-z_]{1,40}$/).optional(),
});

export const studyQuerySchema = z.strictObject({
  dataset: datasetSchema,
  pattern: z.enum(["smooth", "erratic", "intermittent", "lumpy", "all_zero", "insufficient_positive_history"]).optional(),
  scenario: z.string().regex(/^[a-z_]{1,40}$/).optional(),
  origin: originKeySchema.optional(),
  policy: z.enum(POLICIES).optional(),
});

export const seriesBaseQuerySchema = z.strictObject({ series: seriesKeySchema, origin: originKeySchema.optional() });

export function params(search: URLSearchParams): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of search.entries()) result[key] = value;
  return result;
}
