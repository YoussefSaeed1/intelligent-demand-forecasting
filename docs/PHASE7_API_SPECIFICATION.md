# Phase 7A: API specification

> **Amended by Phase 7B (2026-11-12):** the implementation refines this design (no browser database access, dedicated least-privilege roles instead of the service-role key, Postgres-backed rate limiting, `/api/v1` routes, measured 137 MB footprint). See [PHASE7B_BACKEND_RESULTS.md](PHASE7B_BACKEND_RESULTS.md) section 3.

Two surfaces: Next.js route handlers (public, TypeScript, zod-validated) and the FastAPI engine service
(private, reached only from Next.js with a shared secret). JSON everywhere, camelCase fields, ISO dates.
Every response carries `meta.exportVersion` and `meta.evidence` (`"validation"` or `"reported_final_holdout"`).

## 1. Next.js route handlers (`apps/web/app/api/*`)

| Method and path | Purpose | Query / body (bounds) | Cache |
|---|---|---|---|
| `GET /api/health` | Build SHA, export version, engine reachability | | no |
| `GET /api/datasets` | Datasets with counts, selected trial, origins | | 1 day |
| `GET /api/series` | Curated series list | `dataset` (required), `pattern?`, `q?` (max 32 chars, prefix match), `limit` ≤ 50, `cursor?` | 1 day |
| `GET /api/series/{seriesKey}` | Series metadata and its four origins | | 1 day |
| `GET /api/forecasts` | History, actuals and the three forecasts for one series and origin, plus per-model metrics | `series` (required), `origin` (required) | immutable, 1 day |
| `GET /api/metrics/aggregate` | Full-population accuracy by origin, model, pattern | `dataset` (required), `origin?`, `pattern?` | 1 day |
| `GET /api/inventory/study` | 544-case scenario study (pattern grain) | `dataset` (required), `scenario?`, `origin?`, `policy?` | 1 day |
| `GET /api/inventory/series-base` | Phase 5 base results for one curated series | `series`, `origin?` | 1 day |
| `POST /api/planner/simulate` | Run the bounded simulation (proxies to the engine) | body below | no |
| `GET /api/export/planner.csv` | CSV of a run the client posts back (bounded, no storage) | signed payload ≤ 64 kB | no |
| `GET /api/research` | Limitations, audit findings, provenance, trials, reported final-holdout rows | | 1 day |

Rate limits: `POST /api/planner/simulate` 30 requests per minute per IP and 300 per day per IP (token bucket in
the handler; Vercel WAF rule as a second layer if available on Hobby, not verified). Read endpoints 120 per
minute per IP. Exceeding returns `429` with `Retry-After`.

### `POST /api/planner/simulate`

```json
{
  "seriesKey": "store_item|1:11",
  "originKey": "store_item|1",
  "policies": ["selected_ml", "moving_average_28", "seasonal_naive", "fixed_reorder_point"],
  "scenario": {
    "leadDays": 7, "reviewDays": 1, "bufferDays": 3, "initialCoverDays": 7,
    "holdingCost": 1, "shortageCost": 10, "fixedOrderCost": 1, "variableOrderCost": 0,
    "terminalCost": 0, "variabilityMultiplier": 1
  }
}
```

Bounds (zod and Pydantic; the engine's `Scenario` validation is the final check):

| Field | Type | Range | Default (Phase 5 base) |
|---|---|---|---|
| leadDays | integer | 0 to 14 | 7 |
| reviewDays | integer | 1 to 7 | 1 |
| leadDays + reviewDays | | ≤ 28 (engine protection rule) | |
| bufferDays | number | 0 to 7, step 0.5 | 3 |
| initialCoverDays | number | 0 to 14, step 0.5 | 7 |
| holdingCost | number | 0.1 to 5 | 1 |
| shortageCost | number | 1 to 50 | 10 |
| fixedOrderCost | number | 0 to 10 | 1 |
| variableOrderCost | number | 0 to 1 | 0 |
| terminalCost | number | 0 to 1 | 0 |
| variabilityMultiplier | number | 0.5 to 1.5 | 1 |
| policies | 1 to 4 distinct keys | | all four |

Response (`200`):

```json
{
  "meta": {"exportVersion": "2026-11-xx.1", "engineVersion": "<inventory_core hash>", "evidence": "validation",
           "ncuNotice": "Hypothetical normalised cost units; not realised savings."},
  "inputs": {"...echo of validated inputs...", "historicalMean56": 23.71, "dates": ["2017-08-14", "..."]},
  "policies": [
    {"policyKey": "selected_ml",
     "summary": {"totalCostNcu": 2555, "holdingCostNcu": 2254, "shortageCostNcu": 280, "orderingCostNcu": 21,
                 "fillRate": 0.9872, "stockoutDays": 1, "averageOnHand": 80.5, "orders": 20, "finalOnHand": 61, "finalPipeline": 0},
     "daily": [{"date": "2017-08-14", "opening": 166, "receipts": 0, "demand": 21, "fulfilled": 21, "unmet": 0,
                "closing": 145, "pipelineAfter": 0, "order": 26, "position": 171}, "..."]},
    "..."
  ],
  "comparison": {"baseline": "moving_average_28", "deltas": [{"policyKey": "selected_ml", "totalCostNcu": -217, "fillRatePoints": 0.0}]},
  "studyReference": {"scenarioMatched": "base", "phase5TotalCostNcu": {"selected_ml": 2555, "...": 0}}
}
```

`studyReference` is filled only when the submitted scenario equals one of the 17 frozen scenarios exactly;
otherwise it is `null` and the UI says the run is a user hypothetical outside the published study.

Errors: `400` validation (field-level messages), `404` unknown series or origin, `413` payload, `429` rate,
`502` engine unavailable, `500` generic. No stack traces or paths in any response.

## 2. FastAPI engine service (`apps/engine`)

| Method and path | Purpose |
|---|---|
| `GET /health` | engine package hash, Python version, database reachability |
| `POST /simulate` | Same body as above plus the Next.js request id; requires header `X-Engine-Key` equal to a server-only secret |

Execution: validate with Pydantic; construct `Scenario(**params)`; load `validation_actuals`, `forecasts` and
`series_origin_mean56` for the series and origin from Supabase (read-only role); build `ForecastWindow`;
call `engine.simulate` once per policy with `event_rows=[0]`; convert to JSON. One series per request, no
batch endpoint in MVP. Measured locally: about 0.4 s per four-policy request, under 5 MB peak, cold import
about 1.1 s. Timeout 20 s.

Information-availability guarantee: the request never carries demand or forecasts; the service reads them
from immutable tables; `order_quantity` sees only position, history mean, the fixed-origin forecast window and
the decision date (unchanged Phase 5 interface).

## 3. Security constraints

- Secrets: `SUPABASE_SERVICE_ROLE_KEY`, `ENGINE_SHARED_KEY`, `ENGINE_URL` in Vercel encrypted env (Production and Preview separately); `NEXT_PUBLIC_SUPABASE_URL` and the anon key are the only public values.
- Supabase queries use the client library with parameters only; no string-built SQL.
- Request bodies limited to 8 kB; CSV export limited to one run (≤ 4 policies x 28 rows).
- CORS: same origin only for the Next.js API; the engine accepts only requests with the shared key.
- Logging: request id, route, duration, status; never request bodies containing user names or emails (post-MVP auth).
- Abuse: rate limits above, bounded query sizes, pagination cursors, `limit` caps, `q` length cap.

## 4. Versioning

`/api/v1/*` prefix from the first deployment; response `meta.exportVersion` and `meta.engineVersion` let the
UI and tests detect drift between curated data, engine package and expectations.

## Phase 7C additive contract amendment (2026-11-12)
`GET /api/v1/inventory/study` also accepts optional `pattern`: smooth, erratic,
intermittent, lumpy, all_zero, insufficient_positive_history. Omit for all patterns.
Unknown patterns return 400. The filter is applied to saved PatternKey rows before
existing per-origin sums and pooled ratios; response shape and default results are unchanged.
An absent population returns empty arrays. No fabricated zero episodes or averaged fill-rate ratios.
The SQL predicate is parameterised, query values are enum-validated, and existing rate limits,
read-only database permissions, fixed query size and validation-only provenance remain in place.
