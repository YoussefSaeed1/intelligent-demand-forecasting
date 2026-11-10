# Phase 6 DAX measure catalogue

69 measures in the `_Measures` table, generated from `configs/powerbi_model.yaml`.
Pooled metrics use additive numerators and denominators; ratios are never averaged. Macro MASE/RMSSE
follow the Phase 4 definition (mean over origins of the per-origin series mean, undefined scales
excluded). Scope guards return BLANK when datasets, model roles, scenarios or policies would be mixed.
All inventory values are hypothetical normalised cost units (NCU), never savings.

## _Guards

### Forecast Scope Valid

TRUE when exactly one dataset and one model role are in context for forecast metrics.

Folder `_Guards`; format `text`; hidden

```dax
DISTINCTCOUNT ( FactForecastSeriesOrigin[DatasetKey] ) = 1
    && DISTINCTCOUNT ( FactForecastSeriesOrigin[ModelKey] ) = 1
```

### Inventory Scope Valid

TRUE when exactly one dataset, one scenario and one policy are in context for inventory metrics.

Folder `_Guards`; format `text`; hidden

```dax
DISTINCTCOUNT ( FactInventoryScenarioResults[DatasetKey] ) = 1
    && DISTINCTCOUNT ( FactInventoryScenarioResults[ScenarioKey] ) = 1
    && DISTINCTCOUNT ( FactInventoryScenarioResults[PolicyKey] ) = 1
```

## Forecast Accuracy

### Forecast Observations

Daily forecast observations in context (28 per series and origin).

Folder `Forecast Accuracy\Coverage`; format `#,##0`

```dax
SUM ( FactForecastSeriesOrigin[Observations] )
```

### MAE

Pooled mean absolute error, sum of |forecast - actual| / observations. Validation origins only. Equals the Phase 4 four-origin macro MAE because every series has 28 observations per origin.

Folder `Forecast Accuracy`; format `#,##0.0000`

```dax
IF ( [Forecast Scope Valid],
    DIVIDE ( SUM ( FactForecastSeriesOrigin[SumAbsError] ), [Forecast Observations] ) )
```

### RMSE

Pooled root mean squared error, sqrt(sum of squared errors / observations).

Folder `Forecast Accuracy`; format `#,##0.0000`

```dax
IF ( [Forecast Scope Valid],
    SQRT ( DIVIDE ( SUM ( FactForecastSeriesOrigin[SumSquaredError] ), [Forecast Observations] ) ) )
```

### WAPE

Pooled weighted absolute percentage error, sum |error| / sum actual. Blank when actual demand is zero.

Folder `Forecast Accuracy`; format `0.00%`

```dax
IF ( [Forecast Scope Valid],
    DIVIDE ( SUM ( FactForecastSeriesOrigin[SumAbsError] ), SUM ( FactForecastSeriesOrigin[SumActual] ) ) )
```

### Bias

Mean forecast minus actual per observation (positive means over-forecasting).

Folder `Forecast Accuracy`; format `#,##0.0000`

```dax
IF ( [Forecast Scope Valid],
    DIVIDE ( SUM ( FactForecastSeriesOrigin[SumError] ), [Forecast Observations] ) )
```

### Bias %

Sum of forecast minus actual divided by sum of actual demand.

Folder `Forecast Accuracy`; format `0.00%`

```dax
IF ( [Forecast Scope Valid],
    DIVIDE ( SUM ( FactForecastSeriesOrigin[SumError] ), SUM ( FactForecastSeriesOrigin[SumActual] ) ) )
```

### Macro MASE

Mean over origins of the per-origin mean series MASE (series MAE / lag-7 training scale). Series with an undefined (zero) scale are excluded, matching the Phase 4 definition.

Folder `Forecast Accuracy`; format `0.0000`

```dax
IF ( [Forecast Scope Valid],
    AVERAGEX (
        VALUES ( FactForecastSeriesOrigin[OriginKey] ),
        CALCULATE (
            AVERAGEX (
                FILTER ( FactForecastSeriesOrigin, NOT ISBLANK ( FactForecastSeriesOrigin[ScaleAbs] ) ),
                DIVIDE ( FactForecastSeriesOrigin[SumAbsError], FactForecastSeriesOrigin[Observations] )
                    / FactForecastSeriesOrigin[ScaleAbs]
            )
        )
    )
)
```

### Macro RMSSE

Mean over origins of the per-origin mean series RMSSE (sqrt(series MSE / squared lag-7 training scale)). Undefined scales excluded.

Folder `Forecast Accuracy`; format `0.0000`

```dax
IF ( [Forecast Scope Valid],
    AVERAGEX (
        VALUES ( FactForecastSeriesOrigin[OriginKey] ),
        CALCULATE (
            AVERAGEX (
                FILTER ( FactForecastSeriesOrigin, NOT ISBLANK ( FactForecastSeriesOrigin[ScaleSquared] ) ),
                SQRT (
                    DIVIDE ( FactForecastSeriesOrigin[SumSquaredError], FactForecastSeriesOrigin[Observations] )
                        / FactForecastSeriesOrigin[ScaleSquared]
                )
            )
        )
    )
)
```

### Evaluated Series

Distinct series with validation evaluation rows in context.

Folder `Forecast Accuracy\Coverage`; format `#,##0`

```dax
DISTINCTCOUNT ( FactForecastSeriesOrigin[SeriesKey] )
```

### Evaluation Coverage

Evaluated series as a share of the dataset series population in context.

Folder `Forecast Accuracy\Coverage`; format `0.0%`

```dax
DIVIDE ( [Evaluated Series], SUM ( DimDataset[SeriesCount] ) )
```

### Validation Origins Evaluated

Distinct validation origins with evaluation rows in context.

Folder `Forecast Accuracy\Coverage`; format `0`

```dax
DISTINCTCOUNT ( FactForecastSeriesOrigin[OriginKey] )
```

### MAE Selected ML

MAE of the frozen selected ML model, ignoring any model-role filter.

Folder `Forecast Accuracy\Comparisons`; format `#,##0.0000`

```dax
CALCULATE ( [MAE], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "selected_ml" )
```

### MAE MA28

MAE of the 28-day moving-average baseline, ignoring any model-role filter.

Folder `Forecast Accuracy\Comparisons`; format `#,##0.0000`

```dax
CALCULATE ( [MAE], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "moving_average_28" )
```

### MAE Seasonal Naive

MAE of the seasonal-naive baseline, ignoring any model-role filter.

Folder `Forecast Accuracy\Comparisons`; format `#,##0.0000`

```dax
CALCULATE ( [MAE], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "seasonal_naive" )
```

### ML vs MA28 MAE Change %

Relative MAE change of selected ML versus MA28 (negative means lower error).

Folder `Forecast Accuracy\Comparisons`; format `+0.00%;-0.00%;0.00%`

```dax
DIVIDE ( [MAE Selected ML] - [MAE MA28], [MAE MA28] )
```

### ML vs Seasonal Naive MAE Change %

Relative MAE change of selected ML versus Seasonal Naive (negative means lower error).

Folder `Forecast Accuracy\Comparisons`; format `+0.00%;-0.00%;0.00%`

```dax
DIVIDE ( [MAE Selected ML] - [MAE Seasonal Naive], [MAE Seasonal Naive] )
```

### Macro MASE Selected ML

Macro MASE of the selected ML model.

Folder `Forecast Accuracy\Comparisons`; format `0.0000`

```dax
CALCULATE ( [Macro MASE], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "selected_ml" )
```

### Macro MASE MA28

Macro MASE of MA28. On M5, MA28 has the better macro MASE despite the RF's lower MAE.

Folder `Forecast Accuracy\Comparisons`; format `0.0000`

```dax
CALCULATE ( [Macro MASE], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "moving_average_28" )
```

### Actual Units

Realised validation sales (a censored-demand proxy). Read from the selected-ML rows because actuals are identical for every model role.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
IF ( DISTINCTCOUNT ( FactForecastDaily[DatasetKey] ) = 1,
    CALCULATE ( SUM ( FactForecastDaily[SumActual] ), REMOVEFILTERS ( DimForecastModel ),
        DimForecastModel[ModelRoleKey] = "selected_ml" ) )
```

### Forecast Units

Saved fixed-origin forecast units for the model role in context (not daily refreshed).

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
IF ( DISTINCTCOUNT ( FactForecastDaily[DatasetKey] ) = 1
        && DISTINCTCOUNT ( FactForecastDaily[ModelKey] ) = 1,
    SUM ( FactForecastDaily[SumForecast] ) )
```

### Forecast Units Selected ML

Saved fixed-origin forecast units of the selected ML model.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "selected_ml" )
```

### Forecast Units MA28

Saved fixed-origin forecast units of MA28.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "moving_average_28" )
```

### Forecast Units Seasonal Naive

Saved fixed-origin forecast units of Seasonal Naive.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "seasonal_naive" )
```

### Daily MAE

MAE per series-day on the daily fact for one model role.

Folder `Forecast Accuracy\Daily`; format `#,##0.0000`

```dax
IF ( DISTINCTCOUNT ( FactForecastDaily[DatasetKey] ) = 1
        && DISTINCTCOUNT ( FactForecastDaily[ModelKey] ) = 1,
    DIVIDE ( SUM ( FactForecastDaily[SumAbsError] ), SUM ( FactForecastDaily[Series] ) ) )
```

### Series Actual Units

Daily realised sales for detail series (all Store Item; six M5 representatives).

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( SUM ( FactForecastSeriesDaily[Actual] ), REMOVEFILTERS ( DimForecastModel ),
    DimForecastModel[ModelRoleKey] = "selected_ml" )
```

### Series Forecast Units

Daily saved forecast for detail series and the model role in context.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
IF ( DISTINCTCOUNT ( FactForecastSeriesDaily[ModelKey] ) = 1, SUM ( FactForecastSeriesDaily[Forecast] ) )
```

### Series Forecast Selected ML

Daily saved forecast of the selected ML model for detail series.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Series Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "selected_ml" )
```

### Series Forecast MA28

Daily saved MA28 forecast for detail series.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Series Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "moving_average_28" )
```

### Series Forecast Seasonal Naive

Daily saved Seasonal Naive forecast for detail series.

Folder `Forecast Accuracy\Daily`; format `#,##0.0`

```dax
CALCULATE ( [Series Forecast Units], REMOVEFILTERS ( DimForecastModel ), DimForecastModel[ModelRoleKey] = "seasonal_naive" )
```

## Inventory

### Series Episodes

Series x 28-day episodes in context.

Folder `Inventory\Coverage`; format `#,##0`

```dax
SUM ( FactInventoryScenarioResults[SeriesEpisodes] )
```

### Total Simulated Cost (NCU)

Sum of hypothetical normalised cost units. Not a realised financial amount.

Folder `Inventory\Cost`; format `#,##0`

```dax
IF ( [Inventory Scope Valid], SUM ( FactInventoryScenarioResults[TotalCost] ) )
```

### Mean Cost per Episode (NCU)

Total simulated cost / series-episodes. The Phase 5 headline unit. Hypothetical, not savings.

Folder `Inventory\Cost`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[TotalCost] ), [Series Episodes] ) )
```

### Holding Cost per Episode (NCU)

Holding cost on closing stock per series-episode.

Folder `Inventory\Cost`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[HoldingCost] ), [Series Episodes] ) )
```

### Ordering Cost per Episode (NCU)

Fixed plus variable ordering cost per series-episode.

Folder `Inventory\Cost`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[OrderingCost] ), [Series Episodes] ) )
```

### Unmet Demand Penalty per Episode (NCU)

Shortage penalty on lost (unmet) units per series-episode.

Folder `Inventory\Cost`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[ShortageCost] ), [Series Episodes] ) )
```

### Terminal Cost per Episode (NCU)

Terminal exposure charge on closing stock plus pipeline; zero except in the terminal-charge scenario.

Folder `Inventory\Cost`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[TerminalCost] ), [Series Episodes] ) )
```

### Cost per Demanded Unit (NCU)

Total simulated cost divided by demanded units; a scale-normalised view.

Folder `Inventory\Cost`; format `#,##0.0000`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[TotalCost] ), SUM ( FactInventoryScenarioResults[DemandUnits] ) ) )
```

### Fill Rate

Pooled unit fill rate, fulfilled units / demanded units (not an average of series rates).

Folder `Inventory\Service`; format `0.00%`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[FulfilledUnits] ), SUM ( FactInventoryScenarioResults[DemandUnits] ) ) )
```

### Stockout Days per Episode

Days with unmet demand per 28-day series-episode.

Folder `Inventory\Service`; format `0.000`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[StockoutDays] ), [Series Episodes] ) )
```

### Average On-Hand Units

Mean over series-episodes of average daily closing stock.

Folder `Inventory\Stock`; format `#,##0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[AverageOnHandSum] ), [Series Episodes] ) )
```

### Orders per Episode

Positive orders per series-episode.

Folder `Inventory\Stock`; format `0.00`

```dax
IF ( [Inventory Scope Valid], DIVIDE ( SUM ( FactInventoryScenarioResults[Orders] ), [Series Episodes] ) )
```

### Order Frequency

Share of the 28 episode days on which an order is placed.

Folder `Inventory\Stock`; format `0.0%`

```dax
DIVIDE ( [Orders per Episode], 28 )
```

### Mean Cost Selected ML (NCU)

Mean cost per episode under the selected-ML order-up-to policy.

Folder `Inventory\Comparisons`; format `#,##0.00`

```dax
CALCULATE ( [Mean Cost per Episode (NCU)], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "selected_ml" )
```

### Mean Cost MA28 (NCU)

Mean cost per episode under the MA28 order-up-to policy.

Folder `Inventory\Comparisons`; format `#,##0.00`

```dax
CALCULATE ( [Mean Cost per Episode (NCU)], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "moving_average_28" )
```

### Mean Cost Seasonal Naive (NCU)

Mean cost per episode under the Seasonal Naive order-up-to policy.

Folder `Inventory\Comparisons`; format `#,##0.00`

```dax
CALCULATE ( [Mean Cost per Episode (NCU)], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "seasonal_naive" )
```

### Mean Cost Fixed ROP (NCU)

Mean cost per episode under the fixed reorder point, a low-stock and lower-service comparator.

Folder `Inventory\Comparisons`; format `#,##0.00`

```dax
CALCULATE ( [Mean Cost per Episode (NCU)], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "fixed_reorder_point" )
```

### ML vs MA28 Cost Difference (NCU)

Selected ML minus MA28 mean cost per episode. Negative is a lower hypothetical simulated cost, not a realised saving.

Folder `Inventory\Comparisons`; format `+#,##0.00;-#,##0.00;0.00`

```dax
[Mean Cost Selected ML (NCU)] - [Mean Cost MA28 (NCU)]
```

### ML vs MA28 Cost Difference %

Selected ML minus MA28 mean cost as a share of MA28 mean cost (hypothetical NCU).

Folder `Inventory\Comparisons`; format `+0.00%;-0.00%;0.00%`

```dax
DIVIDE ( [ML vs MA28 Cost Difference (NCU)], [Mean Cost MA28 (NCU)] )
```

### ML vs Seasonal Naive Cost Difference (NCU)

Selected ML minus Seasonal Naive mean cost per episode (hypothetical NCU).

Folder `Inventory\Comparisons`; format `+#,##0.00;-#,##0.00;0.00`

```dax
[Mean Cost Selected ML (NCU)] - [Mean Cost Seasonal Naive (NCU)]
```

### ML vs Seasonal Naive Cost Difference %

Selected ML minus Seasonal Naive mean cost as a share of Seasonal Naive mean cost.

Folder `Inventory\Comparisons`; format `+0.00%;-0.00%;0.00%`

```dax
DIVIDE ( [ML vs Seasonal Naive Cost Difference (NCU)], [Mean Cost Seasonal Naive (NCU)] )
```

### ML vs MA28 Fill Rate Difference (pp)

Selected ML minus MA28 pooled fill rate, in percentage points.

Folder `Inventory\Comparisons`; format `+0.00;-0.00;0.00`

```dax
100 * ( CALCULATE ( [Fill Rate], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "selected_ml" )
    - CALCULATE ( [Fill Rate], REMOVEFILTERS ( DimInventoryPolicy ), DimInventoryPolicy[PolicyKey] = "moving_average_28" ) )
```

### Origins ML Cheaper than MA28

Validation origins at which selected ML has the lower mean simulated cost than MA28.

Folder `Inventory\Robustness`; format `0`

```dax
IF ( DISTINCTCOUNT ( FactInventoryScenarioResults[DatasetKey] ) = 1,
    COUNTROWS ( FILTER ( VALUES ( DimValidationOrigin[OriginKey] ), [ML vs MA28 Cost Difference (NCU)] < 0 ) ) + 0 )
```

### Scenarios ML Cheaper than MA28

Scenarios (origins pooled) where selected ML has the lower mean cost than MA28. The scenarios reuse the same four origins; this is not a count of independent confirmations.

Folder `Inventory\Robustness`; format `0`

```dax
IF ( DISTINCTCOUNT ( FactInventoryScenarioResults[DatasetKey] ) = 1,
    COUNTROWS ( FILTER ( VALUES ( DimScenario[ScenarioKey] ), [ML vs MA28 Cost Difference (NCU)] < 0 ) ) + 0 )
```

### Scenarios ML Cheaper than Seasonal Naive

Scenarios (origins pooled) where selected ML has the lower mean cost than Seasonal Naive. Not independent replications.

Folder `Inventory\Robustness`; format `0`

```dax
IF ( DISTINCTCOUNT ( FactInventoryScenarioResults[DatasetKey] ) = 1,
    COUNTROWS ( FILTER ( VALUES ( DimScenario[ScenarioKey] ), [ML vs Seasonal Naive Cost Difference (NCU)] < 0 ) ) + 0 )
```

### Series-Origins ML Cheaper than MA28

Base scenario series-origin pairs where selected ML costs less than MA28 (tolerance 1e-8 NCU).

Folder `Inventory\Robustness`; format `#,##0`

```dax
IF ( DISTINCTCOUNT ( FactInventorySeriesBase[DatasetKey] ) = 1,
    SUMX (
        SUMMARIZE ( FactInventorySeriesBase, FactInventorySeriesBase[SeriesKey], FactInventorySeriesBase[OriginKey] ),
        VAR _ml = CALCULATE ( SUM ( FactInventorySeriesBase[TotalCost] ), REMOVEFILTERS ( DimInventoryPolicy ),
            DimInventoryPolicy[PolicyKey] = "selected_ml" )
        VAR _ma = CALCULATE ( SUM ( FactInventorySeriesBase[TotalCost] ), REMOVEFILTERS ( DimInventoryPolicy ),
            DimInventoryPolicy[PolicyKey] = "moving_average_28" )
        RETURN IF ( _ml < _ma - 0.00000001, 1, 0 )
    ) )
```

### Series-Origins ML Costlier than MA28

Base scenario series-origin pairs where selected ML costs more than MA28 (tolerance 1e-8 NCU).

Folder `Inventory\Robustness`; format `#,##0`

```dax
IF ( DISTINCTCOUNT ( FactInventorySeriesBase[DatasetKey] ) = 1,
    SUMX (
        SUMMARIZE ( FactInventorySeriesBase, FactInventorySeriesBase[SeriesKey], FactInventorySeriesBase[OriginKey] ),
        VAR _ml = CALCULATE ( SUM ( FactInventorySeriesBase[TotalCost] ), REMOVEFILTERS ( DimInventoryPolicy ),
            DimInventoryPolicy[PolicyKey] = "selected_ml" )
        VAR _ma = CALCULATE ( SUM ( FactInventorySeriesBase[TotalCost] ), REMOVEFILTERS ( DimInventoryPolicy ),
            DimInventoryPolicy[PolicyKey] = "moving_average_28" )
        RETURN IF ( _ml > _ma + 0.00000001, 1, 0 )
    ) )
```

## Governance

### Scenario Count

Distinct hypothetical scenarios with results in context.

Folder `Governance`; format `0`

```dax
DISTINCTCOUNT ( FactInventoryScenarioResults[ScenarioKey] )
```

### Inventory Cases

Distinct completed Phase 5 inventory cases (origin x scenario x policy) in context.

Folder `Governance`; format `#,##0`

```dax
DISTINCTCOUNT ( FactInventoryScenarioResults[CaseId] )
```

### Selected Forecast Model

Frozen Phase 4 selected trial for the single dataset in context.

Folder `Governance`; format `text`

```dax
SELECTEDVALUE ( DimDataset[SelectedTrial], "Select one dataset" )
```

### Verification Receipts

Saved verification receipts loaded into the model.

Folder `Governance`; format `0`

```dax
COUNTROWS ( FactScientificValidation )
```

### Verification Receipts Passed

Receipts whose own recorded status is "passed".

Folder `Governance`; format `0`

```dax
COUNTROWS ( FILTER ( FactScientificValidation, FactScientificValidation[Status] = "passed" ) ) + 0
```

### Audit Findings

Independent-audit findings in context.

Folder `Governance`; format `0`

```dax
COUNTROWS ( DimAuditFinding )
```

### Open Audit Findings

Findings whose recorded status starts with "Open".

Folder `Governance`; format `0`

```dax
COUNTROWS ( FILTER ( DimAuditFinding, LEFT ( DimAuditFinding[Status], 4 ) = "Open" ) ) + 0
```

## Titles

### Title Dataset

Selected dataset label, or a prompt when none or both are selected.

Folder `Titles`; format `text`

```dax
SELECTEDVALUE ( DimDataset[Dataset], "Select one dataset" )
```

### Title Forecast Page

Dynamic title for the forecasting page.

Folder `Titles`; format `text`

```dax
"Forecast accuracy | " & [Title Dataset] & " | validation origins only (not the final holdout)"
```

### Title Inventory Page

Dynamic title for the inventory page.

Folder `Titles`; format `text`

```dax
"Inventory policies | " & [Title Dataset] & " | " & SELECTEDVALUE ( DimScenario[Scenario], "select one scenario" ) & " | hypothetical NCU"
```

### Title Scenario Page

Dynamic title for the scenario page.

Folder `Titles`; format `text`

```dax
"Scenario sensitivity | " & [Title Dataset] & " | 17 scenarios share the same four origins"
```
