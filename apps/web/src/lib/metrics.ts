/**
 * Forecast-accuracy ratios from additive components (the Phase 6 definitions). Undefined values are null,
 * never zero: WAPE with zero actual demand and MASE/RMSSE with a zero training scale are undefined.
 */
export interface Components {
  observations: number;
  sumAbsError: number;
  sumSquaredError: number;
  sumError: number;
  sumActual: number;
  scaleAbs?: number | null;
  scaleSquared?: number | null;
}

const ratio = (numerator: number, denominator: number) => (denominator > 0 ? numerator / denominator : null);

export function seriesMetrics(c: Components) {
  const mae = ratio(c.sumAbsError, c.observations);
  const mse = ratio(c.sumSquaredError, c.observations);
  return {
    mae,
    rmse: mse === null ? null : Math.sqrt(mse),
    wape: ratio(c.sumAbsError, c.sumActual),
    bias: ratio(c.sumError, c.observations),
    mase: mae === null || !c.scaleAbs ? null : mae / c.scaleAbs,
    rmsse: mse === null || !c.scaleSquared ? null : Math.sqrt(mse / c.scaleSquared),
  };
}

export interface AggregateComponents extends Components {
  series: number;
  maseSum: number;
  maseCount: number;
  rmsseSum: number;
  rmsseCount: number;
}

/** Pooled MAE/RMSE/WAPE/bias plus macro MASE/RMSSE (mean of defined per-series values). */
export function aggregateMetrics(c: AggregateComponents) {
  const pooled = seriesMetrics(c);
  return {
    ...pooled,
    macroMase: ratio(c.maseSum, c.maseCount),
    macroRmsse: ratio(c.rmsseSum, c.rmsseCount),
    series: c.series,
    undefinedMaseSeries: c.series - c.maseCount,
  };
}
