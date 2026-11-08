# Post-audit feature and sparse-sampling qualification

The frozen final feature schemas are independently retained in
`reports/post_audit/selected_feature_availability.json`. The actual selected Store
Item LightGBM has 27 features; the selected M5 RF has 30. Neither contains price,
SNAP or event columns. The original frozen configurations and model objects are
unchanged. No new availability assumption or feature entered remediation.

| Information | Availability and policy |
|---|---|
| Store/product/hierarchy IDs | Static published-universe metadata; target-free mappings |
| Lags and rolling level/standard deviation | Strictly historical at label time; after origin use only own clipped recursive predictions |
| Observed zero/positive frequency, ADI/CV² and age | Historical; frozen at the true origin for the recursive horizon |
| Calendar/date terms | Deterministic known future dates |
| Historical prices in Phase 3 | Conditional research evidence: completed-week lag does not prove publication latency |
| Historical/future prices in Phase 4 | Excluded, including price-missing indicators |
| SNAP/events | Advance availability unverified; excluded from selected models |
| Future target observations | Unknown future; prohibited; synthetic poisoning invariance tested |

Historical price-enabled Phase 3 comparisons remain labelled conditional; the
price-free final M5 model does not establish that old publication assumption.
Current synthetic tests and original schema evidence do not prove a hostile Python
program cannot read a filesystem; the origin capability is an application boundary.

## Descriptive M5 fixed-sample evidence

`reports/post_audit/sampling_diagnostics.json` uses the existing labels/manifests and
validation scores. It does not read final outcomes, modify labels or fit models.
All 30,490 series, ten stores, 3,049 products, seven departments, three states and
six initial demand classes retain sample membership. Final training contains
182,940 labels, six per series: 123,972 zero and 58,968 positive labels.

6,878 series (22.56%) have no positive sampled label; 6,864 have positive initial
historical sales. All ten stores and seven departments have positive sampled
labels, but nine products have none across their ten stores. All five series in
the fixed insufficient-positive-history class have no positive sampled label.
The class labels are initial-prefix labels; they are not recomputed from final data.

| Validation origin | All-six-zero sampled series | RF minus MA28 MAE in that subgroup |
|---|---:|---:|
| 2016-01-03 | 7,225 | +0.011545 |
| 2016-01-31 | 7,179 | +0.014844 |
| 2016-02-28 | 7,166 | +0.012203 |
| 2016-03-27 | 6,976 | +0.013072 |

MA28 has lower subgroup MAE in each origin, while RF has lower mean MAE in the
sampled-positive subgroup and overall. This is a descriptive association, not proof
that the sparse sample caused the difference. It reinforces that global average
improvement is not universal superiority for intermittent series. The recorded
overall rankings and final results are unchanged.

Final training positions remain seed 42 and indices 56–1912, ending 2016-04-24;
there are six time strata per series. Reproducibility, membership and temporal
span do not establish full positive-outcome or recency representation. Future
research may prospectively study larger, recency-aware or weighted sampling, but
must predeclare the design and obtain untouched assessment data. No replacement
strategy was implemented or selected using final holdout outcomes.
