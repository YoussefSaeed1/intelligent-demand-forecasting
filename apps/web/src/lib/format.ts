/**
 * Presentation-only formatting (Phase 7A UI spec section 3). Undefined values render as an em dash with an
 * explanation elsewhere; they are never shown as zero.
 */
export const DASH = "—";

const cache = new Map<string, Intl.NumberFormat>();
function nf(min: number, max: number, extra: Intl.NumberFormatOptions = {}) {
  const key = `${min}|${max}|${JSON.stringify(extra)}`;
  let format = cache.get(key);
  if (!format) {
    format = new Intl.NumberFormat("en-GB", { minimumFractionDigits: min, maximumFractionDigits: max, ...extra });
    cache.set(key, format);
  }
  return format;
}

const defined = (value: number | null | undefined): value is number =>
  value !== null && value !== undefined && Number.isFinite(value);

export function num(value: number | null | undefined, digits = 2): string {
  return defined(value) ? nf(digits, digits).format(value) : DASH;
}

export function int(value: number | null | undefined): string {
  return defined(value) ? nf(0, 0).format(Math.round(value)) : DASH;
}

/** Forecast errors in demand units (MAE, RMSE, bias): 4 decimals as in the dashboard. */
export function units4(value: number | null | undefined): string {
  return num(value, 4);
}

/** Ratio in [0, 1] shown as a percentage with 2 decimals (WAPE, fill rate). */
export function pct(value: number | null | undefined, digits = 2): string {
  return defined(value) ? `${nf(digits, digits).format(value * 100)}%` : DASH;
}

/** Hypothetical normalised cost units. The NCU suffix is part of every rendered cost. */
export function ncu(value: number | null | undefined, digits = 2): string {
  return defined(value) ? `${nf(digits, digits).format(value)} NCU` : DASH;
}

export function signed(value: number | null | undefined, digits = 2, suffix = ""): string {
  if (!defined(value)) return DASH;
  const text = nf(digits, digits).format(Math.abs(value));
  const sign = value > 0 ? "+" : value < 0 ? "−" : "±";
  return `${sign}${text}${suffix}`;
}

/** Relative difference of two displayed values, e.g. ML versus MA28 mean cost; null when undefined. */
export function relativeChange(value: number | null | undefined, reference: number | null | undefined): number | null {
  if (!defined(value) || !defined(reference) || reference === 0) return null;
  return (value - reference) / Math.abs(reference);
}

export function signedPct(value: number | null | undefined, digits = 1): string {
  return defined(value) ? signed(value * 100, digits, "%") : DASH;
}

export function compact(value: number): string {
  if (Math.abs(value) >= 10_000) return nf(0, 1, { notation: "compact" }).format(value);
  return nf(0, Math.abs(value) < 10 && !Number.isInteger(value) ? 1 : 0).format(value);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** ISO date (YYYY-MM-DD) to "14 Aug 2017" without timezone conversion. */
export function date(iso: string | null | undefined, withYear = true): string {
  if (!iso) return DASH;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return withYear ? `${d} ${MONTHS[m - 1]} ${y}` : `${d} ${MONTHS[m - 1]}`;
}

export function shortHash(value: unknown, length = 12): string {
  return typeof value === "string" ? value.slice(0, length) : DASH;
}
