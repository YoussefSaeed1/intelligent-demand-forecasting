"""Date-only forecasting design, independent of observed target outcomes."""

from datetime import date, timedelta


def chronological_plan(start: date, end: date, horizon: int = 28, windows: int = 4) -> dict:
    """Reserve nonoverlapping expanding-origin validation windows and a final holdout."""
    if type(horizon) is not int or horizon < 1 or type(windows) is not int or windows < 1:
        raise ValueError("horizon and windows must be positive integers")
    cutoff = end - timedelta(days=horizon * (windows + 1))
    if cutoff < start + timedelta(days=2 * 365):
        raise ValueError("This protocol requires two years before validation")
    folds = []
    for number in range(windows):
        origin = cutoff + timedelta(days=number * horizon)
        folds.append(
            {
                "fold": number + 1,
                "train_start": start.isoformat(),
                "origin": origin.isoformat(),
                "validation_start": (origin + timedelta(days=1)).isoformat(),
                "validation_end": (origin + timedelta(days=horizon)).isoformat(),
            }
        )
    return {
        "horizon_days": horizon,
        "eda_start": start.isoformat(),
        "eda_end": cutoff.isoformat(),
        "validation_folds": folds,
        "final_origin": (end - timedelta(days=horizon)).isoformat(),
        "test_start": (end - timedelta(days=horizon - 1)).isoformat(),
        "test_end": end.isoformat(),
        "status": "proposed_not_executed",
    }
