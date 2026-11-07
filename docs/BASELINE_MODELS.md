# Phase 3B baseline methods

Authorised execution uses the unchanged four expanding origins per dataset and a
28-day daily horizon. No final test targets are exposed. These fixed initial rules
are not a hyperparameter search.

| Identifier | Rule for all 28 steps |
|---|---|
| naive | Repeat the last observed sales quantity |
| seasonal_naive | Repeat the last seven observed daily quantities four times |
| moving_average_28 | Repeat the arithmetic mean of the last 28 observed quantities |
| seasonal_moving_average | Average each weekday's four observations in the last 28 days and repeat that seven-day pattern four times |
| zero | Predict zero for every series/day |

The implementations vectorise independent per-series calculations inside a global
adapter to avoid tens of thousands of redundant Parquet scans. This does not pool
series or estimate shared baseline parameters. Recorded zeros are preserved. Predictions
are finite, nonnegative and unrounded.

Minimum histories are 1, 7, 28, 28 and 1 respectively. Insufficient history falls back
to weekly seasonal naive with at least seven observations, otherwise naive. The
delivery artifact records requested and actual methods, fallback flag and reason for
every series. Missing observations are a quality failure, not invented history.

## Execution and evidence

```powershell
.\.venv\Scripts\python.exe -m intelligent_demand.experiments.benchmark run --phase 3b
.\.venv\Scripts\python.exe -m intelligent_demand.evaluation.benchmark_audit --phase 3b
```

Full evaluation comprises 500 Store Item and 30,490 M5 series at each of four origins.
Each complete model therefore delivers 56,000 and 3,414,880 predictions respectively.
Model comparisons use the mean of the four macro per-series MAEs, separately by source.
Pooled/macro secondary metrics, horizon and fixed initial-training demand classes are
reported with undefined-denominator and fallback coverage. Store/product and available
hierarchy breakdowns are derived from independently reconciled predictions.

Origin-only float32 caches reject any sales quantity that would lose precision. They
are hash-bound, checked for complete unique keys, and never contain post-origin targets.
Weekly scales are computed in float64 and tested against the original streaming
implementation. Future and final-test poison mutations cannot affect baseline outputs.

The sequential supervisor caps workers at 2 GiB RSS, four threads and 900 seconds per
baseline origin/model run; a new worker needs at least 512 MiB available system memory.
Only one real experiment runs at a time. Completed runs are checksum-verified for reuse.
Every run has an immutable specification, attempt status, predictions, metrics,
delivery details and resource log under ignored artifacts.

The comparison gate now requires identical evaluation-module hashes rather than
identical hashes for every model implementation in the package. Different families
necessarily have different model code; full code provenance is still retained per run.
Dataset, origin, population, classes, seed, protocol and settings must still match.
Regression tests reject metric-code changes while allowing model-only code differences.

Final executed results and the mandatory quality gate are recorded in
`reports/forecasting/phase3b_gate.json` when the complete independent audit passes.
The earlier Phase 3A integrity report remains historical evidence of its checkpoint.
