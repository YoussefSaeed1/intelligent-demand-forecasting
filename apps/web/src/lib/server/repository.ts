import "server-only";
import { readExact } from "./db";

/**
 * Read-only queries against schema app (webapp_api role). All parameters are bound, never interpolated. Every read
 * runs through `readExact` (READ ONLY transaction, exact float8 text), so numeric results are bit-identical to the
 * stored IEEE-754 values whatever the server's extra_float_digits.
 */

export async function provenance() {
  return readExact(async (q) => {
    const [row] = await q`select * from app.provenance order by export_version desc limit 1`;
    return row as Record<string, unknown>;
  });
}

export async function exportVersion(): Promise<string> {
  return readExact(async (q) => {
    const [row] = await q`select export_version from app.provenance order by export_version desc limit 1`;
    return row.exportVersion as string;
  });
}

export interface DatasetRow {
  datasetKey: string; dataset: string; datasetDescription: string; seriesCount: number; curatedSeries: number;
  selectedTrial: string; trainingStart: string; testStart: string;
}

export interface StudyRow {
  originKey: string; fold: number; scenarioKey: string; scenario: string; scenarioGroup: string; scenarioSort: number;
  policyKey: string; policy: string; policySort: number; seriesEpisodes: number; totalCost: number;
  holdingCost: number; shortageCost: number; orderingCost: number; terminalCost: number; demandUnits: number;
  fulfilledUnits: number; stockoutDays: number; orders: number; averageOnHandSum: number;
}

export async function datasets() {
  return readExact(async (q) => {
    const rows = await q<DatasetRow[]>`
      select dataset_key, dataset, dataset_description, series_count, curated_series, selected_trial,
             training_start::text as training_start, test_start::text as test_start
      from app.datasets order by dataset_sort`;
    const origins = await q`
      select origin_key, dataset_key, fold, fold_label, origin_date::text as origin_date,
             validation_start::text as validation_start, validation_end::text as validation_end
      from app.validation_origins order by dataset_key, fold`;
    const models = await q`
      select model_key, dataset_key, model_role, model_role_key, algorithm, is_selected_model
      from app.forecast_models order by dataset_key, model_role_sort`;
    return rows.map((d) => ({
      ...d,
      origins: origins.filter((o) => o.datasetKey === d.datasetKey),
      models: models.filter((m) => m.datasetKey === d.datasetKey),
    }));
  });
}

export async function seriesList(dataset: string, pattern: string | undefined, q: string | undefined,
                                 limit: number, cursor: string | undefined) {
  const prefix = q ? `${q.replace(/[%_\\]/g, (c) => `\\${c}`)}%` : "%";
  return readExact(async (db) => {
    const rows = await db`
      select series_key, series_id, store_id, item_id, department_id, category_id, state_id, pattern_key,
             curation_stratum, retrospective_sparse_group
      from app.series
      where dataset_key = ${dataset}
        and (${pattern ?? null}::text is null or pattern_key = ${pattern ?? null})
        and series_id like ${prefix}
        and series_id > ${cursor ?? ""}
      order by series_id
      limit ${limit + 1}`;
    const [{ total }] = await db`
      select count(*)::int as total from app.series
      where dataset_key = ${dataset} and (${pattern ?? null}::text is null or pattern_key = ${pattern ?? null})
        and series_id like ${prefix}`;
    const page = rows.slice(0, limit);
    return { items: page, total, nextCursor: rows.length > limit ? page[page.length - 1].seriesId : null };
  });
}

export async function seriesDetail(seriesKey: string) {
  return readExact(async (q) => {
    const [series] = await q`
      select s.*, p.demand_pattern, p.pattern_description
      from app.series s join app.demand_patterns p using (pattern_key)
      where s.series_key = ${seriesKey}`;
    return series ?? null;
  });
}

export async function originsFor(dataset: string) {
  return readExact(async (q) => {
    return q`
      select origin_key, fold, fold_label, origin_date::text as origin_date,
             validation_start::text as validation_start, validation_end::text as validation_end
      from app.validation_origins where dataset_key = ${dataset} order by fold`;
  });
}

export async function forecastBundle(seriesKey: string, originKey: string) {
  return readExact(async (q) => {
    const [origin] = await q`
      select origin_key, fold, fold_label, origin_date::text as origin_date,
             validation_start::text as validation_start, validation_end::text as validation_end
      from app.validation_origins where origin_key = ${originKey}`;
    const history = await q`
      select date::text as date, units from app.series_history
      where series_key = ${seriesKey} and origin_key = ${originKey} order by date`;
    const actuals = await q`
      select date::text as date, units from app.validation_actuals
      where series_key = ${seriesKey} and origin_key = ${originKey} order by date`;
    const forecasts = await q`
      select f.model_key, m.model_role_key, f.horizon_day, f.date::text as date, f.forecast
      from app.forecasts f join app.forecast_models m using (model_key)
      where f.series_key = ${seriesKey} and f.origin_key = ${originKey}
      order by m.model_role_sort, f.horizon_day`;
    const metrics = await q`
      select f.model_key, m.model_role_key, m.model_role, f.observations, f.sum_abs_error, f.sum_squared_error,
             f.sum_error, f.sum_actual, f.sum_forecast, f.scale_abs, f.scale_squared
      from app.forecast_metrics_series f join app.forecast_models m using (model_key)
      where f.series_key = ${seriesKey} and f.origin_key = ${originKey} order by m.model_role_sort`;
    return { origin: origin ?? null, history, actuals, forecasts, metrics };
  });
}

export async function aggregates(dataset: string, origin: string | undefined, pattern: string | undefined) {
  return readExact(async (q) => {
    return q`
      select a.origin_key, o.fold, a.model_key, m.model_role_key, m.model_role, a.pattern_key, a.series,
             a.observations, a.sum_abs_error, a.sum_squared_error, a.sum_error, a.sum_actual, a.sum_forecast,
             a.mase_sum, a.mase_count, a.rmsse_sum, a.rmsse_count
      from app.forecast_metrics_aggregate a
      join app.forecast_models m using (model_key)
      join app.validation_origins o using (origin_key)
      where a.dataset_key = ${dataset}
        and (${origin ?? null}::text is null or a.origin_key = ${origin ?? null})
        and a.pattern_key = ${pattern ?? "all"}
      order by o.fold, m.model_role_sort`;
  });
}

export async function inventoryStudy(dataset: string, scenario?: string, origin?: string, policy?: string, pattern?: string) {
  return readExact(async (q) => {
    return q<StudyRow[]>`
      select r.origin_key, o.fold, r.scenario_key, s.scenario, s.scenario_group, s.scenario_sort,
             r.policy_key, p.policy, p.policy_sort,
             sum(r.series_episodes)::int as series_episodes, sum(r.total_cost) as total_cost,
             sum(r.holding_cost) as holding_cost, sum(r.shortage_cost) as shortage_cost,
             sum(r.ordering_cost) as ordering_cost, sum(r.terminal_cost) as terminal_cost,
             sum(r.demand_units) as demand_units, sum(r.fulfilled_units) as fulfilled_units,
             sum(r.stockout_days) as stockout_days, sum(r.orders) as orders,
             sum(r.average_on_hand) as average_on_hand_sum
      from app.inventory_scenario_results r
      join app.validation_origins o using (origin_key)
      join app.scenarios s using (scenario_key)
      join app.inventory_policies p using (policy_key)
      where r.dataset_key = ${dataset}
        and (${scenario ?? null}::text is null or r.scenario_key = ${scenario ?? null})
        and (${origin ?? null}::text is null or r.origin_key = ${origin ?? null})
        and (${policy ?? null}::text is null or r.policy_key = ${policy ?? null})
        and (${pattern ?? null}::text is null or r.pattern_key = ${pattern ?? null})
      group by r.origin_key, o.fold, r.scenario_key, s.scenario, s.scenario_group, s.scenario_sort,
               r.policy_key, p.policy, p.policy_sort
      order by s.scenario_sort, o.fold, p.policy_sort`;
  });
}

export async function seriesBase(seriesKey: string, origin?: string) {
  return readExact(async (q) => {
    return q`
      select b.origin_key, o.fold, b.policy_key, b.total_cost, b.holding_cost, b.shortage_cost, b.ordering_cost,
             b.terminal_cost, b.demand_units, b.fulfilled_units, b.unmet_units, b.stockout_days, b.orders,
             b.average_on_hand, b.final_on_hand, b.final_pipeline, b.initial_on_hand
      from app.inventory_series_base b join app.validation_origins o using (origin_key)
      where b.series_key = ${seriesKey} and (${origin ?? null}::text is null or b.origin_key = ${origin ?? null})
      order by o.fold, b.policy_key`;
  });
}

export async function scenarios() {
  return readExact(async (q) => {
    return q`select * from app.scenarios order by scenario_sort`;
  });
}

export async function policies() {
  return readExact(async (q) => {
    return q`select policy_key, policy, policy_description, is_low_stock_comparator from app.inventory_policies order by policy_sort`;
  });
}

export async function research() {
  return readExact(async (q) => {
    const [limitations, findings, trials, finalHoldout, patterns] = await Promise.all([
      q`select * from app.limitations order by limitation_id`,
      q`select * from app.audit_findings order by finding_id`,
      q`select * from app.model_selection_trials order by dataset_key, trial_id`,
      q`select * from app.final_holdout_reported order by dataset_key, role desc, trial_id`,
      q`select * from app.demand_patterns order by pattern_sort`,
    ]);
    return { limitations, findings, trials, finalHoldout, patterns };
  });
}
