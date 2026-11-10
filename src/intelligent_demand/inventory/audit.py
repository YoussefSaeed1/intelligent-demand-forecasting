"""Independent scalar/stock-flow/cost reconciliation of persisted inventory cases."""

import argparse
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from intelligent_demand.inventory.design import POLICIES, Scenario
from intelligent_demand.inventory.inputs import load_cohort
from intelligent_demand.inventory.plan import OUTPUT, REPORTS, ROOT, plan
from intelligent_demand.inventory.runner import case_key, completed, execution
from intelligent_demand.preservation.backup import evidence_path, sha256, write_new


def equal(a, b, context):
    if not np.allclose(a, b, equal_nan=True, rtol=1e-9, atol=1e-8):
        raise ValueError(f"Independent inventory reconciliation failed: {context}")


def scalar_reference(y, mean, forecast, settings, policy):
    """Separate scalar state machine; no production policy/engine helper calls."""
    stock = float(math.ceil(mean * settings.initial_cover_days))
    due = [0.0] * (len(y) + settings.lead_days + 2)
    fulfilled = unmet = holding = shortage = ordering = placed = received = orders = 0.0
    closing = position = stockouts = 0.0
    for day, demand in enumerate(y):
        received += due[day]
        stock += due[day]
        served = min(stock, float(demand))
        stock -= served
        lost = float(demand) - served
        fulfilled += served
        unmet += lost
        stockouts += lost > 0
        holding += settings.holding_cost * stock
        shortage += settings.shortage_cost * lost
        pipeline = sum(due[day + 1 :])
        quantity = 0
        if day % settings.review_days == 0 and day + settings.protection_days < len(y):
            if policy == "fixed_reorder_point":
                threshold = mean * settings.protection_days + settings.buffer_days * mean
                quantity = (
                    math.ceil(mean * settings.review_days) if stock + pipeline <= threshold else 0
                )
            else:
                target = float(np.sum(forecast[day + 1 : day + 1 + settings.protection_days]))
                target += settings.buffer_days * mean
                # The declared equation is S - IP, with IP = stock + pipeline.
                # Group IP explicitly: reassociation around ceil can change an
                # integer order at floating-point boundaries in fractional stresses.
                inventory_position = stock + pipeline
                quantity = math.ceil(max(0, target - inventory_position))
            due[day + settings.lead_days + 1] += quantity
        orders += quantity > 0
        placed += quantity
        ordering += (
            settings.fixed_order_cost * (quantity > 0) + settings.variable_order_cost * quantity
        )
        closing += stock
        position += stock + sum(due[day + 1 :])
    terminal = settings.terminal_cost * (stock + sum(due[len(y) :]))
    return {
        "fulfilled_units": fulfilled,
        "unmet_units": unmet,
        "received_units": received,
        "placed_units": placed,
        "orders": orders,
        "stockout_days": stockouts,
        "holding_cost": holding,
        "shortage_cost": shortage,
        "ordering_cost": ordering,
        "terminal_cost": terminal,
        "total_cost": holding + shortage + ordering + terminal,
        "final_on_hand": stock,
        "final_pipeline": sum(due[len(y) :]),
        "average_on_hand": closing / len(y),
        "average_inventory_position": position / len(y),
    }


def event_audit(path, table, metadata, y, settings, full, start=None, representatives=None):
    columns = (
        "opening_stock",
        "receipts",
        "fulfilled",
        "unmet",
        "closing_stock",
        "pipeline_after",
        "order_quantity",
        "demand",
        "inventory_position",
        "holding_cost",
        "shortage_cost",
        "ordering_cost",
    )
    arrays = {key: np.full(y.shape, np.nan) for key in columns}
    seen = np.zeros(y.shape, dtype=bool)
    index = pd.Index(metadata.series_id)
    for batch in pq.ParquetFile(path).iter_batches(batch_size=65536):
        frame = batch.to_pandas()
        rows = index.get_indexer(frame.series_id)
        days = frame.day_index.to_numpy(dtype=int)
        if (rows < 0).any() or ((days < 0) | (days >= 28)).any():
            raise ValueError("Event key outside cohort")
        if start is not None:
            expected_dates = pd.Timestamp(start) + pd.to_timedelta(days, unit="D")
            if not np.array_equal(pd.to_datetime(frame.target_date).to_numpy(), expected_dates):
                raise ValueError("Persisted event absolute date differs from origin window")
        if len(np.unique(rows * 28 + days)) != len(frame) or seen[rows, days].any():
            raise ValueError("Duplicate persisted event key")
        seen[rows, days] = True
        for name in columns:
            arrays[name][rows, days] = frame[name]
    mask = seen.any(axis=1)
    if not seen[mask].all() or (full and not mask.all()):
        raise ValueError("Incomplete declared event coverage")
    if not full and representatives is not None:
        if set(metadata.series_id[mask]) != set(representatives):
            raise ValueError("Sensitivity events differ from frozen representatives")
    a = {k: v[mask] for k, v in arrays.items()}
    equal(a["demand"], y[mask], "persisted event demand vs common source path")
    equal(a["opening_stock"] + a["receipts"] - a["fulfilled"], a["closing_stock"], "daily stock")
    equal(a["demand"] - a["fulfilled"], a["unmet"], "daily service")
    equal(a["opening_stock"][:, 0], table.initial_on_hand.to_numpy()[mask], "initial stock")
    equal(a["opening_stock"][:, 1:], a["closing_stock"][:, :-1], "stock continuity")
    expected = np.zeros_like(a["receipts"])
    offset = settings.lead_days + 1
    if offset < 28:
        expected[:, offset:] = a["order_quantity"][:, :-offset]
    equal(a["receipts"], expected, "receipt offset, no lost/double orders")
    equal(a["pipeline_after"], np.cumsum(a["order_quantity"] - a["receipts"], axis=1), "pipeline")
    equal(a["inventory_position"], a["closing_stock"] + a["pipeline_after"], "inventory position")
    for event, summary in (
        ("receipts", "received_units"),
        ("fulfilled", "fulfilled_units"),
        ("unmet", "unmet_units"),
        ("order_quantity", "placed_units"),
        ("holding_cost", "holding_cost"),
        ("shortage_cost", "shortage_cost"),
        ("ordering_cost", "ordering_cost"),
    ):
        equal(a[event].sum(axis=1), table[summary].to_numpy()[mask], event)
    equal(a["closing_stock"].mean(axis=1), table.average_on_hand.to_numpy()[mask], "mean stock")
    return int(seen.sum())


def aggregate(frame):
    demand = float(frame.demand_units.sum())
    return {
        "series": len(frame),
        "total_cost": float(frame.total_cost.sum()),
        "mean_cost": float(frame.total_cost.mean()),
        "holding_cost": float(frame.holding_cost.sum()),
        "shortage_cost": float(frame.shortage_cost.sum()),
        "ordering_cost": float(frame.ordering_cost.sum()),
        "terminal_cost": float(frame.terminal_cost.sum()),
        "demand_units": demand,
        "fulfilled_units": float(frame.fulfilled_units.sum()),
        "unmet_units": float(frame.unmet_units.sum()),
        "pooled_fill_rate": float(frame.fulfilled_units.sum() / demand) if demand else None,
        "macro_fill_rate": float(frame.fill_rate.mean()) if frame.fill_rate.notna().any() else None,
        "undefined_fill_series": int(frame.fill_rate.isna().sum()),
        "stockout_days": int(frame.stockout_days.sum()),
        "mean_stockout_day_rate": float(frame.stockout_days.mean() / 28),
        "average_on_hand": float(frame.average_on_hand.mean()),
        "average_inventory_position": float(frame.average_inventory_position.mean()),
        "orders": int(frame.orders.sum()),
        "terminal_pipeline": float(frame.final_pipeline.sum()),
        "final_on_hand": float(frame.final_on_hand.sum()),
    }


def metric_audit():
    """Additional persisted-only check of every published ratio and event counter."""
    p, contract = plan(), execution()
    cases = episodes = event_rows = 0
    for cohort in p["cohorts"]:
        index = None
        for raw in p["scenarios"]:
            settings = Scenario(**raw)
            for policy in POLICIES:
                directory = OUTPUT / "runs" / case_key(cohort, settings, policy, contract)
                state = completed(directory)
                table = pd.read_parquet(ROOT / state["files"]["series"]["path"])
                index = pd.Index(table.series_id)
                equal(table.initial_pipeline, np.zeros(len(table)), "empty empirical pipeline")
                equal(table.stockout_day_rate, table.stockout_days / 28, "stockout day rate")
                equal(table.order_frequency, table.orders / 28, "order frequency")
                with np.errstate(divide="ignore", invalid="ignore"):
                    average = np.where(table.orders > 0, table.placed_units / table.orders, np.nan)
                    turnover = np.where(
                        table.average_on_hand > 0,
                        table.fulfilled_units / table.average_on_hand,
                        np.nan,
                    )
                equal(table.average_order_quantity, average, "average order quantity")
                equal(table.window_turnover, turnover, "undefined/defined window turnover")
                counts = np.zeros((len(table), 3))
                seen = np.zeros(len(table), dtype=int)
                for batch in pq.ParquetFile(ROOT / state["files"]["events"]["path"]).iter_batches(
                    batch_size=65536,
                    columns=["series_id", "unmet", "order_quantity", "inventory_position"],
                ):
                    events = batch.to_pandas()
                    rows = index.get_indexer(events.series_id)
                    if (rows < 0).any():
                        raise ValueError("Unexpected metric event key")
                    np.add.at(counts[:, 0], rows, events.unmet.to_numpy() > 0)
                    np.add.at(counts[:, 1], rows, events.order_quantity.to_numpy() > 0)
                    np.add.at(counts[:, 2], rows, events.inventory_position.to_numpy())
                    np.add.at(seen, rows, 1)
                    event_rows += len(events)
                mask = seen > 0
                equal(seen[mask], np.full(mask.sum(), 28), "metric event coverage")
                equal(counts[mask, 0], table.stockout_days[mask], "persisted stockout days")
                equal(counts[mask, 1], table.orders[mask], "persisted positive-order counts")
                equal(
                    counts[mask, 2] / 28,
                    table.average_inventory_position[mask],
                    "mean post-order inventory position",
                )
                cases += 1
                episodes += len(table)
        print(f"METRICS {cohort['dataset']} fold{cohort['fold']['number']}", flush=True)
    if cases != 544:
        raise ValueError("Missing metric cases")
    record = {
        "status": "passed",
        "cases": cases,
        "series_episodes": episodes,
        "retained_event_rows": event_rows,
        "scope": "Every per-series ratio; all retained positive-order/stockout counters "
        "and average post-order inventory position; no target input read",
        "execution_sha256": contract["sha256"],
    }
    write_new(REPORTS / "metric_validation.json", record)
    print(json.dumps(record, indent=2))


def evidence_inventory():
    """Inventory local Phase 5 evidence; a hash list is explicitly not a backup."""
    plan()
    execution()
    paths = set()
    for directory in (OUTPUT, REPORTS, ROOT / "reports/figures/phase5"):
        paths.update(path for path in directory.rglob("*") if path.is_file())
    for pattern in (
        "src/intelligent_demand/inventory/*.py",
        "tests/test_inventory_*.py",
        "docs/PHASE5_*.md",
        "docs/INVENTORY_*.md",
    ):
        paths.update(ROOT.glob(pattern))
    for logical in (
        "configs/inventory.yaml",
        "docs/CLAUDE_FOCUSED_FORECASTING_GATE.md",
        "README.md",
        "docs/ROADMAP.md",
        "docs/ACADEMIC_REQUIREMENTS.md",
        ".gitignore",
        "src/intelligent_demand/preservation/verify.py",
    ):
        paths.add(ROOT / logical)
    # Exclusive output manifests cannot include their own hash or a future gate.
    paths.difference_update(
        {REPORTS / "PHASE5_EVIDENCE_INVENTORY.json", REPORTS / "phase5d_gate.json"}
    )
    names = sorted(
        path.relative_to(ROOT).as_posix() for path in paths if "__pycache__" not in path.parts
    )
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=ROOT,
        input="\n".join(names) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ValueError("Git exclusion inspection failed")
    ignored = set(result.stdout.splitlines())
    entries = []
    for logical in names:
        path = evidence_path(ROOT, logical)
        entries.append(
            {
                "path": logical,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "git_ignored": logical in ignored,
            }
        )
    inventory = {
        "schema_version": 1,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "files": entries,
        "original_phase4_inventory": {
            "path": "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json",
            "sha256": sha256(ROOT / "reports/forecasting/PHASE4_EVIDENCE_INVENTORY.json"),
        },
        "exclusions": "This inventory and future phase5d_gate.json; Python caches. "
        "Original source dependencies remain in the protected Phase 4 inventory and "
        "frozen Phase 5 plan, not duplicated into the Phase 5 namespace.",
        "protection": "LOCAL FILE INVENTORY ONLY; not a backup. Ignored Phase 5 "
        "outputs/figures are not protected by Git and no Phase 5 backup is claimed.",
        "regeneration": "Permitted validation-only simulations/audits and report build; "
        "requires original ignored input/cache/forecast dependencies. No final holdout "
        "target read, training, tuning or forecast regeneration required.",
    }
    write_new(REPORTS / "PHASE5_EVIDENCE_INVENTORY.json", inventory)
    print(
        json.dumps(
            {
                "status": "inventoried",
                "files": len(entries),
                "bytes": inventory["total_bytes"],
                "git_ignored": len(ignored),
            },
            indent=2,
        )
    )


def audit(action, receipt_directory=None):
    began = time.perf_counter()
    p, contract = plan(), execution()
    summaries, groups, paired, receipts = [], [], [], []
    event_rows = scalar_series = series_rows = 0
    for cohort in p["cohorts"]:
        metadata, original, mean, predictions, _ = load_cohort(cohort)
        for raw in p["scenarios"]:
            settings = Scenario(**raw)
            if action == "base" and settings.identifier != "base":
                continue
            y = np.maximum(
                0, mean[:, None] + settings.variability_multiplier * (original - mean[:, None])
            )
            if settings.variability_multiplier == 1:
                y = original
            tables = {}
            for policy in POLICIES:
                key = case_key(cohort, settings, policy, contract)
                directory = OUTPUT / "runs" / key
                state = completed(directory)
                table = pd.read_parquet(ROOT / state["files"]["series"]["path"])
                if (
                    tuple(table.series_id) != tuple(metadata.series_id)
                    or table.series_id.duplicated().any()
                ):
                    raise ValueError("Missing/extra/duplicate policy population")
                equal(table.historical_mean56, mean, "origin-only calibration")
                equal(
                    table.initial_on_hand,
                    np.ceil(mean * settings.initial_cover_days),
                    "fair initial stock",
                )
                equal(table.demand_units, y.sum(axis=1), "common demand path")
                equal(
                    table.initial_on_hand + table.received_units - table.fulfilled_units,
                    table.final_on_hand,
                    "episode stock",
                )
                equal(
                    table.placed_units - table.received_units,
                    table.final_pipeline,
                    "episode pipeline",
                )
                equal(
                    table.demand_units - table.fulfilled_units, table.unmet_units, "episode service"
                )
                equal(
                    table.holding_cost,
                    table.average_on_hand * 28 * settings.holding_cost,
                    "holding",
                )
                equal(table.shortage_cost, table.unmet_units * settings.shortage_cost, "shortage")
                equal(
                    table.ordering_cost,
                    table.orders * settings.fixed_order_cost
                    + table.placed_units * settings.variable_order_cost,
                    "ordering",
                )
                equal(
                    table.terminal_cost,
                    (table.final_on_hand + table.final_pipeline) * settings.terminal_cost,
                    "terminal",
                )
                equal(
                    table.total_cost,
                    table.holding_cost
                    + table.shortage_cost
                    + table.ordering_cost
                    + table.terminal_cost,
                    "total cost",
                )
                with np.errstate(divide="ignore", invalid="ignore"):
                    fill = np.where(
                        table.demand_units > 0, table.fulfilled_units / table.demand_units, np.nan
                    )
                equal(table.fill_rate, fill, "undefined/defined fill rate")
                event_rows += event_audit(
                    ROOT / state["files"]["events"]["path"],
                    table,
                    metadata,
                    y,
                    settings,
                    settings.identifier == "base",
                    cohort["fold"]["validation_start"],
                    cohort["representatives"],
                )
                forecast = predictions["selected_ml" if policy == "fixed_reorder_point" else policy]
                for row in np.flatnonzero(metadata.series_id.isin(cohort["representatives"])):
                    reference = scalar_reference(y[row], mean[row], forecast[row], settings, policy)
                    for name, value in reference.items():
                        equal(table[name].iloc[row], value, "scalar replay " + name)
                    scalar_series += 1
                header = {
                    "dataset": cohort["dataset"],
                    "fold": cohort["fold"]["number"],
                    "scenario": settings.identifier,
                    "policy": policy,
                }
                summaries.append(header | aggregate(table))
                for field in (
                    "pattern",
                    "origin_sample_all_zero",
                    "retrospective_final_training_all_zero",
                ):
                    for group, block in table.groupby(field, sort=True):
                        groups.append(
                            header | {"group_field": field, "group": str(group)} | aggregate(block)
                        )
                tables[policy] = table
                receipts.append(
                    {"case_id": key, "status_sha256": sha256(directory / "status.json")}
                )
                series_rows += len(table)
            baseline = tables["moving_average_28"]
            for policy, table in tables.items():
                difference = table.total_cost.to_numpy() - baseline.total_cost.to_numpy()
                paired.append(
                    {
                        "dataset": cohort["dataset"],
                        "fold": cohort["fold"]["number"],
                        "scenario": settings.identifier,
                        "policy": policy,
                        "reference": "moving_average_28",
                        "series": len(table),
                        "mean_cost_difference": float(difference.mean()),
                        "median_cost_difference": float(np.median(difference)),
                        "lower_cost_series": int((difference < -1e-8).sum()),
                        "higher_cost_series": int((difference > 1e-8).sum()),
                        "ties": int((np.abs(difference) <= 1e-8).sum()),
                    }
                )
        print(f"AUDITED {cohort['dataset']} fold{cohort['fold']['number']}", flush=True)
    expected = 32 if action == "base" else 544
    if len(receipts) != expected:
        raise ValueError("Not all frozen cases reconciled")
    record = {
        "status": "passed",
        "cases": len(receipts),
        "series_episodes": series_rows,
        "independent_event_rows": event_rows,
        "scalar_reference_episodes": scalar_series,
        "seconds": time.perf_counter() - began,
        "plan_sha256": p["sha256"],
        "execution_sha256": contract["sha256"],
        "receipts": receipts,
        "summaries": summaries,
        "groups": groups,
        "paired": paired,
        "scope": "All summary accounting; every base daily event and every retained sensitivity "
        "event; independent scalar replay of all predeclared representative series; "
        "same approved input adapter, independently written arithmetic/state machine",
        "final_holdout_used": False,
    }
    destination = REPORTS if receipt_directory is None else Path(receipt_directory)
    destination.mkdir(parents=True, exist_ok=True)
    write_new(
        destination / ("phase5_base_summary.json" if action == "base" else "phase5_summary.json"),
        record,
    )
    if action == "base" and receipt_directory is None:
        write_new(
            REPORTS / "phase5c_gate.json",
            {k: v for k, v in record.items() if k not in ("summaries", "groups", "paired")},
        )
    print(
        json.dumps(
            {
                k: v
                for k, v in record.items()
                if k not in ("summaries", "groups", "paired", "receipts")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["base", "all", "metrics", "inventory"])
    parser.add_argument("--receipt-directory", type=Path)
    args = parser.parse_args()
    if args.action == "metrics":
        metric_audit()
    elif args.action == "inventory":
        evidence_inventory()
    else:
        audit(args.action, args.receipt_directory)
