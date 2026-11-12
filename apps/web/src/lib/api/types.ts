/**
 * Response contracts of the Phase 7B `/api/v1` routes, written from the route handlers and checked against
 * live local responses. The browser only ever sees these shapes; no database or engine type leaks here.
 */
import type { DATASETS, MODEL_ROLES, POLICIES } from "../schemas";

export type DatasetKey = (typeof DATASETS)[number];
export type ModelRole = (typeof MODEL_ROLES)[number];
export type PolicyKey = (typeof POLICIES)[number];
export type Evidence = "validation" | "reported_final_holdout";

export interface Meta {
  exportVersion: string;
  evidence?: Evidence;
  scope?: string;
  note?: string;
  ncuNotice?: string;
  scenarioNote?: string;
}

export interface Origin {
  originKey: string;
  datasetKey?: string;
  fold: number;
  foldLabel: string;
  originDate: string;
  validationStart: string;
  validationEnd: string;
}

export interface ForecastModel {
  modelKey: string;
  datasetKey: string;
  modelRole: string;
  modelRoleKey: ModelRole;
  algorithm: string;
  isSelectedModel: "Yes" | "No";
}

export interface Dataset {
  datasetKey: DatasetKey;
  dataset: string;
  datasetDescription: string;
  seriesCount: number;
  curatedSeries: number;
  selectedTrial: string;
  trainingStart: string;
  testStart: string;
  origins: Origin[];
  models: ForecastModel[];
  coverageNote: string;
}

export interface DatasetsResponse {
  meta: Meta;
  datasets: Dataset[];
}

export interface SeriesItem {
  seriesKey: string;
  seriesId: string;
  storeId: string | null;
  itemId: string | null;
  departmentId: string | null;
  categoryId: string | null;
  stateId: string | null;
  patternKey: string;
  curationStratum: string;
  retrospectiveSparseGroup: string;
}

export interface SeriesListResponse {
  meta: Meta;
  items: SeriesItem[];
  total: number;
  nextCursor: string | null;
}

export interface SeriesDetail extends SeriesItem {
  datasetKey: DatasetKey;
  trainingPrefixUnits: number;
  trainingPrefixMeanUnits: number;
  demandPattern: string;
  patternDescription: string;
}

export interface SeriesDetailResponse {
  meta: Meta;
  series: SeriesDetail;
  origins: Origin[];
}

export interface SeriesMetrics {
  mae: number | null;
  rmse: number | null;
  wape: number | null;
  bias: number | null;
  mase: number | null;
  rmsse: number | null;
}

export interface DatedUnits {
  date: string;
  units: number;
}

export interface ForecastPoint {
  date: string;
  horizonDay: number;
  value: number;
}

export interface ForecastModelBundle {
  modelKey: string;
  role: ModelRole;
  label: string;
  forecast: ForecastPoint[];
  metrics: SeriesMetrics;
}

export interface ForecastsResponse {
  meta: Meta;
  series: { seriesKey: string; seriesId: string; pattern: string; datasetKey: DatasetKey };
  origin: Origin;
  history: DatedUnits[];
  actuals: DatedUnits[];
  models: ForecastModelBundle[];
}

export interface AggregateMetrics extends SeriesMetrics {
  macroMase: number | null;
  macroRmsse: number | null;
  series: number;
  undefinedMaseSeries: number;
}

export interface AggregateRow {
  originKey: string;
  fold: number;
  modelKey: string;
  role: ModelRole;
  label: string;
  pattern: string;
  metrics: AggregateMetrics;
}

export interface AggregateResponse {
  meta: Meta;
  rows: AggregateRow[];
}

export interface StudyMeasures {
  seriesEpisodes: number;
  meanCostNcu: number | null;
  holdingCostNcu: number | null;
  unmetPenaltyNcu: number | null;
  orderingCostNcu: number | null;
  terminalCostNcu: number | null;
  fillRate: number | null;
  stockoutDaysPerEpisode: number | null;
  averageOnHand: number | null;
  ordersPerEpisode: number | null;
  costPerDemandedUnitNcu: number | null;
}

export interface StudyPolicy {
  policyKey: PolicyKey;
  policy: string;
  policyDescription: string;
  isLowStockComparator: "Yes" | "No";
}

export interface StudyPerOriginRow extends StudyMeasures {
  originKey: string;
  fold: number;
  scenarioKey: string;
  scenario: string;
  scenarioGroup: string;
  policyKey: PolicyKey;
  policy: string;
}

export interface StudyPooledRow extends StudyMeasures {
  scenarioKey: string;
  scenario: string;
  scenarioGroup: string;
  policyKey: PolicyKey;
  policy: string;
  origins: number;
}

export interface StudyResponse {
  meta: Meta;
  policies: StudyPolicy[];
  perOrigin: StudyPerOriginRow[];
  pooled: StudyPooledRow[];
}

export interface SeriesBaseRow {
  originKey: string;
  fold: number;
  policyKey: PolicyKey;
  totalCost: number;
  holdingCost: number;
  shortageCost: number;
  orderingCost: number;
  terminalCost: number;
  demandUnits: number;
  fulfilledUnits: number;
  unmetUnits: number;
  stockoutDays: number;
  orders: number;
  averageOnHand: number;
  finalOnHand: number;
  finalPipeline: number;
  initialOnHand: number;
}

export interface SeriesBaseResponse {
  meta: Meta & { scenario: "base" };
  rows: SeriesBaseRow[];
}

export interface ScenarioInput {
  leadDays: number;
  reviewDays: number;
  bufferDays: number;
  initialCoverDays: number;
  holdingCost: number;
  shortageCost: number;
  fixedOrderCost: number;
  variableOrderCost: number;
  terminalCost: number;
  variabilityMultiplier: number;
}

export interface SimulateRequest {
  seriesKey: string;
  originKey: string;
  policies: PolicyKey[];
  scenario: ScenarioInput;
}

/** Engine summary fields (camelCased by the Next.js server; values are hypothetical NCU or units). */
export interface PolicySummary {
  demandUnits: number;
  fulfilledUnits: number;
  unmetUnits: number;
  receivedUnits: number;
  placedUnits: number;
  holdingCost: number;
  shortageCost: number;
  orderingCost: number;
  terminalCost: number;
  totalCost: number;
  stockoutDays: number;
  orders: number;
  initialOnHand: number;
  initialPipeline: number;
  finalOnHand: number;
  finalPipeline: number;
  fillRate: number | null;
  stockoutDayRate: number | null;
  averageOnHand: number | null;
  averageInventoryPosition: number | null;
  averageOrderQuantity: number | null;
  orderFrequency: number | null;
  windowTurnover: number | null;
}

export interface DailyEvent {
  date: string;
  openingStock: number;
  receipts: number;
  demand: number;
  fulfilled: number;
  unmet: number;
  closingStock: number;
  pipelineAfter: number;
  inventoryPosition: number;
  orderQuantity: number;
  holdingCost: number;
  shortageCost: number;
  orderingCost: number;
  reviewAllowed: boolean;
}

export interface SimulatePolicy {
  policyKey: PolicyKey;
  summary: PolicySummary;
  daily: DailyEvent[];
}

export interface SimulateResponse {
  meta: Meta & { engineVersion: string; requestId: string };
  inputs: {
    seriesKey: string;
    originKey: string;
    policies: PolicyKey[];
    scenario: ScenarioInput;
    historicalMean56: number;
    dates: string[];
    demand: number[];
    demandSource: string;
  };
  policies: SimulatePolicy[];
  comparison: {
    baseline: "moving_average_28";
    deltas: { policyKey: PolicyKey; totalCostNcu: number; fillRatePoints: number | null }[];
  } | null;
  studyReference: {
    scenarioMatched: string;
    note: string;
    phase5TotalCostNcu: Partial<Record<PolicyKey, number>>;
  } | null;
}

export interface Limitation {
  limitationId: string;
  limitation: string;
  sourceDocument: string;
}

export interface AuditFinding {
  findingId: string;
  severity: string;
  finding: string;
  disposition: string;
  status: string;
}

export interface DemandPattern {
  patternKey: string;
  demandPattern: string;
  patternSort: number;
  patternDescription: string;
}

export interface SelectionTrial {
  trialId: string;
  datasetKey: DatasetKey;
  trialKind: string;
  algorithm: string;
  validationMacroMae: number;
  validationMacroMase: number;
  validationMacroRmsse: number;
  validationPooledRmse: number;
  validationPooledWapePercent: number;
  validationBiasUnits: number;
  observations: number;
  fallbackObservations: number;
  isSelected: "Yes" | "No";
}

export interface FinalHoldoutRow {
  datasetKey: DatasetKey;
  trialId: string;
  algorithm: string;
  role: "selected" | "comparator";
  evidenceType: string;
  macroMae: number;
  macroMase: number;
  macroRmsse: number;
  pooledRmse: number;
  pooledWapePercent: number;
  series: number;
  observations: number;
}

export interface Provenance {
  exportVersion: string;
  gitCommit: string;
  planSha256: string;
  executionSha256: string;
  selectionFingerprint: string;
  ledgerSha256: string;
  phase6ManifestSha256: string;
  finalHoldoutTargetsRead: boolean;
  curatedM5Sha256: string;
  [key: string]: unknown;
}

export interface ResearchResponse {
  meta: Meta;
  provenance: Provenance;
  limitations: Limitation[];
  auditFindings: AuditFinding[];
  demandPatterns: DemandPattern[];
  modelSelectionTrials: { evidence: "validation"; rows: SelectionTrial[] };
  finalHoldout: { evidence: "reported_final_holdout"; note: string; rows: FinalHoldoutRow[] };
}

export interface HealthResponse {
  status: "ok" | "degraded";
  exportVersion: string;
  engine: { reachable: boolean; engineVersion?: string };
  build: string;
}

export interface ApiErrorBody {
  error: string;
  message: string;
  fields?: { field: string; message: string }[];
  requestId?: string;
}
