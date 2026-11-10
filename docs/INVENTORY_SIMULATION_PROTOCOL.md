# Frozen Phase 5 inventory simulation protocol

Phase 5 is authorised under the supplied focused forecasting gate's conditional go.
That limited review did not independently establish numerical or full-system validity.
This is hypothetical, validation-reused decision analysis, not observed inventory
performance, independent policy validation or realised savings. Observed sales proxy
demand and may be censored. No Phase 4 model, sample or final assessment is changed.

Use all 500 Store Item and 30,490 M5 series at the four original validation origins.
Each origin is an independent 28-day inventory episode; stock resets under the same
training-only initialisation across policies. Never concatenate episodes as one
continuous operation. Fixed-origin forecasts are not daily refreshed. All models
were selected using these validation folds, so resulting policy comparisons are
exploratory validation-reused results, not a new independent out-of-sample test.

Daily order: receive previously scheduled orders at start; realise sales proxy demand;
fulfil min(available,demand), lose the remainder; charge closing-stock holding and
unmet-unit penalties; review at end of day; place orders using remaining saved
forecast dates and current inventory position. With L full intervening demand days,
an end-of-day order on day t arrives at the start of day t+L+1. L=0 means next day,
never immediate availability. Review every R days starting at episode day one.

The protection period is P=L+R dates, t+1 through t+P inclusive. An end-of-day
decision is permitted only if every protection date lies inside the original saved
forecast horizon. The same decision cutoff applies to fixed-ROP and all forecast
policies. Later demand is still evaluated, but no unsupported late order is placed.
This finite-episode effect is a limitation, not a claimed steady-state policy test.

Initial stock is ceil(initial_cover_days * mean(last56 observed training days)),
with empty initial pipeline, identically for all four policies. Hypothetical buffer
is buffer_days times that same historical mean. It is not a calibrated service
probability. No same-window or final residuals calibrate anything, including fold one.
No oracle or backorder extension is included. No final holdout is used in Phase 5.

The 17 scenarios in configs/inventory.yaml are a fixed base plus one-at-a-time
changes in lead, review, buffer, initial stock, holding/shortage/order costs,
terminal exposure charge and demand-variability stress. No winner/scenario is chosen
after results. Policies share paths, timing, start, assumptions and coverage exactly.
Variability stress is max(0,mu_train+a*(sales-mu_train)); it can also change mean/zeros
and is not an isolated causal variance intervention. Forecasts are not regenerated.

Persist full-population per-series summaries for every case; full daily events for
the base scenario; representative daily paths for sensitivities, selected beforehand
by prefix volume and fixed ID ranks. Full-population evaluation is not limited to
the event sample. Single worker, batch4096, 2GiB monitored RSS, 900s active execution,
8GiB output and 16GiB minimum free disk. Account for every case, failures and resume.
